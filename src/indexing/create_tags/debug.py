import asyncio
import service_pb2
from worker_tags import SqliteSagaWorker
from unittest.mock import MagicMock


async def test():
    worker = SqliteSagaWorker("TestWorker", ":memory:")  # In-Memory DB
    await worker.init_db()

    # Mock gRPC context
    ctx = MagicMock()

    # ProcessTask testen
    req = service_pb2.TaskRequest(task_id="test-1", payload="mock_image.jpg")
    resp = await worker.ProcessTasks(req, ctx)
    print(f"Status: {resp.status}, Record: {resp.db_record_id}")

    # Duplikat testen (Idempotenz)
    resp2 = await worker.ProcessTasks(req, ctx)
    print(f"Duplikat: {resp2.status}")


asyncio.run(test())
