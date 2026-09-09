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

# Importiere die vom Dockerfile generierten Protobuf-Stubs
import service_pb2
import service_pb2_grpc

WATCH_DIR = os.getenv("WATCH_DIR", "/tmp/images")
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "5"))
CATALOG_DIR = Path(os.getenv("CATALOG_DIR", os.path.join(WATCH_DIR, "catalog")))
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))

# Logger-Formatierung für gute Lesbarkeit auf der Hörsaal-Leinwand
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - \033[1;34m[Orchestrator]\033[0m %(message)s",
)
logger = logging.getLogger(__name__)

CONCURRENCY = int(os.getenv("CONCURRENCY", "5"))
sem = asyncio.Semaphore(CONCURRENCY)

# Die gRPC-Endpunkte der Docker-Container
WORKERS = {
    "Worker_Tags": "worker_tags:50051",
    "Worker_Thumbnails": "worker_thumbnails:50052",
    "Worker_Embeddings": "dns:///worker_embeddings:50053",
}

SAGA_PENDING = "PENDING"
SAGA_DOWNLOADED = "DOWNLOADED"
SAGA_WORKERS_COMPLETED = "WORKERS_COMPLETED"
SAGA_COMMITTED = "COMMITTED"
SAGA_RETRY = "RETRY"


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


async def process_image_pipeline(task_id: str, img_path: str):
    """Run the image-level saga and return a committed catalog result."""
    source_path = img_path
    saga_state = {"task_id": task_id, "source_path": source_path, "state": SAGA_PENDING}
    logger.info("===========================================================")
    logger.info(f"🚀 STARTE BILD-SAGA (TX-ID: {task_id})")
    logger.info("===========================================================")

    # download the image using java_api REST endpoint download_file
    async with aiohttp.ClientSession() as session:
        async with session.get(
            "http://java-api:8080/download_file", params={"path": img_path}
        ) as resp:
            if resp.status != 200:
                saga_state["state"] = SAGA_RETRY
                logger.error(
                    f"❌ Download fehlgeschlagen für {img_path}: HTTP {resp.status}"
                )
                return {
                    "status": "FAILED",
                    "source_path": source_path,
                    "saga": saga_state,
                }
            logger.info(f"⬇️ Download erfolgreich für {img_path}")

    # Workaround!
    img_path = os.path.join(WATCH_DIR, os.path.basename(img_path))
    saga_state["state"] = SAGA_DOWNLOADED

    # check if file exists
    if not os.path.exists(img_path):
        saga_state["state"] = SAGA_RETRY
        logger.error(f"❌ Datei existiert nicht: {img_path}")
        return {"status": "FAILED", "source_path": source_path, "saga": saga_state}

    # gRPC-Request-Objekt bauen
    request = service_pb2.TaskRequest(task_id=task_id, img_path=img_path)

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
            raise RuntimeError(f"Worker failure for {task_id}")
        logger.info(
            "🎉 \033[1;32mBILD-SAGA ERFOLGREICH!\033[0m Alle Worker-Schritte sind abgeschlossen."
        )
        saga_state["state"] = SAGA_WORKERS_COMPLETED

        return {
            "status": "COMPLETED",
            "image_path": img_path,
            "metadata": json.loads(tag_response.metadata_json),
            "embedding": list(embedding_response.embedding),
            "thumbnail_path": thumbnail_response.thumbnail_path,
            "saga": saga_state,
        }

    except Exception as e:
        saga_state["state"] = SAGA_RETRY
        thumbnail_path = os.path.join(
            WATCH_DIR,
            "thumbnails",
            f"{Path(img_path).stem}_thumb.jpg",
        )
        if os.path.exists(thumbnail_path):
            os.remove(thumbnail_path)
        logger.error(f"💥 GLOBALER PIPELINE-ABBRUCH! Fehlerursache: {str(e)}")
        return {
            "status": "FAILED",
            "source_path": source_path,
            "saga": saga_state,
        }


def write_catalog_batch(results):
    """Persist completed worker results as one immutable Parquet batch."""
    rows = []
    for result in results:
        image_path = result["image_path"]
        image_id = os.path.basename(image_path)

        with open(image_path, "rb") as image_file:
            content_hash = hashlib.sha256(image_file.read()).hexdigest()

        rows.append(
            {
                "image_id": image_id,
                "content_hash": content_hash,
                "filename": image_id,
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
    temporary_path = CATALOG_DIR / f".{batch_name}.tmp"
    table = pa.Table.from_pylist(rows)
    pq.write_table(table, temporary_path, compression="zstd")
    os.replace(temporary_path, batch_path)
    manifest = {
        "version": batch_name,
        "batches": [
            f"catalog/{path.name}" for path in sorted(CATALOG_DIR.glob("*.parquet"))
        ],
    }
    manifest_path = CATALOG_DIR / "manifest.json"
    manifest_temporary_path = CATALOG_DIR / ".manifest.json.tmp"
    manifest_temporary_path.write_text(json.dumps(manifest, indent=2) + "\n")
    os.replace(manifest_temporary_path, manifest_path)
    logger.info("Wrote catalog batch %s with %d image(s)", batch_path, len(rows))


def catalog_image_ids():
    image_ids = set()
    for batch_path in CATALOG_DIR.glob("*.parquet"):
        table = pq.read_table(batch_path, columns=["image_id"])
        image_ids.update(table["image_id"].to_pylist())
    return image_ids


async def watch_and_process():
    """Überwacht WATCH_DIR auf neue JPG-Dateien und verarbeitet sie."""
    logger.info(
        f"👀 Listener gestartet. Überwache {WATCH_DIR} (alle {POLL_INTERVAL}s, max. Retries: {MAX_RETRIES})..."
    )
    retry_counts = {}
    skipped_image_ids = set()

    while True:
        csv_list_file = os.path.join(WATCH_DIR, "list_files.csv")

        if os.path.exists(csv_list_file):
            logger.info(f"📂 CSV-Datei gefunden: {csv_list_file}")

            async def process_with_limit(task_id, img_path):
                async with sem:
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
                                "state": SAGA_RETRY,
                                "error": str(error),
                            },
                        }

            saga_tasks = []
            existing_image_ids = catalog_image_ids()
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
                    if task_id in skipped_image_ids:
                        logger.info(
                            f"⏭️ Überspringe dauerhaft fehlgeschlagenes Bild: {task_id}"
                        )
                        continue
                    saga_tasks.append(process_with_limit(task_id, img_path))

            results = await asyncio.gather(*saga_tasks)
            completed_results = [
                result
                for result in results
                if isinstance(result, dict) and result.get("status") == "COMPLETED"
            ]
            if completed_results:
                write_catalog_batch(completed_results)
                for result in completed_results:
                    result["saga"]["state"] = SAGA_COMMITTED
                    os.remove(result["image_path"])
                    logger.info(f"🗑️ {result['image_path']} gelöscht.")
                    retry_counts.pop(result["source_path"], None)

            failed_paths = []
            for result in results:
                if isinstance(result, dict) and result.get("status") == "FAILED":
                    src_path = result["source_path"]
                    task_id = os.path.basename(src_path)
                    count = retry_counts.get(src_path, 0) + 1
                    retry_counts[src_path] = count

                    if count < MAX_RETRIES:
                        logger.warning(
                            f"⚠️ Versuch {count}/{MAX_RETRIES} fehlgeschlagen für {src_path}. Erneuter Versuch folgt."
                        )
                        failed_paths.append(src_path)
                    else:
                        logger.error(
                            f"❌ Max. Retries ({MAX_RETRIES}) erreicht für {src_path}. Bild wird übersprungen."
                        )
                        skipped_image_ids.add(task_id)
                        retry_counts.pop(src_path, None)
                        local_file = os.path.join(WATCH_DIR, task_id)
                        if os.path.exists(local_file):
                            try:
                                os.remove(local_file)
                                logger.info(f"🗑️ Lokale Datei {local_file} gelöscht.")
                            except Exception as e:
                                logger.error(
                                    f"Fehler beim Löschen von {local_file}: {e}"
                                )

            if failed_paths:
                retry_path = f"{csv_list_file}.retry"
                with open(retry_path, "w", newline="") as retry_file:
                    writer = csv.writer(retry_file)
                    writer.writerows([[path] for path in failed_paths])
                os.replace(retry_path, csv_list_file)
                logger.warning(
                    f"🔁 {len(failed_paths)} Bild(er) bleiben für einen Retry in {csv_list_file}."
                )
            else:
                os.remove(csv_list_file)
                logger.info(f"🗑️ {csv_list_file} gelöscht.")

        await asyncio.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    try:
        asyncio.run(watch_and_process())
    except KeyboardInterrupt:
        print("\nOrchestrator beendet.")
