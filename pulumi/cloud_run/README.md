# Pixplore - Cloud Run Deployment

Deployt frontend, text2vec und ChromaDB als getrennte Cloud-Run-Services.

## Architektur

```text
Frontend (oeffentlich)
  |-- ID-Token -> text2vec (nur Frontend-SA)
  `-- ID-Token -> chromadb (Frontend-SA und konfigurierter Benutzer)

ChromaDB
  |-- skaliert auf 0 Instanzen
  |-- liest catalog/*.parquet aus GCS beim Start
  `-- baut den Suchindex lokal unter /tmp/chroma auf
```

Parquet-Batches sind die persistente Quelle der Bilddaten. ChromaDB ist ein temporaerer Suchindex und schreibt nicht in den GCS-Bucket.

## Voraussetzungen

- Pulumi CLI und Python installiert
- `gcloud` authentifiziert
- Cloud Run API, Artifact Registry API und Cloud Storage API aktiviert
- Docker verfuegbar fuer den Image-Build

## Setup

```bash
cd pulumi/cloud_run
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
pulumi login --local
pulumi stack init prod
pulumi config set gcp:project pixplore-503406
pulumi config set gcp:region europe-west3
pulumi config set bucket-name pixplore-bucket
pulumi config set admin-email deine-adresse@example.com
```

`admin-email` erhaelt `roles/run.invoker` auf ChromaDB fuer authentifizierte Laptop-Zugriffe.

## Deployen

```bash
pulumi preview
pulumi up
pulumi stack output
```

Die Outputs enthalten URLs fuer Frontend, ChromaDB und text2vec.

## Katalog veroeffentlichen

Der lokale Controller schreibt Batches unter `/tmp/images/catalog`. Vor dem naechsten Cloud-Run-Start muessen sie in den Bucket synchronisiert werden:

```bash
gsutil -m rsync -r /tmp/images/catalog gs://pixplore-bucket/catalog
```

Danach eine neue Cloud-Run-Revision erzwingen:

```bash
pulumi config set catalog-version "$(date -u +%Y%m%dT%H%M%SZ)"
pulumi up
```

Die neue Revision liest beim Start alle Dateien unter `catalog/*.parquet` und erzeugt den lokalen Index neu. Ohne diese neue Revision kann eine bereits laufende Instanz weiterhin den alten Index bedienen.

## Laptop-Zugriff auf ChromaDB

```bash
TOKEN=$(gcloud auth print-identity-token)
curl -H "Authorization: Bearer $TOKEN" \
  "$(pulumi stack output chromadb_url)/api/v1/heartbeat"
```

## Ressourcen

| Service | Skalierung | Persistenz |
|---|---:|---|
| frontend | 0-2 | GCS read-only fuer Bilder/Thumbnails |
| text2vec | 0-2 | stateless |
| chromadb | 0-1 | Parquet-Batches in GCS, Index in `/tmp` |
