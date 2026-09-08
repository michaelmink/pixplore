# create_embeddings – gRPC Worker für BLIP2-Embeddings

gRPC-basierter Worker, der BLIP2-Embeddings aus Bildern generiert und an den Controller zurückgibt. Unterstützt horizontale Skalierung via `dns:///` + round-robin.

## Voraussetzungen

- Python 3.10+
- GPU empfohlen (läuft auch auf CPU, aber deutlich langsamer)

## Setup

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Protobuf-Dateien generieren

```bash
python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. service.proto
```

## Worker starten

```bash
python worker_embeddings.py
```

Der Server läuft auf Port 50053 und liefert das Embedding über gRPC.

## Skalierung

Im Docker Compose mit mehreren Replicas betreiben:

```yaml
embedding-worker:
  build: ./src/indexing/create_embeddings
  deploy:
    replicas: 5
```

Der Controller nutzt `dns:///embedding-worker:50053` mit gRPC client-side round-robin Load Balancing.

## Architektur

```
Controller (gRPC, round-robin) → N × EmbeddingWorker (Port 50053) → Controller-Parquet-Batch
```

Der Worker:
1. Empfängt einen Image-Pfad per gRPC (`ProcessTask`)
2. Generiert ein 256-dimensionales BLIP2-Embedding (ViT-G + Q-Former)
3. Gibt das Embedding an den Controller zurück
4. Der Controller schreibt das vollständige Bildresultat in einen Parquet-Batch
