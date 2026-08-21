FROM python:3.11-slim

WORKDIR /app

# System-Abhängigkeiten für gRPC installieren
RUN apt-get update && apt-get install -y build-essential && rm -rf /var/lib/apt/lists/*

# Python-Pakete installieren
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Quellcode kopieren
COPY . .

# Protobuf-Dateien für gRPC generieren
RUN uv run python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. service.proto

RUN uv run opentelemetry-bootstrap -a requirements | uv pip install -r -

# Der Standardbefehl wird in der docker-compose überschrieben
CMD ["uv", "run", "opentelemetry-instrument", "python", "worker_tags.py"]
