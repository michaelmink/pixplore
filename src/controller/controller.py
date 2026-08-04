import asyncio
import glob
import logging
import os
import grpc
import csv
import aiohttp

# Importiere die vom Dockerfile generierten Protobuf-Stubs
import service_pb2
import service_pb2_grpc

WATCH_DIR = os.getenv("WATCH_DIR", "/tmp/images")
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "5"))

# Logger-Formatierung für gute Lesbarkeit auf der Hörsaal-Leinwand
logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s - \033[1;34m[Orchestrator]\033[0m %(message)s"
)
logger = logging.getLogger(__name__)

CONCURRENCY = int(os.getenv("CONCURRENCY", "5"))
sem = asyncio.Semaphore(CONCURRENCY)

# Die gRPC-Endpunkte der Docker-Container (lokal gemappt via docker-compose)
WORKERS = {
    "Worker_Tags": "localhost:50051",
    "Worker_Thumbnails": "localhost:50052",
    "Worker_Embeddings": "dns:///embedding-worker:50053",
}

async def execute_forward_step(worker_name: str, addr: str, req: service_pb2.TaskRequest):
    """
    Führt den vorwärtsgerichteten RPC-Aufruf aus (Forward Transaction).
    Registriert den Erfolg im Saga-Log des Orchestrators.
    """
    logger.info(f"📡 Sende Task {req.task_id} an \033[1;32m{worker_name}\033[0m ({addr})...")
    
    async with grpc.aio.insecure_channel(addr) as channel:
        stub = service_pb2_grpc.WorkerServiceStub(channel)

        # RPC ausführen mit einem harten Timeout von 3 Sekunden
        response = await stub.ProcessTask(req)
        
        # WICHTIG: Erhaltene Record-ID sofort im In-Memory Saga-Log sichern
        logger.info(f"✅ \033[1;32m{worker_name}\033[0m meldet Erfolg. Record-ID gemerkt: {response.db_record_id}")
        return response

async def execute_compensating_step(worker_name: str, addr: str, task_id: str, record_id: str):
    """
    Führt die rückwärtsgerichtete Kompensation aus (Compensating Transaction).
    Löscht oder storniert den Eintrag in der DB des betroffenen Workers.
    """
    logger.warning(f"🚨 Sende Kompensation an \033[1;33m{worker_name}\033[0m für Record {record_id}...")
    
    async with grpc.aio.insecure_channel(addr) as channel:
        stub = service_pb2_grpc.WorkerServiceStub(channel)
        req = service_pb2.CompensateRequest(task_id=task_id, db_record_id=record_id)
        
        response = await stub.CompensateTask(req, timeout=3.0)
        logger.warning(f"↩️ \033[1;33m{worker_name}\033[0m erfolgreich kompensiert! Status: {response.status}")
        return response

async def run_saga_orchestrator(task_id: str, img_path: str):
    """
    Der zentrale Saga-Souverän. Er steuert Forward und Backward Recovery.
    """
    logger.info(f"===========================================================")
    logger.info(f"🚀 STARTE GLOBALEN SAGA-WORKFLOW (TX-ID: {task_id})")
    logger.info(f"===========================================================")

    # download the image using java_api REST endpoint download_file
    async with aiohttp.ClientSession() as session:
        async with session.get("http://localhost:8080/download_file", params={"path": img_path}) as resp:
            if resp.status != 200:
                logger.error(f"❌ Download fehlgeschlagen für {img_path}: HTTP {resp.status}")
                return
            logger.info(f"⬇️ Download erfolgreich für {img_path}")

    # TODO: Workaround!
    img_path = os.path.join(WATCH_DIR, os.path.basename(img_path))

    # check if file exists
    if not os.path.exists(img_path):
        logger.error(f"❌ Datei existiert nicht: {img_path}")
        return

    # gRPC-Request-Objekt bauen
    request = service_pb2.TaskRequest(task_id=task_id, img_path=img_path)
    
    # Erstelle die parallelen Coroutinen
    tasks = [
        execute_forward_step("Worker_Tags", WORKERS["Worker_Tags"], request),
        execute_forward_step("Worker_Thumbnails", WORKERS["Worker_Thumbnails"], request),
        execute_forward_step("Worker_Embeddings", WORKERS["Worker_Embeddings"], request),
    ]
    
    try:
        # Scatter-Phase: Alle 3 Worker arbeiten zeitgleich
        # return_exceptions=False sorgt für sofortigen Abbruch beim ersten Fehler!
        await asyncio.gather(*tasks, return_exceptions=False)
        logger.info("🎉 \033[1;32mGLOBALER ERFOLG!\033[0m Alle Microservices sind persistent konsistent.")

        # Nach erfolgreicher Verarbeitung löschen
        os.remove(img_path)
        logger.info(f"🗑️ {img_path} gelöscht.")
        
    except Exception as e:
        # Gather-Phase im Fehlerfall: Backward Recovery wird eingeleitet
        logger.error(f"💥 GLOBALER PIPELINE-ABBRUCH! Fehlerursache: {str(e)}")
        logger.error("⚡ Einleitung des Backward Recovery (Saga Kompensation)...")
        
        # Erstelle Kompensations-Aufrufe NUR für Worker, die bereits Daten geschrieben haben
        compensations = []
        for committed_worker, record_id in saga_log.items():
            compensations.append(
                execute_compensating_step(
                    committed_worker, 
                    WORKERS[committed_worker], 
                    task_id, 
                    record_id
                )
            )
        
        if compensations:
            # Führe alle notwendigen Kompensationen parallel aus
            await asyncio.gather(*compensations)
            logger.warning("⚖️ Das verteilte System ist wieder sauber bereinigt (Eventually Consistent).")
        else:
            logger.info("Keine Kompensation nötig. Kein Worker hatte Daten committed.")

async def watch_and_process():
    """Überwacht WATCH_DIR auf neue JPG-Dateien und verarbeitet sie."""
    logger.info(f"👀 Listener gestartet. Überwache {WATCH_DIR} (alle {POLL_INTERVAL}s)...")

    while True:
        csv_list_file = os.path.join(WATCH_DIR, "list_files.csv")

        if os.path.exists(csv_list_file):
            logger.info(f"📂 CSV-Datei gefunden: {csv_list_file}")

            async def process_with_limit(task_id, img_path):
                async with sem:
                    await run_saga_orchestrator(task_id, img_path)

            saga_tasks = []
            with open(csv_list_file, newline='') as csvfile:
                reader = csv.reader(csvfile)
                for i, img_path in enumerate(reader):
                    img_path = img_path[0]

                    if not img_path.lower().endswith(('.jpg', '.jpeg')):
                        logger.info(f"⚠️ Überspringe nicht-JPG-Datei: {img_path}")
                        continue
                    
                    task_id = os.path.basename(img_path)
                    saga_tasks.append(process_with_limit(task_id, img_path))

            results = await asyncio.gather(*saga_tasks, return_exceptions=True)
            for r in results:
                if isinstance(r, Exception):
                    logger.error(f"SAGA fehlgeschlagen: {r}")

            os.remove(csv_list_file)
            logger.info(f"🗑️ CSV-Datei {csv_list_file} gelöscht.")

        await asyncio.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    try:
        asyncio.run(watch_and_process())
    except KeyboardInterrupt:
        print("\nOrchestrator beendet.")
