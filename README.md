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
│   ├── sync_images/
│   │   ├── pcloud-java/   # Spring Boot API zum Sync mit pCloud (Port 8080)
│   │   └── python/        # Python-basierter pCloud-Sync
│   ├── indexing/           # Embedding, Face Detection, Vektorsuche
│   └── vectordb/           # ChromaDB Vektor-Datenbank
├── docker-compose.yaml
└── config.yaml
```

## Services

| Service | Beschreibung | Port |
|---------|-------------|------|
| **java-api** | Spring Boot API – Bilder aus pCloud via WebDAV listen/downloaden | 8080 |
| **frontend** | Streamlit UI – Bilder anzeigen, filtern, durchsuchen | 8501 |

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