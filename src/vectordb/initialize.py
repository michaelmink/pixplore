import json
import os
import shutil

import chromadb
import gcsfs
from pyiceberg.catalog.sql import SqlCatalog
from pyiceberg.exceptions import NoSuchTableError

ICEBERG_CATALOG_URI = os.getenv(
    "ICEBERG_CATALOG_URI", "sqlite:////tmp/iceberg_catalog.db"
)
ICEBERG_WAREHOUSE = os.getenv("ICEBERG_WAREHOUSE", "gs://pixplore-bucket/warehouse")
GCS_PROJECT = os.getenv("GCS_PROJECT", "pixplore-503406")
ICEBERG_NAMESPACE = os.getenv("ICEBERG_NAMESPACE", "catalog")
ICEBERG_TABLE = os.getenv("ICEBERG_TABLE", f"{ICEBERG_NAMESPACE}.images")

CHROMA_PATH = os.getenv("CHROMA_PATH", "/tmp/chroma")
THUMBNAIL_PATH = os.getenv("THUMBNAIL_PATH", "/tmp/images/thumbnails")
MATERIALIZE_THUMBNAILS = os.getenv("MATERIALIZE_THUMBNAILS", "true").lower() == "true"
UPSERT_BATCH_SIZE = int(os.getenv("UPSERT_BATCH_SIZE", "500"))


def _table_location():
    namespace, name = ICEBERG_TABLE.split(".", 1)
    return f"{ICEBERG_WAREHOUSE.rstrip('/')}/{namespace}/{name}"


def _latest_metadata_location():
    """Newest metadata.json on GCS — used to recover the table without a catalog file."""
    # ohne project=, sonst weicht gcsfs bei User-ADC auf den VM-Metadata-SA aus
    fs = gcsfs.GCSFileSystem()
    metadata_dir = f"{_table_location()}/metadata".replace("gs://", "")
    if not fs.exists(metadata_dir):
        return None
    metas = [p for p in fs.ls(metadata_dir) if p.endswith(".metadata.json")]
    return f"gs://{sorted(metas)[-1]}" if metas else None


def load_or_register_table():
    catalog = SqlCatalog(
        "pixplore",
        **{
            "uri": ICEBERG_CATALOG_URI,
            "warehouse": ICEBERG_WAREHOUSE,
        },
    )
    catalog.create_namespace_if_not_exists(ICEBERG_NAMESPACE)
    try:
        return catalog.load_table(ICEBERG_TABLE)
    except NoSuchTableError:
        latest = _latest_metadata_location()
        if not latest:
            return None
        return catalog.register_table(ICEBERG_TABLE, metadata_location=latest)


def main():
    table = load_or_register_table()

    shutil.rmtree(CHROMA_PATH, ignore_errors=True)
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    tags = client.get_or_create_collection("image_tags")
    embeddings = client.get_or_create_collection(
        "image_embeddings", metadata={"hnsw:space": "cosine"}
    )

    if table is None:
        print(
            f"Iceberg table '{ICEBERG_TABLE}' noch nicht vorhanden — "
            "starte mit leerem ChromaDB."
        )
        return

    fields = ["image_id", "metadata", "embedding"]
    if MATERIALIZE_THUMBNAILS:
        fields.append("thumbnail_uri")
    arrow = table.scan(selected_fields=tuple(fields)).to_arrow()
    rows = arrow.to_pylist()

    fs = None
    if MATERIALIZE_THUMBNAILS:
        os.makedirs(THUMBNAIL_PATH, exist_ok=True)
        fs = gcsfs.GCSFileSystem()

    for i in range(0, len(rows), UPSERT_BATCH_SIZE):
        chunk = rows[i : i + UPSERT_BATCH_SIZE]
        ids = [row["image_id"] for row in chunk]
        # leere Metadaten -> None, sonst lehnt ChromaDB den Eintrag ab
        metadata = [json.loads(row["metadata"]) or None for row in chunk]
        documents = [row["image_id"] for row in chunk]
        vectors = [row["embedding"] for row in chunk]

        tags.upsert(ids=ids, metadatas=metadata, documents=documents)
        embeddings.upsert(ids=ids, embeddings=vectors, documents=documents)

        # Thumbnails aus GCS auf den lokalen Serving-Pfad holen
        if MATERIALIZE_THUMBNAILS:
            for row in chunk:
                thumb_uri = row["thumbnail_uri"]
                if not thumb_uri:
                    continue
                thumb_name = os.path.basename(thumb_uri)
                fs.get(thumb_uri, os.path.join(THUMBNAIL_PATH, thumb_name))

    print(
        f"Rebuilt ChromaDB from Iceberg table '{ICEBERG_TABLE}' "
        f"({len(rows)} image(s)) into {CHROMA_PATH}"
    )


if __name__ == "__main__":
    main()
