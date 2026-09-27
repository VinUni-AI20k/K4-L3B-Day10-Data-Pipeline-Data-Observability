from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import math
import os
from uuid import uuid4

import chromadb
import pandas as pd

from core.config import Settings
from core.utils import read_json, safe_slug, write_json
from retrieval.embeddings import MiniLMEmbeddings


@dataclass(frozen=True)
class SearchResult:
    paper_id: str
    title: str
    score: float
    content: str
    metadata: dict[str, Any]


class LocalEmbeddingIndex:
    def __init__(
        self,
        settings: Settings,
        collection_name: str,
        documents: list[dict[str, Any]],
        persist_path: Path,
        *,
        client=None,
        embedding_model=None,
    ):
        self.settings = settings
        self.collection_name = collection_name
        self.documents = documents
        self.persist_path = persist_path
        self.embedding_backend = "chroma"
        self.embedding_model = embedding_model or MiniLMEmbeddings(settings.embedding_model)
        self.client = client or chromadb.PersistentClient(path=str(persist_path))
        try:
            self.collection = self.client.get_collection(name=collection_name)
        except Exception:
            self.client.close()
            raise
        self.documents_by_paper_id = {document["paper_id"].lower(): document for document in documents}
        self.documents_by_title = {document["title"].lower(): document for document in documents}

    @staticmethod
    def _build_documents(df: pd.DataFrame) -> list[dict[str, Any]]:
        records = df.to_dict(orient="records")
        documents: list[dict[str, Any]] = []
        for index, row in enumerate(records):
            documents.append(
                {
                    "record_id": f"{row['paper_id']}::{index}",
                    "paper_id": row["paper_id"],
                    "title": row["title"],
                    "content": row["text_for_embedding"],
                    "metadata": {
                        "paper_id": row["paper_id"],
                        "title": row["title"],
                        "published": row["published"],
                        "authors_joined": row["authors_joined"],
                        "categories_joined": row["categories_joined"],
                        "summary": row["summary"],
                        "abs_url": row["abs_url"],
                        "pdf_url": row["pdf_url"],
                    },
                }
            )
        return documents

    @staticmethod
    def _derive_collection_name(settings: Settings, embeddings_output_path: Path | None) -> str:
        if embeddings_output_path is None:
            return settings.baseline_collection_name

        name_map = {
            settings.paths.embeddings_json.resolve(): settings.baseline_collection_name,
            settings.paths.corrupted_embeddings_json.resolve(): settings.corrupted_collection_name,
            settings.paths.repaired_embeddings_json.resolve(): settings.repaired_collection_name,
        }
        resolved_path = embeddings_output_path.resolve()
        if resolved_path in name_map:
            return name_map[resolved_path]
        return safe_slug(embeddings_output_path.stem)

    @classmethod
    def build(
        cls,
        df: pd.DataFrame,
        settings: Settings,
        embeddings_output_path: Path | None = None,
    ) -> "LocalEmbeddingIndex":
        logical_name = cls._derive_collection_name(settings, embeddings_output_path)
        collection_name = f"{logical_name}-{uuid4().hex[:12]}"
        documents = cls._build_documents(df)
        if not documents:
            raise ValueError("Cannot build an empty index")
        persist_path = settings.paths.chroma_dir
        embedding_model = MiniLMEmbeddings(settings.embedding_model)
        # Encoding and validation must succeed before touching the database.
        embeddings = embedding_model.embed_documents([document["content"] for document in documents])
        if (len(embeddings) != len(documents) or not embeddings or not embeddings[0]
                or any(len(vector) != len(embeddings[0]) or not all(math.isfinite(value) for value in vector)
                       for vector in embeddings)):
            raise ValueError("Embedding output has invalid count, dimension, or non-finite values")
        persist_path.mkdir(parents=True, exist_ok=True)
        client = chromadb.PersistentClient(path=str(persist_path))
        created = False
        try:
            collection = client.create_collection(
                name=collection_name,
                configuration={"hnsw": {"space": "cosine"}},
            )
            created = True
            collection.add(
                ids=[document["record_id"] for document in documents],
                embeddings=embeddings,
                documents=[document["content"] for document in documents],
                metadatas=[document["metadata"] for document in documents],
            )
            if collection.count() != len(documents):
                raise RuntimeError("Candidate index document count differs from input")
            if not collection.query(query_embeddings=[embeddings[0]], n_results=1)["ids"][0]:
                raise RuntimeError("Candidate index failed its retrieval smoke test")
            index = cls(settings, collection_name, documents, persist_path,
                        client=client, embedding_model=embedding_model)
            manifest_path = embeddings_output_path or settings.paths.embeddings_json
            # The atomic manifest is the publication pointer. Existing collections stay intact.
            write_json(manifest_path, {
                "schema_version": 2,
                "backend": "chroma",
                "embedding_model": settings.embedding_model,
                "persist_path": Path(os.path.relpath(persist_path, manifest_path.parent)).as_posix(),
                "collection_name": collection_name,
                "logical_collection_name": logical_name,
                "dimension": len(embeddings[0]),
                "documents": documents,
            })
            return index
        except Exception:
            try:
                if created:
                    client.delete_collection(name=collection_name)
            finally:
                client.close()
            raise

    @classmethod
    def load(cls, settings: Settings, embeddings_path: Path | None = None) -> "LocalEmbeddingIndex":
        manifest_path = Path(embeddings_path or settings.paths.embeddings_json)
        payload = read_json(manifest_path)
        persist_path = Path(payload["persist_path"])
        if not persist_path.is_absolute():
            persist_path = (manifest_path.parent / persist_path).resolve()
        elif payload.get("schema_version", 1) == 1:
            # Old manifests may point at a different machine; use this workspace's DB.
            persist_path = settings.paths.chroma_dir
            if payload["collection_name"] in {settings.corrupted_collection_name, settings.repaired_collection_name}:
                persist_path = persist_path / "comparison"
        if payload["embedding_model"] != settings.embedding_model:
            raise ValueError("Manifest embedding model does not match settings")
        return cls(
            settings=settings,
            collection_name=payload["collection_name"],
            documents=payload["documents"],
            persist_path=persist_path,
        )

    def close(self) -> None:
        """Flush/release the persistent database before hashing or copying artifacts."""
        self.client.close()

    def search(self, query: str, top_k: int | None = None) -> list[SearchResult]:
        limit = self.settings.top_k if top_k is None else top_k
        if limit < 1:
            raise ValueError("top_k must be positive")
        count = self.collection.count()
        if count == 0:
            return []
        query_embedding = self.embedding_model.embed_query(query)
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=min(limit, count),
            include=["documents", "metadatas", "distances"],
        )
        ids = results.get("ids", [[]])[0]
        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        scored: list[SearchResult] = []
        for record_id, content, metadata, distance in zip(ids, documents, metadatas, distances, strict=False):
            if not record_id or not metadata or not content:
                continue
            scored.append(
                SearchResult(
                    paper_id=str(metadata["paper_id"]),
                    title=str(metadata["title"]),
                    score=max(0.0, 1.0 - float(distance or 0.0)),
                    content=str(content),
                    metadata=dict(metadata),
                )
            )
        return scored

    def lookup(self, value: str) -> dict[str, Any] | None:
        needle = value.strip().lower()
        if needle in self.documents_by_paper_id:
            return self.documents_by_paper_id[needle]
        if needle in self.documents_by_title:
            return self.documents_by_title[needle]
        return None
