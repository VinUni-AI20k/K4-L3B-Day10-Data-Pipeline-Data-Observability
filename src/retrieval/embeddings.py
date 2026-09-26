from __future__ import annotations

from functools import lru_cache

from langchain_core.embeddings import Embeddings


@lru_cache(maxsize=4)
def _load_model(model_name: str):
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        if model_name not in {"all-MiniLM-L6-v2", "sentence-transformers/all-MiniLM-L6-v2"}:
            raise ValueError(f"ONNX fallback does not support embedding model {model_name!r}")
        from chromadb.utils.embedding_functions.onnx_mini_lm_l6_v2 import ONNXMiniLM_L6_V2

        return ONNXMiniLM_L6_V2()
    return SentenceTransformer(model_name)


class MiniLMEmbeddings(Embeddings):
    def __init__(self, model_name: str):
        self.model = _load_model(model_name)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if hasattr(self.model, "encode"):
            return self.model.encode(texts, normalize_embeddings=True).tolist()
        return [embedding.tolist() for embedding in self.model(texts)]

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]
