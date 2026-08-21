FROM python:3.12-slim

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY . .

RUN uv run opentelemetry-bootstrap -a requirements | uv pip install -r -

CMD ["uv", "run", "opentelemetry-instrument", "streamlit", "run", "start_server.py"]
