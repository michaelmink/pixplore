import asyncio
import logging
import grpc

import service_pb2
import service_pb2_grpc

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AdderService(service_pb2_grpc.AdderServicer):
    async def Add(self, request, context):
        result = request.a + request.b
        logger.info("Add(%d, %d) = %d", request.a, request.b, result)
        return service_pb2.AddResponse(result=result)


async def main():
    server = grpc.aio.server()
    service_pb2_grpc.add_AdderServicer_to_server(AdderService(), server)
    server.add_insecure_port("[::]:50051")
    await server.start()
    logger.info("Adder gRPC server running on :50051")
    await server.wait_for_termination()


if __name__ == "__main__":
    asyncio.run(main())
