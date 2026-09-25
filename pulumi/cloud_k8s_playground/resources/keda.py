"""KEDA HTTP Add-on: request-getriebenes Scale-to-Zero für hello-world.

- KEDA core + HTTP Add-on via Helm im Namespace 'keda'
- hello-world Deployment/Service im Namespace 'playground-keda'
- HTTPScaledObject skaliert das Deployment über den KEDA-Interceptor von/bis 0
"""

import pulumi
import pulumi_kubernetes as k8s

from . import REGISTRY, k8s_provider

KEDA_NS = "keda"
APP_NS = "playground-keda"
HOST = "hello-world.keda.local"

# ---------------------------------------------------------------------------
# KEDA Installation (Helm)
# ---------------------------------------------------------------------------
keda_ns = k8s.core.v1.Namespace(
    "keda-ns",
    metadata=k8s.meta.v1.ObjectMetaArgs(name=KEDA_NS),
    opts=pulumi.ResourceOptions(provider=k8s_provider),
)

keda = k8s.helm.v3.Release(
    "keda",
    k8s.helm.v3.ReleaseArgs(
        chart="keda",
        namespace=KEDA_NS,
        create_namespace=False,
        repository_opts=k8s.helm.v3.RepositoryOptsArgs(
            repo="https://kedacore.github.io/charts",
        ),
    ),
    opts=pulumi.ResourceOptions(provider=k8s_provider, depends_on=[keda_ns]),
)

# HTTP Add-on braucht die KEDA-core CRDs
keda_http = k8s.helm.v3.Release(
    "keda-http-addon",
    k8s.helm.v3.ReleaseArgs(
        chart="keda-add-ons-http",
        namespace=KEDA_NS,
        create_namespace=False,
        repository_opts=k8s.helm.v3.RepositoryOptsArgs(
            repo="https://kedacore.github.io/charts",
        ),
    ),
    opts=pulumi.ResourceOptions(provider=k8s_provider, depends_on=[keda, keda_ns]),
)

# ---------------------------------------------------------------------------
# hello-world Deployment + Service im Namespace 'playground-keda'
# ---------------------------------------------------------------------------
app_ns = k8s.core.v1.Namespace(
    "playground-keda-ns",
    metadata=k8s.meta.v1.ObjectMetaArgs(name=APP_NS),
    opts=pulumi.ResourceOptions(provider=k8s_provider),
)

labels = {"app": "hello-world"}

deployment = k8s.apps.v1.Deployment(
    "hello-world-keda",
    metadata=k8s.meta.v1.ObjectMetaArgs(name="hello-world", namespace=APP_NS),
    spec=k8s.apps.v1.DeploymentSpecArgs(
        replicas=1,
        selector=k8s.meta.v1.LabelSelectorArgs(match_labels=labels),
        template=k8s.core.v1.PodTemplateSpecArgs(
            metadata=k8s.meta.v1.ObjectMetaArgs(labels=labels),
            spec=k8s.core.v1.PodSpecArgs(
                containers=[
                    k8s.core.v1.ContainerArgs(
                        name="hello-world",
                        image=f"{REGISTRY}/hello-world:latest",
                        ports=[k8s.core.v1.ContainerPortArgs(container_port=8080)],
                        resources=k8s.core.v1.ResourceRequirementsArgs(
                            requests={"cpu": "50m", "memory": "64Mi"},
                            limits={"cpu": "200m", "memory": "128Mi"},
                        ),
                    )
                ],
            ),
        ),
    ),
    # KEDA verwaltet die Replica-Zahl (Scale-to-Zero) über eine HPA.
    opts=pulumi.ResourceOptions(
        provider=k8s_provider,
        depends_on=[app_ns],
        ignore_changes=["spec.replicas"],
    ),
)

svc = k8s.core.v1.Service(
    "hello-world-keda-svc",
    metadata=k8s.meta.v1.ObjectMetaArgs(name="hello-world", namespace=APP_NS),
    spec=k8s.core.v1.ServiceSpecArgs(
        selector=labels,
        ports=[k8s.core.v1.ServicePortArgs(port=80, target_port=8080)],
    ),
    opts=pulumi.ResourceOptions(provider=k8s_provider, depends_on=[app_ns]),
)

# ---------------------------------------------------------------------------
# HTTPScaledObject — Scale-to-Zero über den KEDA HTTP Interceptor
# ---------------------------------------------------------------------------
http_scaled_object = k8s.apiextensions.CustomResource(
    "hello-world-http-scaledobject",
    api_version="http.keda.sh/v1alpha1",
    kind="HTTPScaledObject",
    metadata=k8s.meta.v1.ObjectMetaArgs(name="hello-world", namespace=APP_NS),
    spec={
        "hosts": [HOST],
        "scaleTargetRef": {
            "name": "hello-world",
            "kind": "Deployment",
            "apiVersion": "apps/v1",
            "service": "hello-world",
            "port": 80,
        },
        "replicas": {"min": 0, "max": 1},
    },
    opts=pulumi.ResourceOptions(
        provider=k8s_provider,
        depends_on=[keda_http, deployment, svc],
    ),
)

# ---------------------------------------------------------------------------
# Outputs
# ---------------------------------------------------------------------------
pulumi.export("keda_host", HOST)
pulumi.export(
    "keda_test_hint",
    "kubectl port-forward -n keda svc/keda-add-ons-http-interceptor-proxy 8080:8080 "
    f'&& curl -H "Host: {HOST}" http://localhost:8080',
)
