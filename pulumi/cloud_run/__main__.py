"""Pixplore Cloud Run Deployment — frontend, text2vec, chromadb."""

import pulumi
import pulumi_gcp as gcp
import pulumi_docker_build as docker_build

config = pulumi.Config()
gcp_config = pulumi.Config("gcp")

PROJECT = gcp_config.require("project")
REGION = gcp_config.require("region")
REGISTRY_REGION = config.get("registry-region") or "europe-west3"
BUCKET_NAME = config.require("bucket-name")
CATALOG_VERSION = config.get("catalog-version") or "initial"
ADMIN_EMAIL = config.require("admin-email")
PARTNER_EMAIL = config.require("partner-email")

REGISTRY = f"{REGISTRY_REGION}-docker.pkg.dev/{PROJECT}/pixplore-registry"

# ---------------------------------------------------------------------------
# Docker Images — build & push to Artifact Registry
# ---------------------------------------------------------------------------
gcp_auth = gcp.organizations.get_client_config()

docker_registry = docker_build.RegistryArgs(
    address=f"{REGISTRY_REGION}-docker.pkg.dev",
    username="oauth2accesstoken",
    password=gcp_auth.access_token,
)

text2vec_image = docker_build.Image(
    "text2vec-image",
    context=docker_build.BuildContextArgs(location="../../src/text2vec"),
    tags=[f"{REGISTRY}/text2vec:latest"],
    push=True,
    registries=[docker_registry],
)

frontend_image = docker_build.Image(
    "frontend-image",
    context=docker_build.BuildContextArgs(location="../../src/frontend"),
    tags=[f"{REGISTRY}/frontend:latest"],
    push=True,
    registries=[docker_registry],
)

chromadb_image = docker_build.Image(
    "chromadb-image",
    context=docker_build.BuildContextArgs(location="../../src/vectordb"),
    tags=[f"{REGISTRY}/chromadb:latest"],
    push=True,
    registries=[docker_registry],
)

# ---------------------------------------------------------------------------
# Service Accounts — one per service for least-privilege IAM
# ---------------------------------------------------------------------------
frontend_sa = gcp.serviceaccount.Account(
    "frontend-sa",
    account_id="pixplore-frontend",
    display_name="Pixplore Frontend (Cloud Run)",
)

chromadb_sa = gcp.serviceaccount.Account(
    "chromadb-sa",
    account_id="pixplore-chromadb",
    display_name="Pixplore ChromaDB (Cloud Run)",
)

text2vec_sa = gcp.serviceaccount.Account(
    "text2vec-sa",
    account_id="pixplore-text2vec",
    display_name="Pixplore Text2Vec (Cloud Run)",
)

# ChromaDB reads catalog batches from GCS during startup
gcp.storage.BucketIAMMember(
    "chromadb-bucket-reader",
    bucket=BUCKET_NAME,
    role="roles/storage.objectViewer",
    member=chromadb_sa.email.apply(lambda e: f"serviceAccount:{e}"),
)

# Frontend needs read-only access to GCS bucket (thumbnails)
gcp.storage.BucketIAMMember(
    "frontend-bucket-reader",
    bucket=BUCKET_NAME,
    role="roles/storage.objectViewer",
    member=frontend_sa.email.apply(lambda e: f"serviceAccount:{e}"),
)

# ---------------------------------------------------------------------------
# ChromaDB — Cloud Run Service (persistent via GCS FUSE)
# ---------------------------------------------------------------------------
chromadb_service = gcp.cloudrunv2.Service(
    "chromadb-service",
    name="chromadb",
    location=REGION,
    deletion_protection=False,
    ingress="INGRESS_TRAFFIC_ALL",
    template=gcp.cloudrunv2.ServiceTemplateArgs(
        service_account=chromadb_sa.email,
        scaling=gcp.cloudrunv2.ServiceTemplateScalingArgs(
            min_instance_count=0,
            max_instance_count=1,
        ),
        containers=[
            gcp.cloudrunv2.ServiceTemplateContainerArgs(
                image=chromadb_image.ref,
                ports=gcp.cloudrunv2.ServiceTemplateContainerPortsArgs(
                    container_port=8000,
                ),
                resources=gcp.cloudrunv2.ServiceTemplateContainerResourcesArgs(
                    limits={"memory": "2Gi", "cpu": "1"},
                ),
                envs=[
                    gcp.cloudrunv2.ServiceTemplateContainerEnvArgs(
                        name="CATALOG_MODE",
                        value="iceberg",
                    ),
                    gcp.cloudrunv2.ServiceTemplateContainerEnvArgs(
                        name="ICEBERG_WAREHOUSE",
                        value=f"gs://{BUCKET_NAME}/warehouse",
                    ),
                    gcp.cloudrunv2.ServiceTemplateContainerEnvArgs(
                        name="GCS_PROJECT",
                        value=PROJECT,
                    ),
                    gcp.cloudrunv2.ServiceTemplateContainerEnvArgs(
                        name="MATERIALIZE_THUMBNAILS",
                        value="false",
                    ),
                ],
                volume_mounts=[
                    gcp.cloudrunv2.ServiceTemplateContainerVolumeMountArgs(
                        name="gcs-data",
                        mount_path="/data",
                    )
                ],
            )
        ],
        volumes=[
            gcp.cloudrunv2.ServiceTemplateVolumeArgs(
                name="gcs-data",
                gcs=gcp.cloudrunv2.ServiceTemplateVolumeGcsArgs(
                    bucket=BUCKET_NAME,
                    read_only=True,
                ),
            )
        ],
    ),
)

