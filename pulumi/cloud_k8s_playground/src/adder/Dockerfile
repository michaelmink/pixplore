FROM python:3.12-slim
WORKDIR /app

RUN pip install --no-cache-dir grpcio grpcio-tools

COPY service.proto .
RUN python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. service.proto

COPY main.py .
EXPOSE 50051
CMD ["python", "main.py"]
