"""Pixplore Playground — hello-world Deployment im Namespace 'playground'."""

import pulumi

from resources.hello_world import svc
import resources.keda  # noqa: F401  — KEDA HTTP Add-on Scale-to-Zero Setup


pulumi.export("service", svc.metadata.name)
