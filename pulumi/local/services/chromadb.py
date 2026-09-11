import os

import pulumi
import pulumi_docker as docker
from services import network

chromadb_image = docker.Image(
    "chromadb-image",
    image_name="pixplore/chromadb:latest",
    build=docker.DockerBuildArgs(context="../../src/vectordb"),
    skip_push=True,
)

# Lokale ADC des Users in den Container reichen, damit initialize.py GCS lesen kann
adc_path = os.path.expanduser("~/.config/gcloud/application_default_credentials.json")

chromadb_container = docker.Container(
    "chromadb",
    name="chromadb",
    image=chromadb_image.image_name,
    ports=[docker.ContainerPortArgs(internal=8000, external=8000)],
    envs=[
        "CATALOG_MODE=iceberg",
        "ICEBERG_WAREHOUSE=gs://pixplore-bucket/warehouse",
        "GCS_PROJECT=pixplore-503406",
        "THUMBNAIL_PATH=/data/thumbnails",
        "GOOGLE_APPLICATION_CREDENTIALS=/gcp/adc.json",
        "CHROMA_OTEL_COLLECTION_ENDPOINT=http://otel-collector:4317",
        "CHROMA_OTEL_SERVICE_NAME=chromadb",
        "CHROMA_OTEL_COLLECTION_HEADERS={}",
        "CHROMA_OTEL_GRANULARITY=all",
    ],
    volumes=[
        docker.ContainerVolumeArgs(
            host_path="/tmp/images",
            container_path="/data",
        ),
        docker.ContainerVolumeArgs(
            host_path=adc_path,
            container_path="/gcp/adc.json",
            read_only=True,
        ),
    ],
    networks_advanced=[docker.ContainerNetworksAdvancedArgs(name=network.name)],
    opts=pulumi.ResourceOptions(depends_on=[chromadb_image, network]),
)
