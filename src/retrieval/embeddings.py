from __future__ import annotations

from functools import lru_cache
import os
from typing import TYPE_CHECKING

from langchain_core.embeddings import Embeddings

if TYPE_CHECKING:
    from core.config import Settings


@lru_cache(maxsize=4)
def _load_model(model_name: str):
    """Lazy load sentence_transformers để không ép import khi sử dụng API Embeddings."""
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(model_name)


class MiniLMEmbeddings(Embeddings):
    def __init__(self, model_name: str):
        self.model = _load_model(model_name)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        embeddings = self.model.encode(texts, normalize_embeddings=True)
        return embeddings.tolist()

    def embed_query(self, text: str) -> list[float]:
        embedding = self.model.encode([text], normalize_embeddings=True)
        return embedding[0].tolist()


def build_embeddings(settings: Settings) -> Embeddings:
    """Khởi tạo Embedding model dựa theo provider cấu hình trong .env / settings.

    Hỗ trợ:
    - gemini: GoogleGenerativeAIEmbeddings (API)
    - openai: OpenAIEmbeddings (API)
    - mặc định / fallback: MiniLMEmbeddings (Local)
    """
    provider = getattr(settings, "llm_provider", "").lower()
    embedding_provider = os.getenv("EMBEDDING_PROVIDER", provider).lower()

    if embedding_provider == "gemini" and getattr(settings, "google_api_key", None):
        try:
            from langchain_google_genai import GoogleGenerativeAIEmbeddings

            model_name = os.getenv("EMBEDDING_MODEL", os.getenv("EMBEDDING_MODEL_NAME", "models/text-embedding-004"))
            return GoogleGenerativeAIEmbeddings(
                model=model_name,
                google_api_key=settings.google_api_key,
            )
        except Exception as exc:
            print(f"⚠️ Gemini API Embeddings không sẵn sàng ({exc}), dùng fallback MiniLM.")

    if embedding_provider == "openai" and getattr(settings, "openai_api_key", None):
        try:
            from langchain_openai import OpenAIEmbeddings

            model_name = os.getenv("EMBEDDING_MODEL", os.getenv("EMBEDDING_MODEL_NAME", "text-embedding-3-small"))
            return OpenAIEmbeddings(
                model=model_name,
                api_key=settings.openai_api_key,
            )
        except Exception as exc:
            print(f"⚠️ OpenAI API Embeddings không sẵn sàng ({exc}), dùng fallback MiniLM.")

    return MiniLMEmbeddings(settings.embedding_model)
