import pulumi
import pulumi_kubernetes as k8s

REGISTRY = "europe-west3-docker.pkg.dev/pixplore-503406/pixplore-registry"
NAMESPACE = "playground"

# Kubernetes Provider aus dem Infra-Stack (StackReference).
config = pulumi.Config()
INFRA_STACK = config.get("infra-stack") or "organization/pixplore-k8s-infra/prod"
infra = pulumi.StackReference(INFRA_STACK)
k8s_provider = k8s.Provider(
    "pixplore-k8s",
    kubeconfig=infra.get_output("kubeconfig"),
)

# Create the 'playground' namespace.
ns = k8s.core.v1.Namespace(
    "playground",
    metadata=k8s.meta.v1.ObjectMetaArgs(name=NAMESPACE),
    opts=pulumi.ResourceOptions(provider=k8s_provider),
)
