# In einer neuen Datei services/jaeger.py
import pulumi_docker as docker
from services import network

jaeger_container = docker.Container(
    "jaeger",
    name="jaeger",
    image="jaegertracing/all-in-one:1.58",
    ports=[
        docker.ContainerPortArgs(internal=16686, external=16686),  # UI
        docker.ContainerPortArgs(
            internal=4317, external=14317
        ),  # OTLP gRPC (anderer externer Port)
        docker.ContainerPortArgs(internal=4318, external=14318),  # OTLP HTTP
    ],
    envs=["COLLECTOR_OTLP_ENABLED=true"],
    networks_advanced=[docker.ContainerNetworksAdvancedArgs(name=network.name)],
)
