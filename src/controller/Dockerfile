FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y build-essential && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY . .

RUN uv run opentelemetry-bootstrap -a requirements | uv pip install -r -

RUN uv run python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. service.proto

USER 1000:1000

ENV UV_NO_CACHE=1

CMD ["uv", "run", "opentelemetry-instrument", "python", "controller.py"]
