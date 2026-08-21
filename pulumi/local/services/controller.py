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
    envs=[
        "WATCH_DIR=/tmp/images",
        "CONCURRENCY=5",
        "OTEL_SERVICE_NAME=controller",
        "OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317",
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
        ]
    ),
)
