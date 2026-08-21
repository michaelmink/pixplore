# Pixplore — Lokales Setup (Pulumi + Docker)

Startet alle Pixplore-Services lokal als Docker-Container. Ersetzt docker-compose durch Pulumi mit dem Docker-Provider.

## Architektur

```
┌──────────────── Docker (lokal) ────────────────────┐
│  Network: pixplore                                 │
│                                                    │
│  ┌────────────┐  ┌──────────┐  ┌──────────────┐   │
│  │ java-api   │  │ chromadb │  │   text2vec   │   │
│  │ :8080      │  │ :8000    │  │   :8090→8081 │   │
│  └────────────┘  └──────────┘  └──────────────┘   │
│                        ▲                           │
│  ┌────────────────────┐│┌─────────────────────┐    │
│  │ worker_tags  :50051│││ worker_embeddings   │    │
│  │ worker_thumb :50052│││ (chromadb)          │    │
│  └────────────────────┘│└─────────────────────┘    │
│                        │                           │
│  ┌─────────────┐      │  ┌──────────────┐         │
│  │ controller  │──────┘  │  frontend    │         │
│  │ (orchestr.) │         │  :8501       │         │
│  └─────────────┘         └──────────────┘         │
└────────────────────────────────────────────────────┘
  Shared Volume: /tmp/images
```

## Voraussetzungen

- Pulumi CLI: `curl -fsSL https://get.pulumi.com | sh`
- PATH: `export PATH="$HOME/.pulumi/bin:$PATH"`
- Docker läuft

## Setup

```bash
cd pulumi/local
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Lokales Backend
pulumi login --local

# Stack anlegen
pulumi stack init dev

# Secrets setzen (verschlüsselt gespeichert)
pulumi config set --secret pcloud-username "dein-user"
pulumi config set --secret pcloud-password "dein-passwort"
```

## Deployen

```bash
# Alles hochfahren (baut Images + startet Container)
pulumi up

# Preview (was würde passieren)
pulumi preview

# Alles runterfahren
pulumi destroy

# Outputs anzeigen
pulumi stack output
```

## Services

| Service | Port | Funktion |
|---------|------|----------|
| java-api | 8080 | pCloud Sync (lädt Bilder herunter) |
| frontend | 8501 | Streamlit UI |
| chromadb | 8000 | Vector-Datenbank |
| text2vec | 8090 | Text-zu-Embedding Modell |
| worker_tags | 50051 | gRPC: Bild-Tagging |
| worker_thumbnails | 50052 | gRPC: Thumbnail-Erzeugung |
| worker_embeddings | — | gRPC: Bild-Embeddings → ChromaDB |
| controller | — | Orchestriert Worker bei neuen Bildern |
| otel-collector | 4317/4318 | OpenTelemetry Collector (OTLP gRPC + HTTP) |
| jaeger | 16686 | Distributed Tracing UI |
| prometheus | 9090 | Metrics (scrapes OTel Collector :8889) |

## Observability

Services senden Traces/Metrics via OTel Auto-Instrumentation an den Collector:

```
Service (OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317)
    → OTel Collector
        ├── Traces → Jaeger (http://localhost:16686)
        └── Metrics → Prometheus scrapes :8889 (http://localhost:9090)
```

Konfiguration: `otel-collector-config.yaml`, `prometheus.yml`

## Dateistruktur

```
pulumi/local/
├── __main__.py           # Importiert alle Services, definiert Outputs
├── Pulumi.yaml           # Projekt-Definition
├── Pulumi.dev.yaml       # Stack-Config (Secrets, verschlüsselt)
├── requirements.txt      # pulumi + pulumi-docker
└── services/
    ├── __init__.py       # Shared Docker Network
    ├── java_api.py       # pCloud API
    ├── frontend.py       # Streamlit
    ├── chromadb.py       # VectorDB
    ├── text2vec.py       # Embedding-Modell
    ├── worker.py         # Tags + Thumbnails + Embeddings
    ├── controller.py     # Orchestrierung
    ├── opentelemetry_collector.py  # OTel Collector
    ├── jaeger.py         # Jaeger Tracing
    └── prometheus.py     # Prometheus Metrics
```

## Nützliche Befehle

```bash
# Container-Logs (Pulumi hat kein Log-Viewing)
docker logs java-api
docker logs -f controller

# Alle Container anzeigen
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Dependency-Graph visualisieren
pulumi stack graph graph.dot
dot -Tpng graph.dot -o graph.png

# State inspizieren
pulumi stack --show-urns
pulumi stack export | python -m json.tool
```

## Einzelne Services starten

Pulumi ist deklarativ — es fährt immer den gesamten definierten Zustand hoch. Für selektives Starten: Imports in `__main__.py` auskommentieren.

```python
from services.java_api import java_api_container
# from services.frontend import frontend_container  # ← wird nicht gestartet
```

## Networking

Alle Container hängen am Docker-Network `pixplore`. Dadurch können sie sich gegenseitig über den Container-Namen erreichen:

- `TEXT2VEC_URL=http://text2vec:8081` → findet den text2vec Container
- `CHROMA_HOST=chromadb` → findet den chromadb Container

## Encryption

Bei `pulumi login --local` wird eine Passphrase benötigt:

```bash
export PULUMI_CONFIG_PASSPHRASE="deine-passphrase"
```

Secrets in `Pulumi.dev.yaml` sind damit verschlüsselt und können committed werden.
