FROM python:3.11-slim

WORKDIR /app

# System-Abhängigkeiten für gRPC installieren
RUN apt-get update && apt-get install -y build-essential && rm -rf /var/lib/apt/lists/*

# Python-Pakete installieren
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Quellcode kopieren
COPY . .

# Protobuf-Dateien für gRPC generieren
RUN python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. service.proto

# Der Standardbefehl wird in der docker-compose überschrieben
CMD ["python", "worker_tags.py"]