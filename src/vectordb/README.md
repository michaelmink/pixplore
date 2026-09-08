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

Parquet-Batches in `catalog/` sind die persistente Quelle. ChromaDB läuft als eigener Service und baut beim Start einen lokalen Index unter `/tmp/chroma` daraus auf.

```bash
gsutil -m rsync -r /tmp/images/catalog gs://pixplore-bucket/catalog
```

Worker schreiben nicht direkt nach ChromaDB. Der Controller erzeugt Parquet, ChromaDB importiert es beim Start.

## Dockerfile

Das Dockerfile (`FROM chromadb/chroma:latest`) existiert für lokales Testen im Server-Modus:

```bash
docker run -p 8000:8000 -v /tmp/images/vector_db:/data chromadb/chroma
```

Für Production auf Cloud Run wird kein separater ChromaDB-Container benötigt.
