"""Index all images into the vector store using BLIP2 embeddings."""

import logging
import os
import glob
import sys
from pathlib import Path
from datetime import datetime

from PIL import Image
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.common_tools import load_config
from src.indexing.embedding import Blip2Embedder
from src.indexing.vector_store import VectorStore

logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


def get_image_files(raw_dir: str, formats: list) -> list:
    """Recursively find all image files."""
    image_files = []
    for f in glob.glob(os.path.join(raw_dir, "**", "*"), recursive=True):
        if f.lower().endswith(tuple(formats)):
            image_files.append(Path(f))
    return sorted(image_files)


def extract_metadata(image_path: Path) -> dict:
    """Extract basic metadata from an image file."""
    stat = image_path.stat()
    meta = {
        "filename": image_path.name,
        "directory": str(image_path.parent),
        "size_bytes": stat.st_size,
        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
    }
    # Try to extract year from path or filename
    parts = str(image_path).split("/")
    for part in parts:
        if part.isdigit() and 1990 <= int(part) <= 2030:
            meta["year"] = part
            break
    return meta


def main():
    config = load_config("config.yaml")

    raw_path = config["dataset"]["raw_path"]
    image_formats = config["image_formats"]
    embed_config = config.get("embedding", {})
    model_name = embed_config.get("model_name", "Salesforce/blip2-opt-2.7b")
    vector_db_path = embed_config.get("vector_db_path", "./data/vector_db")
    batch_size = embed_config.get("batch_size", 4)

    # Find all images
    image_files = get_image_files(raw_path, image_formats)
    logger.info(f"Found {len(image_files)} images in {raw_path}")

    # Init vector store
    store = VectorStore(persist_dir=vector_db_path)
    already_indexed = store.get_indexed_paths()
    logger.info(f"Already indexed: {len(already_indexed)} images")

    # Filter to only new images
    new_files = [f for f in image_files if str(f) not in already_indexed]
    logger.info(f"New images to index: {len(new_files)}")

    if not new_files:
        logger.info("Nothing to index. Done.")
        return

    # Init embedder
    embedder = Blip2Embedder(model_name=model_name)

    # Process in batches
    for i in tqdm(range(0, len(new_files), batch_size), desc="Indexing"):
        batch_paths = new_files[i : i + batch_size]
        images = []
        valid_paths = []
        metadatas = []

        for img_path in batch_paths:
            try:
                img = Image.open(img_path).convert("RGB")
                images.append(img)
                valid_paths.append(str(img_path))
                metadatas.append(extract_metadata(img_path))
            except Exception as e:
                logger.warning(f"Cannot open {img_path}: {e}")
                continue

        if not images:
            continue

        # Generate embeddings
        embeddings = embedder.embed_images(images, batch_size=len(images))

        # Store in vector DB
        store.add_images_batch(valid_paths, embeddings, metadatas)

    logger.info(f"Indexing complete. Total images in store: {store.count()}")


if __name__ == "__main__":
    main()
