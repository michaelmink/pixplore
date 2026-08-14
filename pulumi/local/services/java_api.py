import pulumi
import pulumi_docker as docker
from services import network

config = pulumi.Config()
pcloud_username = config.require_secret("pcloud-username")
pcloud_password = config.require_secret("pcloud-password")

java_api_image = docker.Image(
    "java-api-image",
    image_name="pixplore/java-api:latest",
    build=docker.DockerBuildArgs(context="../../src/sync_images/pcloud-java"),
    skip_push=True,
)

java_api_container = docker.Container(
    "java-api",
    name="java-api",
    image=java_api_image.image_name,
    ports=[docker.ContainerPortArgs(internal=8080, external=8080)],
    envs=[
        pcloud_username.apply(lambda u: f"PCLOUD_USERNAME={u}"),
        pcloud_password.apply(lambda p: f"PCLOUD_PASSWORD={p}"),
        "PCLOUD_DOWNLOAD_PATH=/tmp/images",
    ],
    volumes=[
        docker.ContainerVolumeArgs(
            host_path="/tmp/images", container_path="/tmp/images"
        )
    ],
    networks_advanced=[docker.ContainerNetworksAdvancedArgs(name=network.name)],
)
