#!/bin/sh
set -eu

if [ "${CATALOG_MODE:-auto}" = "parquet" ]; then
	python /initialize.py
	exec chroma run --host 0.0.0.0 --port 8000 --path /tmp/chroma
fi

exec chroma run --host 0.0.0.0 --port 8000 --path /data
