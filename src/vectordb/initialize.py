import glob
import json
import os
import shutil

import chromadb
import pyarrow.parquet as parquet


CATALOG_GLOB = os.getenv("CATALOG_GLOB", "/data/catalog/*.parquet")
CHROMA_PATH = os.getenv("CHROMA_PATH", "/tmp/chroma")


def main():
    batch_files = sorted(glob.glob(CATALOG_GLOB))

    shutil.rmtree(CHROMA_PATH, ignore_errors=True)
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    tags = client.get_or_create_collection("image_tags")
    embeddings = client.get_or_create_collection(
        "image_embeddings", metadata={"hnsw:space": "cosine"}
    )

    for batch_file in batch_files:
        table = parquet.read_table(batch_file)
        rows = table.to_pylist()
        ids = [row["image_id"] for row in rows]
        metadata = [json.loads(row["metadata"]) for row in rows]
        documents = [row["filename"] for row in rows]
        vectors = [row["embedding"] for row in rows]

        tags.upsert(ids=ids, metadatas=metadata, documents=documents)
        embeddings.upsert(ids=ids, embeddings=vectors, documents=documents)

    print(f"Initialized ChromaDB from {len(batch_files)} catalog batch(es)")


if __name__ == "__main__":
    main()
