import grpc
import grpc.aio
import asyncio
import service_pb2
import service_pb2_grpc
import os
from PIL import Image


# setup grpc server
def serve():
    server = grpc.aio.server()
    service_pb2_grpc.add_WorkerServiceServicer_to_server(WorkerService(), server)
    server.add_insecure_port("[::]:50052")
    return server


class WorkerService(service_pb2_grpc.WorkerServiceServicer):
    async def ProcessTask(self, request, context):
        """
        gRPC-Methode zum Erstellen eines Thumbnails.
        """
        img_path = request.img_path
        thumbnail_dir = os.path.join(os.path.dirname(img_path), "thumbnails")
        os.makedirs(thumbnail_dir, exist_ok=True)

        task_id = request.task_id

        thumbnail_path = os.path.join(
            thumbnail_dir, os.path.basename(img_path).rsplit(".", 1)[0] + "_thumb.jpg"
        )

        try:
            with Image.open(img_path) as img:
                img.thumbnail((1024, 1024))
                img.save(thumbnail_path)
                print(f"✅ Thumbnail erstellt: {thumbnail_path}")
                return service_pb2.TaskResponse(
                    status="COMPLETED", db_record_id=task_id
                )
        except Exception as e:
            print(f"❌ Fehler beim Erstellen des Thumbnails für {img_path}: {e}")
            return service_pb2.TaskResponse(status="FAILED", db_record_id=task_id)


if __name__ == "__main__":
    server = serve()
    loop = asyncio.get_event_loop()
    loop.run_until_complete(server.start())
    print("gRPC-Server Worker Thumbnails läuft auf Port 50052...")
    loop.run_forever()
