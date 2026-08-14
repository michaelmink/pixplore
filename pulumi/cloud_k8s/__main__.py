"""Pixplore GKE Deployment — frontend + text2vec."""

import pulumi
import pulumi_gcp as gcp
import pulumi_kubernetes as k8s
import pulumi_docker_build as docker_build

config = pulumi.Config()
gcp_config = pulumi.Config("gcp")

PROJECT = gcp_config.require("project")
REGION = gcp_config.require("region")
BUCKET_NAME = config.require("bucket-name")
CLUSTER_NAME = config.require("cluster-name")

REGISTRY = f"{REGION}-docker.pkg.dev/{PROJECT}/pixplore-registry"

# ---------------------------------------------------------------------------
# Artifact Registry
# ---------------------------------------------------------------------------
registry = gcp.artifactregistry.Repository(
    "pixplore-registry",
    location=REGION,
    repository_id="pixplore-registry",
    format="DOCKER",
)

# ---------------------------------------------------------------------------
# Docker Images — build & push to Artifact Registry
# ---------------------------------------------------------------------------
gcp_auth = gcp.organizations.get_client_config()

docker_registry = docker_build.RegistryArgs(
    address=f"{REGION}-docker.pkg.dev",
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

# ---------------------------------------------------------------------------
# Kubernetes Namespace
# ---------------------------------------------------------------------------
ns = k8s.core.v1.Namespace(
    "pixplore",
    metadata=k8s.meta.v1.ObjectMetaArgs(name="pixplore"),
)

# ---------------------------------------------------------------------------
# Service Account for GCS access (Workload Identity)
# ---------------------------------------------------------------------------
gsa = gcp.serviceaccount.Account(
    "pixplore-gsa",
    account_id="pixplore-k8s",
    display_name="Pixplore K8s Workload Identity",
)

gcp.storage.BucketIAMMember(
    "gsa-bucket-reader",
    bucket=BUCKET_NAME,
    role="roles/storage.objectViewer",
    member=gsa.email.apply(lambda e: f"serviceAccount:{e}"),
)

# KSA (Kubernetes Service Account) mit Workload Identity Annotation
ksa = k8s.core.v1.ServiceAccount(
    "pixplore-ksa",
    metadata=k8s.meta.v1.ObjectMetaArgs(
        name="pixplore",
        namespace="pixplore",
        annotations={
            "iam.gke.io/gcp-service-account": gsa.email,
        },
    ),
    opts=pulumi.ResourceOptions(depends_on=[ns]),
)

# Workload Identity Binding: KSA darf als GSA agieren
gcp.serviceaccount.IAMMember(
    "workload-identity-binding",
    service_account_id=gsa.name,
    role="roles/iam.workloadIdentityUser",
    member=pulumi.Output.concat(
        "serviceAccount:", PROJECT, ".svc.id.goog[pixplore/pixplore]"
    ),
)

# ---------------------------------------------------------------------------
# text2vec Deployment + Service
# ---------------------------------------------------------------------------
text2vec_labels = {"app": "text2vec"}

text2vec_deployment = k8s.apps.v1.Deployment(
    "text2vec",
    metadata=k8s.meta.v1.ObjectMetaArgs(name="text2vec", namespace="pixplore"),
    spec=k8s.apps.v1.DeploymentSpecArgs(
        replicas=1,
        selector=k8s.meta.v1.LabelSelectorArgs(match_labels=text2vec_labels),
        template=k8s.core.v1.PodTemplateSpecArgs(
            metadata=k8s.meta.v1.ObjectMetaArgs(labels=text2vec_labels),
            spec=k8s.core.v1.PodSpecArgs(
                service_account_name="pixplore",
                containers=[
                    k8s.core.v1.ContainerArgs(
                        name="text2vec",
                        image=text2vec_image.ref,
                        ports=[k8s.core.v1.ContainerPortArgs(container_port=8081)],
                        resources=k8s.core.v1.ResourceRequirementsArgs(
                            requests={"memory": "4Gi", "cpu": "1"},
                            limits={"memory": "8Gi", "cpu": "2"},
                        ),
                    )
                ],
            ),
        ),
    ),
    opts=pulumi.ResourceOptions(depends_on=[ns, ksa]),
)

text2vec_svc = k8s.core.v1.Service(
    "text2vec-svc",
    metadata=k8s.meta.v1.ObjectMetaArgs(name="text2vec", namespace="pixplore"),
    spec=k8s.core.v1.ServiceSpecArgs(
        selector=text2vec_labels,
        ports=[k8s.core.v1.ServicePortArgs(port=8081, target_port=8081)],
    ),
    opts=pulumi.ResourceOptions(depends_on=[ns]),
)

# ---------------------------------------------------------------------------
# frontend Deployment + Service (mit GCS FUSE für Thumbnails/VectorDB)
# ---------------------------------------------------------------------------
frontend_labels = {"app": "frontend"}

frontend_deployment = k8s.apps.v1.Deployment(
    "frontend",
    metadata=k8s.meta.v1.ObjectMetaArgs(name="frontend", namespace="pixplore"),
    spec=k8s.apps.v1.DeploymentSpecArgs(
        replicas=1,
        selector=k8s.meta.v1.LabelSelectorArgs(match_labels=frontend_labels),
        template=k8s.core.v1.PodTemplateSpecArgs(
            metadata=k8s.meta.v1.ObjectMetaArgs(
                labels=frontend_labels,
                annotations={"gke-gcsfuse/volumes": "true"},
            ),
            spec=k8s.core.v1.PodSpecArgs(
                service_account_name="pixplore",
                containers=[
                    k8s.core.v1.ContainerArgs(
                        name="frontend",
                        image=frontend_image.ref,
                        ports=[k8s.core.v1.ContainerPortArgs(container_port=8501)],
                        env=[
                            k8s.core.v1.EnvVarArgs(
                                name="BASE_PATH", value="/tmp/images"
                            ),
                            k8s.core.v1.EnvVarArgs(
                                name="TEXT2VEC_URL",
                                value="http://text2vec:8081",
                            ),
                        ],
                        volume_mounts=[
                            k8s.core.v1.VolumeMountArgs(
                                name="gcs-data",
                                mount_path="/tmp/images",
                                read_only=True,
                            )
                        ],
                        resources=k8s.core.v1.ResourceRequirementsArgs(
                            requests={"memory": "512Mi", "cpu": "500m"},
                            limits={"memory": "1Gi", "cpu": "1"},
                        ),
                    )
                ],
                volumes=[
                    k8s.core.v1.VolumeArgs(
                        name="gcs-data",
                        csi=k8s.core.v1.CSIVolumeSourceArgs(
                            driver="gcsfuse.csi.storage.gke.io",
                            read_only=True,
                            volume_attributes={"bucketName": BUCKET_NAME},
                        ),
                    )
                ],
            ),
        ),
    ),
    opts=pulumi.ResourceOptions(depends_on=[ns, ksa]),
)

frontend_svc = k8s.core.v1.Service(
    "frontend-svc",
    metadata=k8s.meta.v1.ObjectMetaArgs(name="frontend", namespace="pixplore"),
    spec=k8s.core.v1.ServiceSpecArgs(
        type="LoadBalancer",
        selector=frontend_labels,
        ports=[k8s.core.v1.ServicePortArgs(port=8501, target_port=8501)],
    ),
    opts=pulumi.ResourceOptions(depends_on=[ns]),
)

# ---------------------------------------------------------------------------
# Outputs
# ---------------------------------------------------------------------------
pulumi.export(
    "frontend_ip",
    frontend_svc.status.apply(
        lambda s: (
            s.load_balancer.ingress[0].ip if s.load_balancer.ingress else "pending"
        )
    ),
)
pulumi.export("text2vec_cluster_url", "http://text2vec.pixplore.svc.cluster.local:8081")
