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
import pyarrow.parquet as pq
import gcsfs
import pyarrow.dataset as ds

# Importiere die vom Dockerfile generierten Protobuf-Stubs
import service_pb2
import service_pb2_grpc

WATCH_DIR = os.getenv("WATCH_DIR", "/tmp/images")
CATALOG_DIR = Path(os.getenv("CATALOG_DIR", os.path.join(WATCH_DIR, "catalog")))
THUMBNAILS_DIR = Path(
    os.getenv("THUMBNAILS_DIR", os.path.join(WATCH_DIR, "thumbnails"))
)

POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "5"))
CONSIDER_EXISTING_FROM_REMOTE_STORAGE = False

# Logger-Formatierung für gute Lesbarkeit auf der Hörsaal-Leinwand
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - \033[1;34m[Orchestrator]\033[0m %(message)s",
)
logger = logging.getLogger(__name__)

CONCURRENCY = int(os.getenv("CONCURRENCY", "5"))
PROCESSING_BATCH_SIZE = 5

# Die gRPC- und Java-REST-Endpunkte
LOCAL = True
if LOCAL:
    JAVA_API_URL = "http://localhost:8080"
    WORKERS = {
        "Worker_Tags": "localhost:50051",
        "Worker_Thumbnails": "localhost:50052",
        "Worker_Embeddings": "localhost:50053",
    }
else:
    JAVA_API_URL = os.getenv("JAVA_API_URL", "http://java_api:8080")
    WORKERS = {
        "Worker_Tags": os.getenv("WORKER_TAGS_ADDR", "worker_tags:50051"),
        "Worker_Thumbnails": os.getenv(
            "WORKER_THUMBNAILS_ADDR", "worker_thumbnails:50052"
        ),
        "Worker_Embeddings": os.getenv(
            "WORKER_EMBEDDINGS_ADDR", "dns:///worker_embeddings:50053"
        ),
    }


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
        state.is_retry()

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
        # return_exceptions=False sorgt für sofortigen Abbruch beim ersten Fehler!
        tag_response, thumbnail_response, embedding_response = await asyncio.gather(
            *tasks, return_exceptions=False
        )
        if any(
            response.status != "COMPLETED"
            for response in (tag_response, thumbnail_response, embedding_response)
        ):
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
    """Persist completed worker results as one immutable Parquet batch."""
    rows = []
    for result in results:
        image_path_local = result["image_path_local"]
        image_id = os.path.basename(image_path_local)

        with open(image_path_local, "rb") as image_file:
            content_hash = hashlib.sha256(image_file.read()).hexdigest()

        rows.append(
            {
                "image_id": image_id,
                "content_hash": content_hash,
                "filepath_orig": result["image_path"],
                "metadata": json.dumps(result["metadata"], sort_keys=True),
                "embedding": result["embedding"],
                "thumbnail_path": result["thumbnail_path"],
                "processed_at": datetime.now(timezone.utc).isoformat(),
            }
        )

    CATALOG_DIR.mkdir(parents=True, exist_ok=True)
    batch_name = (
        f"batch-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')}.parquet"
    )
    batch_path = CATALOG_DIR / batch_name
    # compression format for the Parquet file
    temporary_path = CATALOG_DIR / f".{batch_name}.tmp"
    table = pa.Table.from_pylist(rows)
    pq.write_table(table, temporary_path, compression="zstd")
    os.replace(temporary_path, batch_path)

    # copy to gcs
    fs = gcsfs.GCSFileSystem(project="pixplore-503406")
    gcs_path = f"gs://pixplore-bucket/catalog/{batch_name}"
    fs.put(str(batch_path), gcs_path)


def get_catalog_image_ids():
    """
    Download processed.parquet from remote storage (if not exist locally)
    and return a set of all image_ids in the catalog.
    """
    fs = gcsfs.GCSFileSystem(project="pixplore-503406")

    GCS_BASE_PATH = "gs://pixplore-bucket"
    PARQUET_FILES = fs.ls(f"{GCS_BASE_PATH}/catalog")
    dataset = ds.dataset(PARQUET_FILES, format="parquet", filesystem=fs)
    table = dataset.to_table(columns=["image_id"]).to_pandas()

    return set(table["image_id"].to_list())


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
                logger.info("✅ Batch abgeschlossen. Fahre mit dem nächsten fort.")

            os.remove(csv_list_file)
            logger.info(f"🗑️ {csv_list_file} gelöscht. Processing ist done.")

        await asyncio.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    # create folder structure
    os.makedirs(CATALOG_DIR, exist_ok=True)
    os.makedirs(THUMBNAILS_DIR, exist_ok=True)

    try:
        asyncio.run(watch_and_process())
    except KeyboardInterrupt:
        print("\nOrchestrator beendet.")
