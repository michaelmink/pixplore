import logging
from pathlib import Path
from typing import Dict, List, Optional

import chromadb
import numpy as np

logger = logging.getLogger(__name__)


class VectorStore:
    """Local persistent vector store backed by ChromaDB."""

    def __init__(self, persist_dir: str, collection_name: str = "image_embeddings"):
        self.persist_dir = Path(persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Initializing ChromaDB at {self.persist_dir}")
        self.client = chromadb.PersistentClient(path=str(self.persist_dir))
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info(
            f"Collection '{collection_name}' has {self.collection.count()} entries."
        )

    def add_image(
        self,
        image_path: str,
        embedding: np.ndarray,
        metadata: Optional[Dict] = None,
    ):
        """Add a single image embedding to the store."""
        doc_id = image_path  # use path as unique ID
        meta = metadata or {}
        meta["path"] = image_path

        self.collection.upsert(
            ids=[doc_id],
            embeddings=[embedding.tolist()],
            metadatas=[meta],
        )

    def add_images_batch(
        self,
        image_paths: List[str],
        embeddings: np.ndarray,
        metadatas: Optional[List[Dict]] = None,
    ):
        """Add a batch of image embeddings."""
        if metadatas is None:
            metadatas = [{"path": p} for p in image_paths]
        else:
            for meta, path in zip(metadatas, image_paths):
                meta["path"] = path

        self.collection.upsert(
            ids=image_paths,
            embeddings=embeddings.tolist(),
            metadatas=metadatas,
        )

    def search(
        self,
        query_embedding: np.ndarray,
        n_results: int = 10,
        where: Optional[Dict] = None,
    ) -> Dict:
        """Search for similar images by embedding vector.

        Returns dict with keys: ids, distances, metadatas
        """
        kwargs = {
            "query_embeddings": [query_embedding.tolist()],
            "n_results": n_results,
        }
        if where:
            kwargs["where"] = where

        results = self.collection.query(**kwargs)
        return {
            "ids": results["ids"][0],
            "distances": results["distances"][0],
            "metadatas": results["metadatas"][0],
        }

    def get_indexed_paths(self) -> set:
        """Return set of all image paths currently in the store."""
        if self.collection.count() == 0:
            return set()
        all_data = self.collection.get()
        return set(all_data["ids"])

    def count(self) -> int:
        return self.collection.count()

    def delete(self, image_paths: List[str]):
        """Remove entries by image path."""
        self.collection.delete(ids=image_paths)
