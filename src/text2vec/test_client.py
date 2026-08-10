import numpy as np
import Pyro5.api

# Marshal als Serializer aktivieren
Pyro5.config.SERIALIZER = "marshal"


def main():
    # Connect to the Pyro5 server
    uri = "PYRO:blip2.embedder@localhost:9090"  # Use the same URI as in main.py
    embedder = Pyro5.api.Proxy(uri)  # Create a proxy for the remote object

    # Test embedding a text query
    text_query = "A beautiful sunset over the mountains."
    byte_data, dtype, shape = embedder.embed_text(text_query)
    print(f"Text Query: {text_query}")
    embedding = np.frombuffer(byte_data, dtype=dtype).reshape(shape)
    print(f"Embedding Shape: {embedding.shape}")
    print(f"Embedding (first 10 values): {embedding[:10]}")


if __name__ == "__main__":
    main()
