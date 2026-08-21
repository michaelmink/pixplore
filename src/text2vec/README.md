# text2vec

Microservice zur Erzeugung von Text-Embeddings mittels BLIP2 (`Salesforce/blip2-itm-vit-g`). Projiziert Text in einen gemeinsamen 256-dimensionalen Embedding-Raum, der auch für Bild-Embeddings verwendet wird – ermöglicht Cosine-Similarity-Suche zwischen Text-Queries und Bildern.

## Architektur

- **Modell:** Blip2ForImageTextRetrieval (Salesforce/blip2-itm-vit-g)
- **Server:** FastAPI/uvicorn auf Port 8081
- **Ausgabe:** 256-dim normalisierter Float-Vektor

## Starten

```bash
pip install -r requirements.txt
python main.py
```

## Docker (lokal)

```bash
docker build -t text2vec .
docker run -p 8081:8081 text2vec
```

## Docker (GCP Artifact Registry)

```bash
docker build -t europe-west3-docker.pkg.dev/pixplore-503406/pixplore-registry/text2vec:latest .
docker push europe-west3-docker.pkg.dev/pixplore-503406/pixplore-registry/text2vec:latest
```

## API

`POST /embed_text`

Request:
```json
{"text": "A sunset over mountains"}
```

Response:
```json
{"embedding": [0.012, -0.034, ...]}
```

## Client-Beispiel

```python
import requests

resp = requests.post("http://localhost:8081/embed_text", json={"text": "A sunset over mountains"})
embedding = resp.json()["embedding"]  # list of 256 floats
```

## Observability

OpenTelemetry Auto-Instrumentation ist aktiv. Der Service sendet Traces und Metrics an den OTel Collector (konfiguriert via `OTEL_EXPORTER_OTLP_ENDPOINT`).
