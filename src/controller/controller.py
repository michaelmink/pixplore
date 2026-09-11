import asyncio
import logging
import os
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import grpc
import aiohttp
import pyarrow as pa
import gcsfs
from pyiceberg.catalog.sql import SqlCatalog

# Importiere die vom Dockerfile generierten Protobuf-Stubs
import service_pb2
import service_pb2_grpc

WATCH_DIR = os.getenv("WATCH_DIR", "/tmp/images")
THUMBNAILS_DIR = Path(
    os.getenv("THUMBNAILS_DIR", os.path.join(WATCH_DIR, "thumbnails"))
)

# Iceberg-Katalog: SQLite-Zeiger lokal, Daten/Metadaten auf GCS
ICEBERG_CATALOG_URI = os.getenv(
    "ICEBERG_CATALOG_URI",
    f"sqlite:///{os.path.join(WATCH_DIR, 'iceberg_catalog.db')}",
)
ICEBERG_WAREHOUSE = os.getenv("ICEBERG_WAREHOUSE", "gs://pixplore-bucket/warehouse")
GCS_PROJECT = os.getenv("GCS_PROJECT", "pixplore-503406")
THUMBNAIL_GCS_PREFIX = os.getenv(
    "THUMBNAIL_GCS_PREFIX", "gs://pixplore-bucket/thumbnails"
)
ICEBERG_NAMESPACE = "catalog"
ICEBERG_TABLE = f"{ICEBERG_NAMESPACE}.images"

POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "5"))
CONSIDER_EXISTING_FROM_REMOTE_STORAGE = True

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - \033[1;34m[Orchestrator]\033[0m %(message)s",
)
logger = logging.getLogger(__name__)

CONCURRENCY = int(os.getenv("CONCURRENCY", "5"))
PROCESSING_BATCH_SIZE = 100

# Die gRPC- und Java-REST-Endpunkte
JAVA_API_URL = os.getenv("JAVA_API_URL", "http://localhost:8080")
WORKERS = {
    "Worker_Tags": os.getenv("WORKER_TAGS_ADDR", "localhost:50051"),
    "Worker_Thumbnails": os.getenv("WORKER_THUMBNAILS_ADDR", "localhost:50052"),
    "Worker_Embeddings": os.getenv("WORKER_EMBEDDINGS_ADDR", "localhost:50053"),
}

# Schema der Katalog-Tabelle
CATALOG_SCHEMA = pa.schema(
    [
        ("image_id", pa.string()),
        ("content_hash", pa.string()),
        ("filepath_orig", pa.string()),
        ("metadata", pa.string()),
        ("embedding", pa.list_(pa.float32())),
        ("thumbnail_uri", pa.string()),
        ("processed_at", pa.timestamp("us", tz="UTC")),
    ]
)

_catalog = None


def get_catalog():
    global _catalog
    if _catalog is None:
        _catalog = SqlCatalog(
            "pixplore",
            **{
                "uri": ICEBERG_CATALOG_URI,
                "warehouse": ICEBERG_WAREHOUSE,
            },
        )
    return _catalog


def init_catalog():
    catalog = get_catalog()
    catalog.create_namespace_if_not_exists(ICEBERG_NAMESPACE)
    catalog.create_table_if_not_exists(ICEBERG_TABLE, schema=CATALOG_SCHEMA)


async def execute_forward_step(
    worker_name: str, addr: str, req: service_pb2.TaskRequest
):
    """Execute one worker step and return its result."""
    logger.info(
        f"📡 Sende Task {req.task_id} an \033[1;32m{worker_name}\033[0m ({addr})..."
    )

    async with grpc.aio.insecure_channel(addr) as channel:
        stub = service_pb2_grpc.WorkerServiceStub(channel)

        # RPC ausführen mit einem harten Timeout von 3 Sekunden
        response = await stub.ProcessTask(req)

        logger.info(
            f"✅ \033[1;32m{worker_name}\033[0m meldet Erfolg. "
            f"Record-ID gemerkt: {response.db_record_id}"
        )
        return response


class State:
    PENDING = "PENDING"
    DOWNLOADED = "DOWNLOADED"
    WORKERS_COMPLETED = "WORKERS_COMPLETED"
    COMMITTED = "COMMITTED"
    RETRY = "RETRY"

    def __init__(self, img_path: str):
        self.img_path = img_path
        self.state = self.PENDING

    def is_pending(self):
        self.state = self.PENDING

    def is_downloaded(self):
        self.state = self.DOWNLOADED

    def is_workers_completed(self):
        self.state = self.WORKERS_COMPLETED

    def is_committed(self):
        self.state = self.COMMITTED

    def is_retry(self):
        self.state = self.RETRY

    def print(self):
        logger.info(f"Image path: {self.img_path}, State: {self.state}")


async def process_image_pipeline(task_id: str, img_path: str):
    """
    Run the image pipeline
    """
    # init state
    state = State(img_path)
    # download the image using java_api REST endpoint download_file
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"{JAVA_API_URL}/download_file", params={"path": img_path}
        ) as resp:
            if resp.status != 200:
                logger.error(
                    f"❌ Download fehlgeschlagen für {img_path}: HTTP {resp.status}"
                )
                return state.is_retry()
            logger.info(f"⬇️ Download erfolgreich für {img_path}")

    # Workaround!
    img_path_local = os.path.join(WATCH_DIR, os.path.basename(img_path))

    # check if file exists
    if os.path.exists(img_path_local):
        state.is_downloaded()
    else:
        return state.is_retry()

    # gRPC-Request-Objekt bauen
    request = service_pb2.TaskRequest(task_id=task_id, img_path=img_path_local)

    # Erstelle die parallelen Coroutinen
    tasks = [
        execute_forward_step("Worker_Tags", WORKERS["Worker_Tags"], request),
        execute_forward_step(
            "Worker_Thumbnails", WORKERS["Worker_Thumbnails"], request
        ),
        execute_forward_step(
            "Worker_Embeddings", WORKERS["Worker_Embeddings"], request
        ),
    ]

    try:
        # Scatter-Phase: Alle 3 Worker arbeiten zeitgleich
        # return_exceptions=True sorgt dafür, dass alle Aufgaben ausgeführt werden, auch wenn einige fehlschlagen. Fehler werden als Ausnahmen zurückgegeben.
        tag_response, thumbnail_response, embedding_response = await asyncio.gather(
            *tasks, return_exceptions=True
        )
        responses = (tag_response, thumbnail_response, embedding_response)
        if any(isinstance(r, Exception) for r in responses):
            state.is_retry()
            raise RuntimeError(f"Worker failure for {task_id}")
        if any(r.status != "COMPLETED" for r in responses):
            state.is_retry()
            raise RuntimeError(f"Worker failure for {task_id}")

        # workers have completed successfully
        state.is_workers_completed()

        return {
            "status": state.state,
            "image_path_local": img_path_local,
            "image_path": img_path,
            "metadata": json.loads(tag_response.metadata_json),
            "embedding": list(embedding_response.embedding),
            "thumbnail_path": thumbnail_response.thumbnail_path,
        }

    except Exception as e:
        state.is_retry()
        # remove potential created thumbnail
        thumbnail_path = os.path.join(
            WATCH_DIR,
            "thumbnails",
            f"{Path(img_path_local).stem}_thumb.jpg",
        )
        if os.path.exists(thumbnail_path):
            os.remove(thumbnail_path)
        logger.error(f"💥 GLOBALER PIPELINE-ABBRUCH! Fehlerursache: {str(e)}")
        return state


def write_catalog_batch(results):
    """Upload thumbnails to GCS, then upsert catalog rows (upload-before-commit)."""
    # ohne project=, sonst weicht gcsfs bei User-ADC auf den VM-Metadata-SA aus
    fs = gcsfs.GCSFileSystem()
    prefix = THUMBNAIL_GCS_PREFIX.rstrip("/")
    rows = []
    for result in results:
        image_path_local = result["image_path_local"]
        image_id = os.path.basename(image_path_local)

        with open(image_path_local, "rb") as image_file:
            content_hash = hashlib.sha256(image_file.read()).hexdigest()

        # Thumbnail VOR dem Upsert nach GCS -> eine Zeile referenziert nie eine fehlende Datei
        thumb_name = os.path.basename(result["thumbnail_path"])
        thumbnail_uri = f"{prefix}/{thumb_name}"
        fs.put(result["thumbnail_path"], thumbnail_uri)

        rows.append(
            {
                "image_id": image_id,
                "content_hash": content_hash,
                "filepath_orig": result["image_path"],
                "metadata": json.dumps(result["metadata"], sort_keys=True),
                "embedding": result["embedding"],
                "thumbnail_uri": thumbnail_uri,
                "processed_at": datetime.now(timezone.utc),
            }
        )

    # Alle Thumbnails liegen jetzt auf GCS -> atomarer Upsert
    arrow_table = pa.Table.from_pylist(rows, schema=CATALOG_SCHEMA)
    table = get_catalog().load_table(ICEBERG_TABLE)
    # Dedup direkt beim Schreiben über content_hash
    table.upsert(arrow_table, join_cols=["content_hash"])
    logger.info("📚 %d Bild(er) in den Iceberg-Katalog upserted.", len(rows))


