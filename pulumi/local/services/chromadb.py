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
    image=chromadb_image.image_name,
    ports=[docker.ContainerPortArgs(internal=8000, external=8000)],
    volumes=[
        docker.ContainerVolumeArgs(
            host_path="/tmp/images/vectordb",
            container_path="/data",
        )
    ],
    networks_advanced=[docker.ContainerNetworksAdvancedArgs(name=network.name)],
)
