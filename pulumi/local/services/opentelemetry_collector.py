import pulumi_docker as docker
from services import network

import os

_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.join(_dir, "..")


otel_collector_container = docker.Container(
    "otel-collector",
    name="otel-collector",
    image="otel/opentelemetry-collector-contrib:0.104.0",
    command=["--config=/etc/otelcol-contrib/config.yaml"],
    ports=[
        docker.ContainerPortArgs(internal=4317, external=4317),
        docker.ContainerPortArgs(internal=4318, external=4318),
        docker.ContainerPortArgs(internal=8889, external=8889),
    ],
    volumes=[
        docker.ContainerVolumeArgs(
            host_path=os.path.join(_project_root, "otel-collector-config.yaml"),
            container_path="/etc/otelcol-contrib/config.yaml",
        )
    ],
    networks_advanced=[docker.ContainerNetworksAdvancedArgs(name=network.name)],
)
