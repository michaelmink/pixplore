# VectorDB

ChromaDB-basierte Vektordatenbank für Image Embeddings (BLIP2, 256-dim, Cosine Similarity).

## Struktur

```
data/vector_db/
├── chroma.sqlite3              # Metadata (IDs, Metadaten)
└── <collection-uuid>/          # HNSW Index (Embedding-Vektoren)
    ├── data_level0.bin
    ├── header.bin
    ├── length.bin
    └── link_lists.bin
```

## Lokale Nutzung

```python
import chromadb

client = chromadb.PersistentClient(path="data/vector_db")
col = client.get_collection("image_embeddings")
print(col.count())
print(col.peek(5))
```

## Deployment

Die VectorDB wird **nicht als separater Service** deployed. Stattdessen wird die DB direkt als GCS Volume in den Frontend-Container gemountet und per `PersistentClient` gelesen.

### Sync nach GCS

```bash
gsutil -m rsync -r data/vector_db/ gs://pixplore-vectordb/
```

### Cloud Run Frontend Deploy mit DB-Mount

```bash
gcloud run deploy frontend \
  --image europe-west1-docker.pkg.dev/pixplore-503406/pixplore/frontend:latest \
  --region europe-west1 \
  --port 8080 \
  --execution-environment gen2 \
  --add-volume name=chromadata,type=cloud-storage,bucket=pixplore-vectordb \
  --add-volume-mount volume=chromadata,mount-path=/data/vector_db \
  --allow-unauthenticated
```

## Dockerfile

Das Dockerfile (`FROM chromadb/chroma:latest`) existiert für lokales Testen im Server-Modus:

```bash
docker run -p 8000:8000 -v /tmp/images/vector_db:/data chromadb/chroma
```

Für Production auf Cloud Run wird kein separater ChromaDB-Container benötigt.
