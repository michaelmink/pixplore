import pulumi
import pulumi_docker as docker
from services import network
from services.opentelemetry_collector import otel_collector_container

import os

_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.join(_dir, "..")

prometheus_container = docker.Container(
    "prometheus",
    name="prometheus",
    image="prom/prometheus:v2.53.0",
    ports=[docker.ContainerPortArgs(internal=9090, external=9090)],
    command=[
        "--config.file=/etc/prometheus/prometheus.yml",
        "--web.enable-lifecycle",
    ],
    volumes=[
        docker.ContainerVolumeArgs(
            host_path=os.path.join(_project_root, "prometheus.yml"),
            container_path="/etc/prometheus/prometheus.yml",
        )
    ],
    networks_advanced=[docker.ContainerNetworksAdvancedArgs(name=network.name)],
    opts=pulumi.ResourceOptions(depends_on=[otel_collector_container]),
)
