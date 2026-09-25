import pulumi
import pulumi_kubernetes as k8s

from . import REGISTRY, NAMESPACE, ns, k8s_provider

# Define labels for the Deployment and Service.
labels = {"app": "hello-world"}

# Create the Deployment for the 'hello-world' application.
deployment = k8s.apps.v1.Deployment(
    "hello-world",  # Name of the Deployment.
    metadata=k8s.meta.v1.ObjectMetaArgs(
        name="hello-world", namespace=NAMESPACE
    ),  # Metadata for the Deployment.
    spec=k8s.apps.v1.DeploymentSpecArgs(  # Specification for the Deployment.
        replicas=1,  # Number of replicas for the Deployment.
        selector=k8s.meta.v1.LabelSelectorArgs(
            match_labels=labels
        ),  # Selector for the Deployment.
        template=k8s.core.v1.PodTemplateSpecArgs(  # Pod template for the Deployment.
            metadata=k8s.meta.v1.ObjectMetaArgs(labels=labels),
            spec=k8s.core.v1.PodSpecArgs(  # Pod specification for the Deployment.
                containers=[  # List of containers for the Pod.
                    k8s.core.v1.ContainerArgs(  # Container definition for the 'hello-world' application.
                        name="hello-world",
                        image=f"{REGISTRY}/hello-world:latest",
                        ports=[k8s.core.v1.ContainerPortArgs(container_port=8080)],
                        resources=k8s.core.v1.ResourceRequirementsArgs(  # Resource requirements for the container.
                            requests={"cpu": "50m", "memory": "64Mi"},
                            limits={"cpu": "200m", "memory": "128Mi"},
                        ),
                    )
                ],
            ),
        ),
    ),
    opts=pulumi.ResourceOptions(
        provider=k8s_provider, depends_on=[ns]
    ),  # Ensure the Deployment is created after the namespace.
)

# Create the Service for the 'hello-world' application.
svc = k8s.core.v1.Service(
    "hello-world",  # Name of the Service.
    metadata=k8s.meta.v1.ObjectMetaArgs(
        name="hello-world", namespace=NAMESPACE
    ),  # Metadata for the Service.
    spec=k8s.core.v1.ServiceSpecArgs(  # Specification for the Service.
        selector=labels,  # Selector for the Service.
        ports=[
            k8s.core.v1.ServicePortArgs(port=8080, target_port=8080)
        ],  # Ports for the Service.
    ),
    opts=pulumi.ResourceOptions(
        provider=k8s_provider, depends_on=[ns]
    ),  # Ensure the Service is created after the namespace.
)
