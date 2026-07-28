# create_tags – gRPC Worker für EXIF-Tag-Extraktion

gRPC-basierter Worker, der EXIF-Metadaten aus Bildern extrahiert und in ChromaDB speichert.

## Voraussetzungen

- Python 3.10+
- Laufender ChromaDB-Server (Docker)

## Setup

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Protobuf-Dateien generieren

Nach jeder Änderung an `service.proto` müssen die Python-Stubs neu generiert werden:

```bash
python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. service.proto
```

Das erzeugt:
- `service_pb2.py` – Message-Klassen (TaskRequest, TaskResponse, etc.)
- `service_pb2_grpc.py` – gRPC-Stubs und Servicer-Basisklassen

## ChromaDB starten

```bash
docker run -d -p 8000:8000 chromadb/chroma
```

## Worker starten

```bash
source venv/bin/activate
python worker_tags.py
```

Der Server läuft auf Port 50051 und verbindet sich mit ChromaDB auf localhost:8000.

## ChromaDB-Einträge prüfen

```bash
curl -s http://localhost:8000/api/v2/tenants/default_tenant/databases/default_database/collections/image_tags/get \
  -X POST -H "Content-Type: application/json" \
  -d '{"include": ["metadatas", "documents"]}' | python -m json.tool
```

## Architektur

```
Client (gRPC) → TagWorker (Port 50051) → ChromaDB (Port 8000)
```

Der Worker:
1. Empfängt einen Image-Pfad per gRPC (`ProcessTask`)
2. Liest EXIF-Daten (Datum, Kameramodell, GPS)
3. Schreibt Metadaten in die ChromaDB-Collection `image_tags`
4. Gibt die extrahierten Tags in der gRPC-Response zurück
