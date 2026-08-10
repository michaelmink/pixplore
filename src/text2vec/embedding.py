import logging
import torch
import numpy as np
from typing import Optional
from transformers import Blip2Processor, Blip2ForImageTextRetrieval

logger = logging.getLogger(__name__)


class Blip2Embedder:
    """Generates image and text embeddings using BLIP2's retrieval model.

    Uses Blip2ForImageTextRetrieval which projects both modalities into a
    shared 256-dim space via learned projection heads, enabling cosine
    similarity search between text queries and image embeddings.
    """

    def __init__(
        self,
        model_name: str = "Salesforce/blip2-itm-vit-g",
        device: Optional[str] = None,
    ):
        if device is None:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device

        logger.info(f"Loading BLIP2 retrieval model '{model_name}' on {self.device}...")
        self.processor = Blip2Processor.from_pretrained(model_name)
        self.model = Blip2ForImageTextRetrieval.from_pretrained(
            model_name,
            torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
        ).to(self.device)
        self.model.eval()
        logger.info("BLIP2 model loaded.")

    @torch.no_grad()
    def embed_text(self, text: str) -> np.ndarray:
        """Generate embedding for a text query. Returns a 1D numpy array (256-dim)."""
        inputs = self.processor(text=text, return_tensors="pt", padding=True).to(
            self.device
        )
        # Text → embeddings → Q-Former (self-attention only, query_length=0) → text_projection
        query_embeds = self.model.embeddings(input_ids=inputs["input_ids"])
        text_outputs = self.model.qformer(
            query_embeds=query_embeds,
            query_length=0,
            attention_mask=inputs["attention_mask"],
        )
        text_feats = text_outputs.last_hidden_state[:, 0, :]  # CLS token
        text_feats = self.model.text_projection(text_feats)
        text_feats = torch.nn.functional.normalize(text_feats, dim=-1)

        np_array = text_feats.squeeze().cpu().float().numpy()
        # return as bytes
        return np_array.tobytes(), np_array.dtype.name, np_array.shape
