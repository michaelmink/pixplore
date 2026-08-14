import logging
import torch
import numpy as np
from PIL import Image
from typing import List, Optional
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
    def embed_image(self, image: Image.Image) -> np.ndarray:
        """Generate embedding for a single image. Returns a 1D numpy array (256-dim)."""
        inputs = self.processor(images=image, return_tensors="pt").to(
            self.device, dtype=self.model.dtype
        )
        # ViT → Q-Former (with cross-attention) → vision_projection → 256-dim
        vision_outputs = self.model.vision_model(pixel_values=inputs["pixel_values"])
        image_embeds = vision_outputs[0]
        image_attention_mask = torch.ones(
            image_embeds.size()[:-1], dtype=torch.long, device=self.device
        )
        query_tokens = self.model.query_tokens.expand(image_embeds.shape[0], -1, -1)
        query_outputs = self.model.qformer(
            query_embeds=query_tokens,
            encoder_hidden_states=image_embeds,
            encoder_attention_mask=image_attention_mask,
        )
        # (B, 32, 768) → project each → (B, 32, 256) → mean pool → (B, 256)
        image_feats = query_outputs.last_hidden_state
        image_feats = self.model.vision_projection(image_feats)
        image_feats = torch.nn.functional.normalize(image_feats.mean(dim=1), dim=-1)
        return image_feats.squeeze().cpu().float().numpy()

    @torch.no_grad()
    def embed_images(
        self, images: List[Image.Image], batch_size: int = 8
    ) -> np.ndarray:
        """Generate embeddings for a batch of images. Returns (N, 256) numpy array."""
        all_embeddings = []
        for i in range(0, len(images), batch_size):
            batch = images[i : i + batch_size]
            inputs = self.processor(images=batch, return_tensors="pt").to(
                self.device, dtype=self.model.dtype
            )
            vision_outputs = self.model.vision_model(
                pixel_values=inputs["pixel_values"]
            )
            image_embeds = vision_outputs[0]
            image_attention_mask = torch.ones(
                image_embeds.size()[:-1], dtype=torch.long, device=self.device
            )
            query_tokens = self.model.query_tokens.expand(image_embeds.shape[0], -1, -1)
            query_outputs = self.model.qformer(
                query_embeds=query_tokens,
                encoder_hidden_states=image_embeds,
                encoder_attention_mask=image_attention_mask,
            )
            image_feats = query_outputs.last_hidden_state
            image_feats = self.model.vision_projection(image_feats)
            image_feats = torch.nn.functional.normalize(image_feats.mean(dim=1), dim=-1)
            all_embeddings.append(image_feats.cpu().float().numpy())
        return np.concatenate(all_embeddings, axis=0)

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
        return text_feats.squeeze().cpu().float().numpy()

    @torch.no_grad()
    def embed_texts(self, texts: List[str], batch_size: int = 16) -> np.ndarray:
        """Generate embeddings for multiple texts. Returns (N, 256) numpy array."""
        all_embeddings = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            inputs = self.processor(text=batch, return_tensors="pt", padding=True).to(
                self.device
            )
            query_embeds = self.model.embeddings(input_ids=inputs["input_ids"])
            text_outputs = self.model.qformer(
                query_embeds=query_embeds,
                query_length=0,
                attention_mask=inputs["attention_mask"],
            )
            text_feats = text_outputs.last_hidden_state[:, 0, :]
            text_feats = self.model.text_projection(text_feats)
            text_feats = torch.nn.functional.normalize(text_feats, dim=-1)
            all_embeddings.append(text_feats.cpu().float().numpy())
        return np.concatenate(all_embeddings, axis=0)
