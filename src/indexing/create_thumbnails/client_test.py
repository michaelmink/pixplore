import asyncio
import grpc.aio
import service_pb2
import service_pb2_grpc


async def main():
    channel = grpc.aio.insecure_channel("localhost:50051")
    stub = service_pb2_grpc.WorkerServiceStub(channel)

    images = [
        "/tmp/images/20250415_173150.jpg",
        "/tmp/images/20260122_201016.jpg",
        "/tmp/images/20260121_071024.jpg",
    ]

    for i, img in enumerate(images):
        resp = await stub.ProcessTask(
            service_pb2.TaskRequest(task_id=str(i), img_path=img)
        )
        print(f"Response: status={resp.status}, record_id={resp.db_record_id}")

    await channel.close()


if __name__ == "__main__":
    asyncio.run(main())