def get_catalog_image_ids():
    """Return the set of all image_ids already present in the Iceberg catalog."""
    table = get_catalog().load_table(ICEBERG_TABLE)
    arrow = table.scan(selected_fields=("image_id",)).to_arrow()
    return set(arrow.column("image_id").to_pylist())


async def process_with_limit(semaphore, task_id, img_path):
    """
    Process an image with concurrency control using a semaphore.
    """
    async with semaphore:
        try:
            return await process_image_pipeline(task_id, img_path)
        except Exception as error:
            logger.exception("Unerwarteter Fehler für %s", task_id)
            return {
                "status": "FAILED",
                "source_path": img_path,
                "saga": {
                    "task_id": task_id,
                    "source_path": img_path,
                    "error": str(error),
                },
            }


async def watch_and_process():
    """
    überwacht WATCH_DIR auf neue csv Files und verarbeitet sie
    """
    logger.info(
        f"👀 Listener gestartet. Überwache {WATCH_DIR} (alle {POLL_INTERVAL}s)..."
    )
    csv_list_file = os.path.join(WATCH_DIR, "list_files.csv")
    semaphore = asyncio.Semaphore(CONCURRENCY)

    while True:
        if os.path.exists(csv_list_file):
            logger.info(f"📂 CSV-Datei gefunden: {csv_list_file}")

            # collect tasks for processing
            tasks = []
            if CONSIDER_EXISTING_FROM_REMOTE_STORAGE:
                existing_image_ids = get_catalog_image_ids()
            else:
                existing_image_ids = []

            with open(csv_list_file, newline="") as csvfile:
                reader = csv.reader(csvfile)
                for i, img_path in enumerate(reader):
                    img_path = img_path[0]

                    if not img_path.lower().endswith((".jpg", ".jpeg")):
                        logger.info(f"⚠️ Überspringe nicht-JPG-Datei: {img_path}")
                        continue

                    task_id = os.path.basename(img_path)
                    if task_id in existing_image_ids:
                        logger.info(
                            f"⏭️ Überspringe bereits katalogisiertes Bild: {task_id}"
                        )
                        continue

                    # append to tasks list
                    tasks.append(process_with_limit(semaphore, task_id, img_path))

            # process batches of tasks
            for batch in [
                tasks[i : i + PROCESSING_BATCH_SIZE]
                for i in range(0, len(tasks), PROCESSING_BATCH_SIZE)
            ]:
                # run in event loop
                results = await asyncio.gather(*batch)

                # successful results
                completed_results = [
                    result
                    for result in results
                    if isinstance(result, dict)
                    and result.get("status") == "WORKERS_COMPLETED"
                ]
                if completed_results:
                    # write to parquet
                    write_catalog_batch(completed_results)
                    # clean up
                    for result in completed_results:
                        result["status"] = "COMMITED"
                        os.remove(result["image_path_local"])

                # failed results
                failed_results = []
                for result in results:
                    if isinstance(result, dict) and result.get("status") == "FAILED":
                        failed_results.append(result)

                if failed_results:
                    retry_path = f"{csv_list_file}.retry"
                    with open(retry_path, "w", newline="") as retry_file:
                        writer = csv.writer(retry_file)
                        writer.writerows(
                            [[result["image_path"]] for result in failed_results]
                        )
                    logger.info(
                        f"🔁 {len(failed_results)} Bild(er) für einen Retry in {retry_path} geschrieben."
                    )

                # batch done. next one.
                await asyncio.sleep(0)
                logger.info("✅ Batch abgeschlossen. Fahre mit dem nächsten fort.")

            os.remove(csv_list_file)
            logger.info(f"🗑️ {csv_list_file} gelöscht. Processing ist done.")

        await asyncio.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    # create folder structure
    os.makedirs(THUMBNAILS_DIR, exist_ok=True)
    # Iceberg-Katalog + Tabelle sicherstellen
    init_catalog()

    try:
        asyncio.run(watch_and_process())
    except KeyboardInterrupt:
        print("\nOrchestrator beendet.")
