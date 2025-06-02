from langchain.embeddings.base import Embeddings
from typing import List
from sentence_transformers import SentenceTransformer

class LangchainEmbeddingWrapper(Embeddings):
    def __init__(self, model_name: str = "dragonkue/BGE-m3-ko", device: str = "cuda"):
        self.model = SentenceTransformer(model_name)
        self.model.to(device)

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return self.model.encode(texts, convert_to_numpy=True).tolist()

    def embed_query(self, text: str) -> List[float]:
        return self.model.encode(text, convert_to_numpy=True).tolist()
