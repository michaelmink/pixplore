"""Search indexed images using natural language text queries."""

import argparse
import logging
import sys
from pathlib import Path

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


def search(query: str, n_results: int = 10, model_name: str = None, vector_db_path: str = None):
    """Search for images matching a text query."""
    config = load_config("config.yaml")
    embed_config = config.get("embedding", {})

    if model_name is None:
        model_name = embed_config.get("model_name", "Salesforce/blip2-opt-2.7b")
    if vector_db_path is None:
        vector_db_path = embed_config.get("vector_db_path", "./data/vector_db")

    # Init
    store = VectorStore(persist_dir=vector_db_path)
    embedder = Blip2Embedder(model_name=model_name)

    # Embed query text
    query_embedding = embedder.embed_text(query)

    # Search
    results = store.search(query_embedding, n_results=n_results)

    return results


def main():
    parser = argparse.ArgumentParser(description="Search images by text query")
    parser.add_argument("query", type=str, help="Text query to search for")
    parser.add_argument("-n", "--n-results", type=int, default=10, help="Number of results")
    args = parser.parse_args()

    results = search(args.query, n_results=args.n_results)

    print(f"\nResults for: '{args.query}'\n{'=' * 50}")
    for i, (path, distance, meta) in enumerate(
        zip(results["ids"], results["distances"], results["metadatas"])
    ):
        similarity = 1 - distance  # cosine distance → similarity
        print(f"{i + 1:3d}. [{similarity:.3f}] {path}")
        if "year" in meta:
            print(f"     year: {meta['year']}")


if __name__ == "__main__":
    main()
