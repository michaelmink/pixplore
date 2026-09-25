import json
import os
import shutil
import sys
from pathlib import Path
import gcsfs

import chromadb

BASE_PATH = Path(__file__).parent.parent
sys.path.append(str(BASE_PATH))
from shared.storage_manager import StorageManager, ICEBERG_TABLE  # noqa: E402

CHROMA_PATH = os.getenv("CHROMA_PATH", "/tmp/chroma")
THUMBNAIL_PATH = os.getenv("THUMBNAIL_PATH", "/tmp/images/thumbnails")
UPSERT_BATCH_SIZE = int(os.getenv("UPSERT_BATCH_SIZE", "500"))
LOCAL_LIMIT = int(os.getenv("LOCAL_LIMIT"))


def main():
    # Clear the existing ChromaDB data to start fresh.
    shutil.rmtree(CHROMA_PATH, ignore_errors=True)
    # Initialize the ChromaDB client.
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    # initialize collections
    tags = client.get_or_create_collection("image_tags")
    embeddings = client.get_or_create_collection(
        "image_embeddings", metadata={"hnsw:space": "cosine"}
    )
    # Initialize the storage manager to interact with the Iceberg catalog.
    storage_manager = StorageManager()
    rows = storage_manager.get_catalog_all_rows()
    # Ensure the local thumbnail directory exists and initialize the GCS filesystem.
    os.makedirs(THUMBNAIL_PATH, exist_ok=True)
    fs = gcsfs.GCSFileSystem()
    # Process the catalog rows in batches for upserting into ChromaDB and materializing thumbnails.
    if LOCAL_LIMIT:
        rows = rows[:LOCAL_LIMIT]

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
