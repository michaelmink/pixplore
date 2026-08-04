import os
import asyncio
import logging
import grpc
from PIL import Image
import chromadb

import service_pb2
import service_pb2_grpc
from embedding import Blip2Embedder

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EmbeddingWorker(service_pb2_grpc.WorkerServiceServicer):

    def __init__(self):
        CHROMA_HOST = os.getenv("CHROMA_HOST", "localhost")
        client = chromadb.HttpClient(host=CHROMA_HOST, port=8000)
        self.collection = client.get_or_create_collection(
            "image_embeddings",
            metadata={"hnsw:space": "cosine"}
        )
        self.embedder = Blip2Embedder()

    async def ProcessTask(self, request, context):
        logger.info(f"Got task: {request.task_id} | img_path: {request.img_path}")

        if not os.path.exists(request.img_path):
            logger.error(f"File not found: {request.img_path}")
            return service_pb2.TaskResponse(status="FAILED", db_record_id="")

        try:
            image = Image.open(request.img_path).convert("RGB")
            image_file_name = os.path.basename(request.img_path)

            # check idempotency
            existing = self.collection.get(ids=[image_file_name])
            if existing and existing["ids"]:
                logger.info(f"Already exists: {image_file_name}")
                return service_pb2.TaskResponse(status="ALREADY_EXISTS", db_record_id=image_file_name)

            embedding = self.embedder.embed_image(image)

            self.collection.add(
                ids=[image_file_name],
                embeddings=[embedding.tolist()],
                documents=[image_file_name]
            )

            logger.info(f"Stored embedding for {image_file_name}")
            return service_pb2.TaskResponse(status="COMPLETED", db_record_id=image_file_name)

        except Exception as e:
            logger.error(f"Error processing image: {e}")
            return service_pb2.TaskResponse(status="FAILED", db_record_id="")

    async def CompensateTask(self, request, context):
        logger.info(f"Compensate: {request.task_id} | record: {request.db_record_id}")
        try:
            self.collection.delete(ids=[request.db_record_id])
            return service_pb2.CompensateResponse(status="ROLLED_BACK")
        except Exception as e:
            logger.error(f"Compensation failed: {e}")
            return service_pb2.CompensateResponse(status="NOT_FOUND")


async def main():
    server = grpc.aio.server()
    service_pb2_grpc.add_WorkerServiceServicer_to_server(EmbeddingWorker(), server)
    server.add_insecure_port("[::]:50053")
    await server.start()
    logger.info("Embedding worker running on :50053")
    await server.wait_for_termination()


if __name__ == "__main__":
    asyncio.run(main())
