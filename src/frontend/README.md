# Pixplore Frontend

Streamlit-basiertes Frontend zur Bildanzeige und -verwaltung.

## Lokale Entwicklung

```bash
cd src/frontend
source venv/bin/activate
streamlit run start_server.py
```

## Docker

### Image bauen

```bash
docker build -t frontend .
```

### Container starten

```bash
docker run -d -p 8501:8501 -v /tmp/images:/tmp/images frontend
```

| Flag | Beschreibung |
|------|-------------|
| `-d` | Container im Hintergrund starten |
| `-p 8501:8501` | Port 8501 vom Container auf den Host mappen |
| `-v /tmp/images:/tmp/images` | Bilderverzeichnis vom Host in den Container einbinden |

Die App ist dann erreichbar unter http://localhost:8501.

## Artifact Registry (GCP)

### Image taggen und pushen

```bash
docker build -t europe-west3-docker.pkg.dev/pixplore-503406/pixplore-registry/frontend:latest .
docker push europe-west3-docker.pkg.dev/pixplore-503406/pixplore-registry/frontend:latest
```

### Auth (einmalig)

```bash
gcloud auth configure-docker europe-west3-docker.pkg.dev
```
