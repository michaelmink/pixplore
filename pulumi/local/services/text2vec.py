import pulumi_docker as docker
from services import network

text2vec_image = docker.Image(
    "text2vec-image",
    image_name="pixplore/text2vec:latest",
    build=docker.DockerBuildArgs(context="../../src/text2vec"),
    skip_push=True,
)

text2vec_container = docker.Container(
    "text2vec",
    name="text2vec",
    image=text2vec_image.repo_digest,
    ports=[docker.ContainerPortArgs(internal=8081, external=8090)],
    envs=[
        "OTEL_SERVICE_NAME=text2vec",
        "OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317",
    ],
    networks_advanced=[docker.ContainerNetworksAdvancedArgs(name=network.name)],
)
