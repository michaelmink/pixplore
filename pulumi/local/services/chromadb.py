import pulumi_docker as docker
from services import network

chromadb_image = docker.Image(
    "chromadb-image",
    image_name="pixplore/chromadb:latest",
    build=docker.DockerBuildArgs(context="../../src/vectordb"),
    skip_push=True,
)

chromadb_container = docker.Container(
    "chromadb",
    name="chromadb",
    image=chromadb_image.repo_digest,
    ports=[docker.ContainerPortArgs(internal=8000, external=8000)],
    envs=[
        "CHROMA_OTEL_COLLECTION_ENDPOINT=http://otel-collector:4317",
        "CHROMA_OTEL_SERVICE_NAME=chromadb",
        "CHROMA_OTEL_COLLECTION_HEADERS={}",
        "CHROMA_OTEL_GRANULARITY=all",
    ],
    volumes=[
        docker.ContainerVolumeArgs(
            host_path="/tmp/images/vectordb",
            container_path="/data",
        )
    ],
    networks_advanced=[docker.ContainerNetworksAdvancedArgs(name=network.name)],
)
