# Pixplore — GKE Autopilot Cluster (Pulumi Infra)

Erstellt den GKE **Autopilot**-Cluster als eigene Infrastruktur-Ebene, getrennt
von den Workloads. Autopilot verwaltet die Nodes automatisch und skaliert ohne
laufende Workloads auf **null Compute-Kosten** (Scale-to-Zero). Die Cluster-Fee
ist im Free-Tier (ein Autopilot-/Zonal-Cluster pro Billing-Account) enthalten.

## Warum ein separater Stack?

- **Cluster** ändert sich selten, ist teuer/langsam beim Auf- und Abbau.
- **Workloads** (`cloud_k8s`, `cloud_k8s_playground`) ändern sich oft.

Getrennte Stacks erlauben `pulumi destroy` der Workloads, ohne den Cluster neu
aufbauen zu müssen — und umgekehrt.

## Outputs

| Output | Beschreibung |
| --- | --- |
| `cluster_name` | Name des Clusters |
| `cluster_endpoint` | API-Server-Endpoint |
| `cluster_location` | Region des Clusters |
| `kubeconfig` | Fertige Kubeconfig (secret) für Downstream-Stacks / kubectl |

## Voraussetzungen

- Pulumi CLI (`curl -fsSL https://get.pulumi.com | sh`)
- `gcloud` CLI authentifiziert
- `gke-gcloud-auth-plugin` installiert (für kubectl/Provider-Zugriff):
  ```bash
  gcloud components install gke-gcloud-auth-plugin
  ```

## Setup

```bash
cd pulumi/cloud_k8s_infra
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Lokales Backend (kein Pulumi Cloud Account nötig)
pulumi login --local

# Stack anlegen
pulumi stack init prod

# Config setzen
pulumi config set gcp:project pixplore-503406
pulumi config set gcp:region europe-west3
pulumi config set cluster-name pixplore-cluster   # optional, default: pixplore-cluster

# Cluster erstellen
pulumi up
```

## Kubeconfig für kubectl exportieren

```bash
pulumi stack output kubeconfig --show-secrets > ~/.kube/pixplore.yaml
export KUBECONFIG=~/.kube/pixplore.yaml
kubectl get nodes
```

Oder klassisch via gcloud:

```bash
gcloud container clusters get-credentials pixplore-cluster --region europe-west3
```

## Cluster wieder entfernen

```bash
pulumi destroy
```

`deletion_protection` ist auf `False` gesetzt, damit der Cluster per Pulumi
gelöscht werden kann.
