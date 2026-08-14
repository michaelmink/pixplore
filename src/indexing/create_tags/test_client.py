import grpc
import service_pb2
import service_pb2_grpc

# Verbindung zum Server
channel = grpc.insecure_channel("localhost:50051")
stub = service_pb2_grpc.WorkerServiceStub(channel)

# ProcessTask aufrufen
response = stub.ProcessTask(
    service_pb2.TaskRequest(task_id="test-001", payload="Mein erster Task")
)
print(f"Status: {response.status}, Record-ID: {response.db_record_id}")

# CompensateTask aufrufen (Rollback)
response = stub.CompensateTask(
    service_pb2.CompensateRequest(
        task_id="test-001", db_record_id="rec_TagWorker_test-001"
    )
)
print(f"Kompensation: {response.status}")
