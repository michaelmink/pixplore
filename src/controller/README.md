# Controller – Saga Orchestrator

Überwacht `/tmp/images` auf neue JPG-Dateien und orchestriert deren Verarbeitung über gRPC-Worker.

## Architektur

```
/tmp/images/*.jpg  →  Controller (Polling)  →  Worker_Tags (gRPC :50051)  →  ChromaDB (:8000)
```

## Ablauf

1. Controller pollt alle 5s den Ordner `/tmp/images` nach `*.jpg`
2. Pro Bild wird der Saga-Workflow gestartet (`run_saga_orchestrator`)
3. Worker_Tags extrahiert EXIF-Daten und schreibt sie in ChromaDB
4. Bei Fehler: Kompensation (Rollback) an alle bereits erfolgreichen Worker
5. Nach Erfolg: Bild wird gelöscht

## Voraussetzungen

- Worker_Tags läuft auf Port 50051
- ChromaDB läuft auf Port 8000
- JPG-Dateien liegen in `/tmp/images`

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

## Starten

```bash
python controller.py
```

## Umgebungsvariablen

| Variable | Default | Beschreibung |
|---|---|---|
| `WATCH_DIR` | `/tmp/images` | Ordner der auf JPGs überwacht wird |
| `POLL_INTERVAL` | `5` | Polling-Intervall in Sekunden |

## Docker Compose

Der Controller wird zusammen mit den anderen Services gestartet:

```bash
docker compose up --build controller
```

## ChromaDB-Einträge prüfen

```bash
curl -s http://localhost:8000/api/v2/tenants/default_tenant/databases/default_database/collections/image_tags/get \
  -X POST -H "Content-Type: application/json" \
  -d '{"include": ["metadatas", "documents"]}' | python -m json.tool
```