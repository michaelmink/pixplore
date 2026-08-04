# Controller – Saga Orchestrator

Überwacht `/tmp/images` auf neue JPG-Dateien und orchestriert deren Verarbeitung über gRPC-Worker. Verarbeitet mehrere Bilder parallel via Semaphore.

## Architektur

```
                          ┌→ Worker_Tags        (gRPC :50051) → ChromaDB
CSV → Controller (async) ─┼→ Worker_Thumbnails  (gRPC :50052)
                          └→ Worker_Embeddings  (gRPC :50053) → ChromaDB
```

- Pro Bild laufen alle 3 Worker parallel (`asyncio.gather`)
- Mehrere Bilder werden gleichzeitig verarbeitet (Semaphore, default: 5)
- Worker_Embeddings nutzt `dns:///` + round-robin für Lastverteilung auf N Replicas

## Ablauf

1. Controller pollt alle 5s den Ordner `/tmp/images` nach `list_files.csv`
2. Alle Bilder aus der CSV werden parallel verarbeitet (begrenzt durch Semaphore)
3. Pro Bild startet ein Saga-Workflow mit 3 parallelen Worker-Aufrufen
4. Bei Fehler: Kompensation (Rollback) an alle bereits erfolgreichen Worker
5. Nach Erfolg: Bild wird gelöscht

## Voraussetzungen

- Worker_Tags läuft auf Port 50051
- Worker_Thumbnails läuft auf Port 50052
- Worker_Embeddings läuft auf Port 50053 (skalierbar via Replicas)
- ChromaDB läuft auf Port 8000

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
| `CONCURRENCY` | `5` | Max. gleichzeitig verarbeitete Bilder (Semaphore) |

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