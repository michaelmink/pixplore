# Pixplore — GKE Deployment (Pulumi)

Deployt frontend + text2vec auf einen GKE Kubernetes Cluster. Thumbnails und VectorDB liegen auf einem GCS Bucket und werden via GCS FUSE in die Pods gemountet.

## Architektur

```
┌─────────────────── GKE Cluster ───────────────────┐
│  Namespace: pixplore                              │
│                                                   │
│  ┌─────────────┐       ┌──────────────┐          │
│  │  frontend   │──────▶│   text2vec   │          │
│  │  :8501      │       │   :8081      │          │
│  │  (GCS FUSE) │       └──────────────┘          │
│  └──────┬──────┘              ClusterIP           │
│         │ LoadBalancer                            │
└─────────┼─────────────────────────────────────────┘
          │
    Internet ← User

    ┌─────────────┐
    │  GCS Bucket │  ← Thumbnails + VectorDB
    └─────────────┘
```

## Voraussetzungen

- Pulumi CLI installiert (`curl -fsSL https://get.pulumi.com | sh`)
- PATH: `export PATH="$HOME/.pulumi/bin:$PATH"` (in `.bashrc` eintragen)
- `gcloud` CLI authentifiziert
- GKE Cluster existiert mit GCS FUSE CSI Driver aktiviert:
  ```bash
  gcloud container clusters update CLUSTER_NAME --region europe-west3 \
    --update-addons GcsFuseCsiDriver=ENABLED
  ```
- Kubeconfig zeigt auf den Cluster:
  ```bash
  gcloud container clusters get-credentials CLUSTER_NAME --region europe-west3
  ```

## Setup

```bash
cd pulumi/cloud_k8s
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Lokales Backend (kein Pulumi Cloud Account nötig)
pulumi login --local

# Stack anlegen
pulumi stack init prod

# Config setzen
pulumi config set gcp:project pixplore-503406
pulumi config set gcp:region europe-west3
pulumi config set bucket-name "DEIN-BUCKET-NAME"
pulumi config set cluster-name "DEIN-CLUSTER-NAME"
```

## Deployen

```bash
# Preview (Dry-Run, zeigt was passieren würde)
pulumi preview

# Deployen
pulumi up

# Nur Outputs anzeigen
pulumi stack output
```

## Ressourcen die erstellt werden

| Ressource | Typ | Zweck |
|-----------|-----|-------|
| Artifact Registry | GCP | Docker Images speichern |
| Service Account (GSA) | GCP | Bucket-Zugriff für Pods |
| Workload Identity Binding | GCP | KSA → GSA Verknüpfung |
| Namespace `pixplore` | K8s | Isolation |
| ServiceAccount `pixplore` | K8s | Pod-Identity mit GSA-Annotation |
| Deployment `text2vec` | K8s | Embedding-Modell (8Gi RAM) |
| Service `text2vec` | K8s | ClusterIP, intern erreichbar |
| Deployment `frontend` | K8s | Streamlit UI mit GCS FUSE Mount |
| Service `frontend` | K8s | LoadBalancer, öffentliche IP |

## Nützliche Befehle

```bash
# Status anschauen
pulumi stack
pulumi stack --show-urns

# Dependency-Graph visualisieren
pulumi stack graph graph.dot
dot -Tpng graph.dot -o graph.png

# State mit Realität abgleichen (ohne Änderung)
pulumi refresh

# Alles löschen
pulumi destroy

# Logs der Pods (über kubectl, nicht Pulumi)
kubectl logs -n pixplore -l app=frontend
kubectl logs -n pixplore -l app=text2vec
```

## Konzepte

| Konzept | Erklärung |
|---------|-----------|
| Stack | Eine Umgebung (z.B. `prod`, `staging`) |
| `pulumi.Config()` | Liest Werte aus `Pulumi.prod.yaml` |
| `pulumi.export()` | Gibt Werte nach `pulumi up` aus |
| `depends_on` | Explizite Reihenfolge (sonst parallel) |
| Workload Identity | Pod bekommt GCP-Rechte ohne Key-File |
| GCS FUSE | Mountet GCS Bucket als Dateisystem in den Pod |
| URN | Eindeutige ID einer Ressource im State |

## Encryption / Secrets

Secrets werden mit `--secret` Flag gesetzt und verschlüsselt in der Stack-Config gespeichert:

```bash
pulumi config set --secret mein-geheimnis "wert"
```

Bei `pulumi login --local` wirst du nach einer Passphrase gefragt. Diese wird benötigt um den State zu entschlüsseln:

```bash
export PULUMI_CONFIG_PASSPHRASE="deine-passphrase"
```
