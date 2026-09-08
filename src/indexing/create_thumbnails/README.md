# create_thumbnails – gRPC Thumbnail Worker

Erzeugt JPEG-Thumbnails und gibt den erzeugten Pfad an den Controller zurück.

## Starten

```bash
python worker_thumbnails.py
```

Der gRPC-Server läuft auf Port `50052`. Der Worker schreibt nur die Thumbnail-Datei; persistente Metadaten und Embeddings werden vom Controller als Parquet-Batch gespeichert.
