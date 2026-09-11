FROM python:3.12-slim

WORKDIR /app

RUN apt-get update \
  && apt-get install -y --no-install-recommends curl \
  && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir chromadb==1.5.9 pyarrow "pyiceberg[gcsfs,sql-sqlite]"

COPY initialize.py /initialize.py
COPY start.sh /start.sh
RUN chmod +x /start.sh

ENTRYPOINT ["/start.sh"]

HEALTHCHECK --interval=10s --timeout=3s --start-period=5s \
  CMD curl -f http://localhost:8000/api/v2/heartbeat || exit 1
