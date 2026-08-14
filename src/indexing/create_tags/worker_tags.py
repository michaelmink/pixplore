import os
import asyncio
import logging
import grpc
from PIL import Image
from PIL.ExifTags import TAGS
import chromadb

import service_pb2
import service_pb2_grpc


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TagWorker(service_pb2_grpc.WorkerServiceServicer):
    def __init__(self):
        # chromadb connection
        CHROMA_HOST = os.getenv("CHROMA_HOST", "localhost")
        client = chromadb.HttpClient(host=CHROMA_HOST, port=8000)
        self.collection = client.get_or_create_collection("image_tags")

    async def ProcessTask(self, request, context):
        logger.info(f"Got task: {request.task_id} | img_path: {request.img_path}")

        # check if file exists
        if not os.path.exists(request.img_path):
            logger.error(f"File not found: {request.img_path}")
            return service_pb2.TaskResponse(status="FAILED", db_record_id="")

        # read EXIF data from image
        try:
            image = Image.open(request.img_path)
            image_file_name = os.path.basename(request.img_path)
            exif_data = image._getexif()
            tags = {}
            metadata = {}

            if exif_data:
                for tag_id, value in exif_data.items():
                    tag_name = TAGS.get(tag_id, tag_id)
                    tags[tag_name] = value
                    if tag_name == "DateTimeOriginal":
                        metadata["date_taken"] = value
                    if tag_name == "Model":
                        metadata["model"] = value
                    if tag_name == "GPSInfo":
                        metadata["gps_lat"] = "0"
                        metadata["gps_lon"] = "0"

            # write to db
            self.collection.add(
                ids=[image_file_name], metadatas=[metadata], documents=[image_file_name]
            )

            return service_pb2.TaskResponse(
                status="COMPLETED", db_record_id=image_file_name
            )

        except Exception as e:
            logger.error(f"Error reading EXIF data: {e}")
            return service_pb2.TaskResponse(status="FAILED", db_record_id="")

    async def CompensateTask(self, request, context):
        logger.info(f"Compensate: {request.task_id}")
        return service_pb2.CompensateResponse(status="ROLLED_BACK")


async def main():
    server = grpc.aio.server()
    service_pb2_grpc.add_WorkerServiceServicer_to_server(TagWorker(), server)
    server.add_insecure_port("[::]:50051")
    await server.start()
    logger.info("Server running on :50051")
    await server.wait_for_termination()


if __name__ == "__main__":
    asyncio.run(main())
