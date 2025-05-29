from sentence_transformers import SentenceTransformer

# Hugging Face용 래퍼 함수
class LangchainEmbeddingWrapper:
    def __init__(self, model_name: str = "dragonkue/BGE-m3-ko", device: str = "cuda"):
        self.model = SentenceTransformer(model_name)
        self.model.to(device)

    def __call__(self, text: str):
        return self.model.encode(text)
