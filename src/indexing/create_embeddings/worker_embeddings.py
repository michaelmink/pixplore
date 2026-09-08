import os
import asyncio
import logging
import grpc
from PIL import Image

import service_pb2
import service_pb2_grpc
from embedding import Blip2Embedder

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EmbeddingWorker(service_pb2_grpc.WorkerServiceServicer):
    def __init__(self):
        self.embedder = Blip2Embedder()

    async def ProcessTask(self, request, context):
        logger.info(f"Got task: {request.task_id} | img_path: {request.img_path}")

        if not os.path.exists(request.img_path):
            logger.error(f"File not found: {request.img_path}")
            return service_pb2.TaskResponse(status="FAILED", db_record_id="")

        try:
            image = Image.open(request.img_path).convert("RGB")
            image_file_name = os.path.basename(request.img_path)

            embedding = self.embedder.embed_image(image)

            logger.info(f"Stored embedding for {image_file_name}")
            return service_pb2.TaskResponse(
                status="COMPLETED",
                db_record_id=image_file_name,
                embedding=embedding.tolist(),
            )

        except Exception as e:
            logger.error(f"Error processing image: {e}")
            return service_pb2.TaskResponse(status="FAILED", db_record_id="")


async def main():
    server = grpc.aio.server()
    service_pb2_grpc.add_WorkerServiceServicer_to_server(EmbeddingWorker(), server)
    server.add_insecure_port("[::]:50053")
    await server.start()
    logger.info("Embedding worker running on :50053")
    await server.wait_for_termination()


if __name__ == "__main__":
    asyncio.run(main())
