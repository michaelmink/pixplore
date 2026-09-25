"""Pixplore GKE Infrastruktur — Autopilot Cluster (Scale-to-Zero).

Erstellt den GKE Autopilot Cluster inkl. GCS FUSE CSI Driver und exportiert
Cluster-Infos + Kubeconfig als Stack-Outputs. Die Workload-Stacks (cloud_k8s,
cloud_k8s_playground) konsumieren diese Outputs per StackReference.
"""

import pulumi
import pulumi_gcp as gcp

config = pulumi.Config()
gcp_config = pulumi.Config("gcp")

PROJECT = gcp_config.require("project")
REGION = gcp_config.require("region")
CLUSTER_NAME = config.get("cluster-name") or "pixplore-cluster"

# ---------------------------------------------------------------------------
# GKE Autopilot Cluster
# ---------------------------------------------------------------------------
# Autopilot verwaltet Nodes automatisch und skaliert ohne laufende Workloads
# auf null Compute-Kosten herunter. Workload Identity ist im Autopilot-Modus
# standardmäßig aktiv (von cloud_k8s benötigt).
cluster = gcp.container.Cluster(
    "pixplore-cluster",
    name=CLUSTER_NAME,
    location=REGION,
    enable_autopilot=True,
    # erlaubt `pulumi destroy`, den Cluster wieder zu entfernen
    deletion_protection=False,
    addons_config=gcp.container.ClusterAddonsConfigArgs(
        gcs_fuse_csi_driver_config=gcp.container.ClusterAddonsConfigGcsFuseCsiDriverConfigArgs(
            enabled=True,
        ),
    ),
)

# ---------------------------------------------------------------------------
# Kubeconfig für Downstream-Stacks
# ---------------------------------------------------------------------------
_KUBECONFIG_TEMPLATE = """apiVersion: v1
kind: Config
clusters:
- cluster:
    certificate-authority-data: {ca_cert}
    server: https://{endpoint}
  name: {name}
contexts:
- context:
    cluster: {name}
    user: {name}
  name: {name}
current-context: {name}
users:
- name: {name}
  user:
    exec:
      apiVersion: client.authentication.k8s.io/v1beta1
      command: gke-gcloud-auth-plugin
      provideClusterInfo: true
"""

kubeconfig = pulumi.Output.all(
    cluster.name,
    cluster.endpoint,
    cluster.master_auth.cluster_ca_certificate,
).apply(
    lambda args: _KUBECONFIG_TEMPLATE.format(
        name=args[0], endpoint=args[1], ca_cert=args[2]
    )
)

# ---------------------------------------------------------------------------
# Outputs
# ---------------------------------------------------------------------------
pulumi.export("cluster_name", cluster.name)
pulumi.export("cluster_endpoint", cluster.endpoint)
pulumi.export("cluster_location", cluster.location)
pulumi.export("kubeconfig", pulumi.Output.secret(kubeconfig))
