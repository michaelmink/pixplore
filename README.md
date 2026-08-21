# pixplore

Pixplore - AI Image Explorer

Framework that contains the following basic functionalities:
* sync images from cloud service provider (here: pCloud via WebDAV)
* training pipeline to finetune face recognition to family members
* pipeline to index images
* server to visualize / filter thumbnails
* integrate blip2/qwen3-vl embeddings to enable query based search
* local llm to leverage image search

**Target Platform:** Docker Compose (lokal) → Minikube (lokal K8s) → GKE (Google Cloud)

## Architektur

```
pixplore/
├── src/
│   ├── frontend/          # Streamlit UI (Port 8501)
│   ├── controller/        # Saga Orchestrator – überwacht /tmp/images, dispatcht an Worker
│   ├── text2vec/          # BLIP2 Text-Embedding Service (Port 8081)
│   ├── sync_images/
│   │   ├── pcloud-java/   # Spring Boot API zum Sync mit pCloud (Port 8080)
│   │   └── python/        # Python-basierter pCloud-Sync
│   ├── indexing/
│   │   ├── create_tags/       # gRPC Worker – EXIF-Extraktion (Port 50051)
│   │   ├── create_thumbnails/ # gRPC Worker – Thumbnail-Erzeugung (Port 50052)
│   │   ├── create_embeddings/ # gRPC Worker – BLIP2 Bild-Embeddings → ChromaDB
│   │   └── face_detection/    # Gesichtserkennung
│   └── vectordb/          # ChromaDB Vektor-Datenbank (Port 8000)
├── docker-compose.yaml
└── k8s/                   # Kubernetes Manifeste
```

### Datenfluss

```
pCloud → java-api → /tmp/images/*.jpg → Controller ─┬→ Worker_Tags → ChromaDB (image_tags)
                                                     ├→ Worker_Thumbnails → /tmp/images/thumbnails/
                                                     └→ Worker_Embeddings → ChromaDB (image_embeddings)

Frontend (Streamlit) ← liest Metadaten + Thumbnails + Embeddings aus ChromaDB
    ↓
Text-Suche → text2vec (BLIP2) → Embedding → ChromaDB Cosine Similarity → Ergebnisse
```

## Services

| Service | Beschreibung | Port |
|---------|-------------|------|
| **java-api** | Spring Boot API – Bilder aus pCloud via WebDAV listen/downloaden | 8080 |
| **frontend** | Streamlit UI – Bilder anzeigen, filtern, Text-Suche | 8501 |
| **text2vec** | FastAPI – BLIP2 Text-Embeddings für Similarity Search | 8081 |
| **chromadb** | ChromaDB Vektor-Datenbank | 8000 |
| **worker_tags** | gRPC Worker – extrahiert EXIF-Metadaten → ChromaDB | 50051 |
| **worker_thumbnails** | gRPC Worker – erzeugt Thumbnails | 50052 |
| **worker_embeddings** | gRPC Worker – BLIP2 Bild-Embeddings → ChromaDB | - |
| **controller** | Saga Orchestrator – pollt /tmp/images und dispatcht an Worker | - |
| **otel-collector** | OpenTelemetry Collector – empfängt Traces/Metrics, leitet weiter | 4317/4318 |
| **jaeger** | Distributed Tracing UI | 16686 |
| **prometheus** | Metrics-Scraping und -Abfrage | 9090 |

## Schnellstart

### 1. `.env`-Datei erstellen

```env
PCLOUD_USERNAME=deine@email.com
PCLOUD_PASSWORD=deinPasswort
```

### 2. Starten mit Docker Compose

```bash
docker compose up --build
```

Frontend: http://localhost:8501
API: http://localhost:8080
Swagger UI: http://localhost:8080/swagger-ui.html

### Einzelne Services lokal starten

**Java-API:**
```bash
cd src/sync_images/pcloud-java
./gradlew bootRun
```

**Frontend:**
```bash
cd src/frontend
streamlit run start_server.py
```

## Minikube Deployment

K8s-Manifeste liegen in `k8s/`. Nutzt `hostPath` für lokalen Dateizugriff.

### Voraussetzungen

- Minikube installiert und gestartet (`minikube start`)
- `kubectl` installiert

### 1. Images in Minikube bauen

```bash
eval $(minikube docker-env)
docker build -t java-api ./src/sync_images/pcloud-java
docker build -t frontend ./src/frontend
```

### 2. Secret anlegen

`k8s/secret.yaml` ist in `.gitignore` — manuell erstellen:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: pcloud-credentials
  namespace: pixplore
type: Opaque
stringData:
  PCLOUD_USERNAME: "deine@email.com"
  PCLOUD_PASSWORD: "deinPasswort"
```

### 3. Host-Verzeichnis mounten

```bash
minikube mount /tmp/images:/tmp/images &
```

### 4. Deployen

```bash
kubectl apply -f k8s/
```

### 5. Port-Forwarding (von anderen Rechnern erreichbar)

```bash
kubectl port-forward svc/java-api 8080:8080 -n pixplore --address 0.0.0.0 &
kubectl port-forward svc/frontend 8501:8501 -n pixplore --address 0.0.0.0 &
```

### Nützliche Befehle

```bash
kubectl get pods -n pixplore                      # Pod-Status
kubectl logs -f deployment/java-api -n pixplore   # Logs
kubectl exec -it deployment/java-api -n pixplore -- sh  # Shell im Container
kubectl rollout restart deployment/java-api -n pixplore # Pod neustarten
minikube service java-api -n pixplore --url       # Service-URL anzeigen
kubectl delete -f k8s/                            # Alles aufräumen
```

## Internet Facing

Using [Cloudflare Tunnel](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/) + [Cloudflare Access](https://developers.cloudflare.com/cloudflare-one/policies/access/) for secure public access with authentication.

### Expose via Cloudflare Tunnel

```bash
cloudflared tunnel run pixplore
```

### Authentication

Cloudflare Access with email-based OTP. Only whitelisted emails can access the app.

### Setup Steps

1. Buy domain at Cloudflare Registrar
2. Install `cloudflared` on server
3. Create tunnel: `cloudflared tunnel create pixplore`
4. Configure tunnel to proxy to `http://localhost:8501`
5. Add DNS route: `cloudflared tunnel route dns pixplore <subdomain>`
6. Create Access policy: allow only whitelisted emails

## Tags

Table schema für Tags
-------------------------------
GPS Location: TEXT
City: TEXT
Country: TEXT
Year: INTEGER
Month: INTEGER
Day: INTEGER
Peron_janine: BOOLEAN
Person_micmink: BOOLEAN
Person_other: BOOLEAN
Count_faces: INTEGER
ref_image_path: TEXT
ref_thumbnail_path: TEXT