# ---------------------------------------------------------------------------
# text2vec — Cloud Run Service (stateless)
# ---------------------------------------------------------------------------
text2vec_service = gcp.cloudrunv2.Service(
    "text2vec-service",
    name="text2vec",
    location=REGION,
    deletion_protection=False,
    ingress="INGRESS_TRAFFIC_ALL",
    template=gcp.cloudrunv2.ServiceTemplateArgs(
        service_account=text2vec_sa.email,
        scaling=gcp.cloudrunv2.ServiceTemplateScalingArgs(
            min_instance_count=0,
            max_instance_count=2,
        ),
        containers=[
            gcp.cloudrunv2.ServiceTemplateContainerArgs(
                image=text2vec_image.ref,
                ports=gcp.cloudrunv2.ServiceTemplateContainerPortsArgs(
                    container_port=8081,
                ),
                resources=gcp.cloudrunv2.ServiceTemplateContainerResourcesArgs(
                    limits={"memory": "8Gi", "cpu": "4"},
                ),
                startup_probe=gcp.cloudrunv2.ServiceTemplateContainerStartupProbeArgs(
                    http_get=gcp.cloudrunv2.ServiceTemplateContainerStartupProbeHttpGetArgs(
                        path="/health",
                        port=8081,
                    ),
                    failure_threshold=60,
                    period_seconds=10,
                    timeout_seconds=5,
                ),
            )
        ],
    ),
)

# ---------------------------------------------------------------------------
# Frontend — Cloud Run Service (GCS FUSE for thumbnails, HttpClient for ChromaDB)
# ---------------------------------------------------------------------------
frontend_service = gcp.cloudrunv2.Service(
    "frontend-service",
    name="frontend",
    location=REGION,
    deletion_protection=False,
    ingress="INGRESS_TRAFFIC_ALL",
    template=gcp.cloudrunv2.ServiceTemplateArgs(
        service_account=frontend_sa.email,
        scaling=gcp.cloudrunv2.ServiceTemplateScalingArgs(
            min_instance_count=0,
            max_instance_count=2,
        ),
        containers=[
            gcp.cloudrunv2.ServiceTemplateContainerArgs(
                image=frontend_image.ref,
                ports=gcp.cloudrunv2.ServiceTemplateContainerPortsArgs(
                    container_port=8501,
                ),
                resources=gcp.cloudrunv2.ServiceTemplateContainerResourcesArgs(
                    limits={"memory": "1Gi", "cpu": "1"},
                ),
                envs=[
                    gcp.cloudrunv2.ServiceTemplateContainerEnvArgs(
                        name="BASE_PATH",
                        value="/tmp/images",
                    ),
                    gcp.cloudrunv2.ServiceTemplateContainerEnvArgs(
                        name="TEXT2VEC_URL",
                        value=text2vec_service.uri,
                    ),
                    gcp.cloudrunv2.ServiceTemplateContainerEnvArgs(
                        name="CHROMA_URL",
                        value=chromadb_service.uri,
                    ),
                ],
                volume_mounts=[
                    gcp.cloudrunv2.ServiceTemplateContainerVolumeMountArgs(
                        name="gcs-data",
                        mount_path="/tmp/images",
                    )
                ],
            )
        ],
        volumes=[
            gcp.cloudrunv2.ServiceTemplateVolumeArgs(
                name="gcs-data",
                gcs=gcp.cloudrunv2.ServiceTemplateVolumeGcsArgs(
                    bucket=BUCKET_NAME,
                    read_only=True,
                ),
            )
        ],
    ),
)

# ---------------------------------------------------------------------------
# IAM Bindings — least-privilege access control
# ---------------------------------------------------------------------------

# Only frontend can invoke text2vec
gcp.cloudrunv2.ServiceIamMember(
    "text2vec-invoker",
    location=REGION,
    name=text2vec_service.name,
    role="roles/run.invoker",
    member=frontend_sa.email.apply(lambda e: f"serviceAccount:{e}"),
)

# Frontend can invoke chromadb
gcp.cloudrunv2.ServiceIamMember(
    "chromadb-invoker-frontend",
    location=REGION,
    name=chromadb_service.name,
    role="roles/run.invoker",
    member=frontend_sa.email.apply(lambda e: f"serviceAccount:{e}"),
)

# Allow the configured user to access ChromaDB from a laptop
gcp.cloudrunv2.ServiceIamMember(
    "chromadb-invoker-admin",
    location=REGION,
    name=chromadb_service.name,
    role="roles/run.invoker",
    member=f"user:{ADMIN_EMAIL}",
)

# Public frontend access (protected at the DNS/Zero Trust layer by Cloudflare Access)
gcp.cloudrunv2.ServiceIamMember(
    "frontend-public",
    location=REGION,
    name=frontend_service.name,
    role="roles/run.invoker",
    member="allUsers",
)

# ---------------------------------------------------------------------------
# Outputs
# ---------------------------------------------------------------------------
pulumi.export("frontend_url", frontend_service.uri)
pulumi.export("chromadb_url", chromadb_service.uri)
pulumi.export("text2vec_url", text2vec_service.uri)
