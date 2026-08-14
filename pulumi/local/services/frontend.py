import pulumi
import pulumi_docker as docker
from services import network
from services.java_api import java_api_container
from services.text2vec import text2vec_container

frontend_image = docker.Image(
    "frontend-image",
    image_name="pixplore/frontend:latest",
    build=docker.DockerBuildArgs(context="../../src/frontend"),
    skip_push=True,
)

frontend_container = docker.Container(
    "frontend",
    name="frontend",
    image=frontend_image.image_name,
    ports=[docker.ContainerPortArgs(internal=8501, external=8501)],
    envs=[
        "BASE_PATH=/tmp/images",
        "TEXT2VEC_URL=http://text2vec:8081",
    ],
    volumes=[
        docker.ContainerVolumeArgs(
            host_path="/tmp/images", container_path="/tmp/images"
        )
    ],
    networks_advanced=[docker.ContainerNetworksAdvancedArgs(name=network.name)],
    opts=pulumi.ResourceOptions(depends_on=[java_api_container, text2vec_container]),
)
