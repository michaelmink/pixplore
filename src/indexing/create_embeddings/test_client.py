import grpc
import service_pb2
import service_pb2_grpc
import chromadb
import os


def run():
    channel = grpc.insecure_channel("localhost:50053")
    stub = service_pb2_grpc.WorkerServiceStub(channel)

    response = stub.ProcessTask(
        service_pb2.TaskRequest(
            task_id="20250415_173150.jpg",
            img_path="/tmp/images/20250415_173150.jpg"
        )
    )
    print(f"Status: {response.status}, Record ID: {response.db_record_id}")

    # read embedding for task_id from chromadb to verify
    CHROMA_HOST = os.getenv("CHROMA_HOST", "localhost")
    client = chromadb.HttpClient(host=CHROMA_HOST, port=8000)
    collection = client.get_or_create_collection(
        "image_embeddings",
        metadata={"hnsw:space": "cosine"}
    )
    result = collection.get(ids=["20250415_173150.jpg"], include=["embeddings"])
    print(f"Embedding shape: {len(result['embeddings'][0])}d")
    print(f"First 5 values: {result['embeddings'][0][:5]}")



if __name__ == "__main__":
    run()
