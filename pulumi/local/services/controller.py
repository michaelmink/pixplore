import pulumi
import pulumi_docker as docker
from services import network
from services.java_api import java_api_container
from services.worker import (
    worker_tags_container,
    worker_thumbnails_container,
    worker_embeddings_container,
)

controller_image = docker.Image(
    "controller-image",
    image_name="pixplore/controller:latest",
    build=docker.DockerBuildArgs(context="../../src/controller"),
    skip_push=True,
)

controller_container = docker.Container(
    "controller",
    name="controller",
    image=controller_image.image_name,
    user="0:0",
    envs=[
        "WATCH_DIR=/tmp/images",
        "CONCURRENCY=5",
        "OTEL_SERVICE_NAME=controller",
        "OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317",
        "OTEL_LOGS_EXPORTER=none",
        "JAVA_API_URL=http://java_api:8080",
        "WORKER_TAGS_ADDR=worker_tags:50051",
        "WORKER_THUMBNAILS_ADDR=worker_thumbnails:50052",
        "WORKER_EMBEDDINGS_ADDR=dns:///worker_embeddings:50053",
    ],
    volumes=[
        docker.ContainerVolumeArgs(
            host_path="/tmp/images", container_path="/tmp/images"
        )
    ],
    networks_advanced=[docker.ContainerNetworksAdvancedArgs(name=network.name)],
    opts=pulumi.ResourceOptions(
        depends_on=[
            java_api_container,
            worker_tags_container,
            worker_thumbnails_container,
            worker_embeddings_container,
            controller_image,
            network,
        ]
    ),
)
