import pulumi
import pulumi_docker as docker
from services import network
from services.chromadb import chromadb_container

# --- worker_tags ---
worker_tags_image = docker.Image(
    "worker-tags-image",
    image_name="pixplore/worker-tags:latest",
    build=docker.DockerBuildArgs(context="../../src/indexing/create_tags"),
    skip_push=True,
)

worker_tags_container = docker.Container(
    "worker-tags",
    name="worker_tags",
    image=worker_tags_image.image_name,
    ports=[docker.ContainerPortArgs(internal=50051, external=50051)],
    envs=[
        "CHROMA_HOST=chromadb",
        "OTEL_SERVICE_NAME=worker_tags",
        "OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317",
    ],
    volumes=[
        docker.ContainerVolumeArgs(
            host_path="/tmp/images", container_path="/tmp/images"
        )
    ],
    networks_advanced=[docker.ContainerNetworksAdvancedArgs(name=network.name)],
    opts=pulumi.ResourceOptions(depends_on=[chromadb_container]),
)

# --- worker_thumbnails ---
worker_thumbnails_image = docker.Image(
    "worker-thumbnails-image",
    image_name="pixplore/worker-thumbnails:latest",
    build=docker.DockerBuildArgs(context="../../src/indexing/create_thumbnails"),
    skip_push=True,
)

worker_thumbnails_container = docker.Container(
    "worker-thumbnails",
    name="worker_thumbnails",
    image=worker_thumbnails_image.image_name,
    ports=[docker.ContainerPortArgs(internal=50052, external=50052)],
    envs=[
        "OTEL_SERVICE_NAME=worker_thumbnails",
        "OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317",
    ],
    volumes=[
        docker.ContainerVolumeArgs(
            host_path="/tmp/images", container_path="/tmp/images"
        ),
        docker.ContainerVolumeArgs(
            host_path="/tmp/images/thumbnails", container_path="/tmp/images/thumbnails"
        ),
    ],
    networks_advanced=[docker.ContainerNetworksAdvancedArgs(name=network.name)],
)

# --- worker_embeddings (5 replicas in compose, hier 1 Container) ---
worker_embeddings_image = docker.Image(
    "worker-embeddings-image",
    image_name="pixplore/worker-embeddings:latest",
    build=docker.DockerBuildArgs(context="../../src/indexing/create_embeddings"),
    skip_push=True,
)

worker_embeddings_container = docker.Container(
    "worker-embeddings",
    name="worker_embeddings",
    image=worker_embeddings_image.image_name,
    envs=[
        "CHROMA_HOST=chromadb",
        "OTEL_SERVICE_NAME=worker_embeddings",
        "OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317",
    ],
    volumes=[
        docker.ContainerVolumeArgs(
            host_path="/tmp/images", container_path="/tmp/images"
        )
    ],
    networks_advanced=[docker.ContainerNetworksAdvancedArgs(name=network.name)],
    opts=pulumi.ResourceOptions(depends_on=[chromadb_container]),
)
