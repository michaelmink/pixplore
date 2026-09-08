# create_tags – gRPC Worker für EXIF-Tag-Extraktion

gRPC-basierter Worker, der EXIF-Metadaten aus Bildern extrahiert und an den Controller zurückgibt.

## Voraussetzungen

- Python 3.10+

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

## Worker starten

```bash
source venv/bin/activate
python worker_tags.py
```

Der Server läuft auf Port 50051. Der Worker schreibt keine persistente Datenbank.

## ChromaDB-Einträge prüfen

```bash
curl -s http://localhost:8000/api/v2/tenants/default_tenant/databases/default_database/collections/image_tags/get \
  -X POST -H "Content-Type: application/json" \
  -d '{"include": ["metadatas", "documents"]}' | python -m json.tool
```

## Architektur

```
Client (gRPC) → TagWorker (Port 50051) → Controller → Parquet catalog
```

Der Worker:
1. Empfängt einen Image-Pfad per gRPC (`ProcessTask`)
2. Liest EXIF-Daten (Datum, Kameramodell, GPS)
3. Gibt die extrahierten Metadaten in der gRPC-Response zurück
4. Der Controller schreibt sie in den Parquet-Batch
