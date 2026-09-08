# Controller – Image Pipeline

Überwacht `/tmp/images` auf neue JPG-Dateien und orchestriert deren Verarbeitung über gRPC-Worker. Verarbeitet mehrere Bilder parallel via Semaphore.

## Architektur

```
                          ┌→ Worker_Tags        (gRPC :50051) → result
CSV → Controller (async) ─┼→ Worker_Thumbnails  (gRPC :50052)
                          └→ Worker_Embeddings  (gRPC :50053) → result
```

- Pro Bild laufen alle 3 Worker parallel (`asyncio.gather`)
- Mehrere Bilder werden gleichzeitig verarbeitet (Semaphore, default: 5)
- Worker_Embeddings nutzt `dns:///` + round-robin für Lastverteilung auf N Replicas

## Ablauf

1. Controller pollt alle 5s den Ordner `/tmp/images` nach `list_files.csv`
2. Alle Bilder aus der CSV werden parallel verarbeitet (begrenzt durch Semaphore)
3. Pro Bild startet eine Saga mit 3 parallelen Worker-Aufrufen
4. Worker-Ergebnisse werden gesammelt und als Parquet-Zeile committed
5. Bei Fehler bleibt das Bild auf der Retry-Liste
6. Nach Commit wird das Bild gelöscht

## Voraussetzungen

- Worker_Tags läuft auf Port 50051
- Worker_Thumbnails läuft auf Port 50052
- Worker_Embeddings läuft auf Port 50053 (skalierbar via Replicas)
- ChromaDB wird separat aus den Parquet-Batches aufgebaut

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
| `CATALOG_DIR` | `/tmp/images/catalog` | Parquet-Batches und Manifest |

## Docker Compose

Der Controller wird zusammen mit den anderen Services gestartet:

```bash
docker compose up --build controller
```

ChromaDB liest die fertigen Batches beim Containerstart und ist ein temporärer Suchindex.
