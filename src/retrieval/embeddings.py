from __future__ import annotations

from functools import lru_cache
import hashlib
import numpy as np

try:
    from langchain_core.embeddings import Embeddings
except Exception:
    class Embeddings:
        pass


@lru_cache(maxsize=4)
def _load_model(model_name: str):
    try:
        from sentence_transformers import SentenceTransformer
        # Thu load model local neu co
        return SentenceTransformer(model_name)
    except Exception as exc:
        return None


def _deterministic_dense_embed(text: str, dim: int = 384) -> list[float]:
    """Tao vector 384 chieu chuan hoa cosine tu van ban mot cach tat dinh (reproducible)."""
    tokens = text.lower().split()
    vec = np.zeros(dim, dtype=np.float32)
    for i, token in enumerate(tokens):
        h = int(hashlib.md5(token.encode("utf-8")).hexdigest(), 16)
        idx = h % dim
        sign = 1.0 if ((h >> 8) & 1) else -1.0
        vec[idx] += sign * (1.0 / (1.0 + 0.05 * min(i, 30)))
    norm = np.linalg.norm(vec)
    if norm > 0:
        vec = vec / norm
    else:
        vec[0] = 1.0
    return vec.tolist()


class MiniLMEmbeddings(Embeddings):
    def __init__(self, model_name: str):
        self.model_name = model_name
        self.model = _load_model(model_name)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if self.model is not None:
            try:
                embeddings = self.model.encode(texts, normalize_embeddings=True)
                return embeddings.tolist()
            except Exception:
                pass
        return [_deterministic_dense_embed(t, 384) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        if self.model is not None:
            try:
                embedding = self.model.encode([text], normalize_embeddings=True)
                return embedding[0].tolist()
            except Exception:
                pass
        return _deterministic_dense_embed(text, 384)
