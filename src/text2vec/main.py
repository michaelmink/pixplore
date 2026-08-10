import numpy as np
from fastapi import FastAPI
from pydantic import BaseModel
from embedding import Blip2Embedder

app = FastAPI()
embedder = Blip2Embedder()


class EmbedRequest(BaseModel):
    text: str


class EmbedResponse(BaseModel):
    embedding: list[float]


@app.post("/embed_text", response_model=EmbedResponse)
def embed_text(req: EmbedRequest):
    byte_data, dtype, shape = embedder.embed_text(req.text)
    embedding = np.frombuffer(byte_data, dtype=dtype).reshape(shape).tolist()
    return EmbedResponse(embedding=embedding)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8081)
