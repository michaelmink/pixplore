"""Pixplore Local Dev — alle Services via Docker."""

import pulumi
from services.java_api import java_api_container  # noqa: F401
from services.frontend import frontend_container  # noqa: F401
from services.chromadb import chromadb_container  # noqa: F401
from services.text2vec import text2vec_container  # noqa: F401
from services.worker import (  # noqa: F401
    worker_tags_container,
    worker_thumbnails_container,
    worker_embeddings_container,
)
from services.controller import controller_container  # noqa: F401
from services.opentelemetry_collector import otel_collector_container  # noqa: F401
from services.jaeger import jaeger_container  # noqa: F401
from services.prometheus import prometheus_container  # noqa: F401

pulumi.export("java_api_url", "http://localhost:8080")
pulumi.export("frontend_url", "http://localhost:8501")
pulumi.export("chromadb_url", "http://localhost:8000")
pulumi.export("text2vec_url", "http://localhost:8090")
pulumi.export("otel_collector_url", "http://localhost:4318")
pulumi.export("jaeger_ui", "http://localhost:16686")
pulumi.export("otel_collector_otlp", "http://localhost:4317")
pulumi.export("prometheus_metrics", "http://localhost:8889/metrics")
pulumi.export("prometheus_ui", "http://localhost:9090")
