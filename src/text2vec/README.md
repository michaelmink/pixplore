# text2vec

Microservice zur Erzeugung von Text-Embeddings mittels BLIP2 (`Salesforce/blip2-itm-vit-g`). Projiziert Text in einen gemeinsamen 256-dimensionalen Embedding-Raum, der auch für Bild-Embeddings verwendet wird – ermöglicht Cosine-Similarity-Suche zwischen Text-Queries und Bildern.

## Architektur

- **Modell:** Blip2ForImageTextRetrieval (Salesforce/blip2-itm-vit-g)
- **Server:** Pyro5 RPC auf Port 9090
- **Ausgabe:** 256-dim normalisierter Float-Vektor

## Starten

```bash
pip install -r requirements.txt
python main.py
```

Der Service registriert sich unter der URI `PYRO:blip2.embedder@localhost:9090`.

## Docker

```bash
docker build -t text2vec .
docker run -p 9090:9090 text2vec
```

## Client-Beispiel

```python
import numpy as np
import Pyro5.api

Pyro5.config.SERIALIZER = "marshal"
embedder = Pyro5.api.Proxy("PYRO:blip2.embedder@localhost:9090")

byte_data, dtype, shape = embedder.embed_text("A sunset over mountains")
embedding = np.frombuffer(byte_data, dtype=dtype).reshape(shape)
```

## API

| Methode | Beschreibung |
|---------|-------------|
| `embed_text(text: str)` | Gibt `(bytes, dtype, shape)` eines 256-dim Embeddings zurück |
