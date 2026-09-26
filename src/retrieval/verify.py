"""Build and smoke-test the three RAG indexes: python -m retrieval.verify.

Uses existing clean/corrupted/repaired JSON artifacts; does not call an LLM API.
Only the three configured collections and their embedding manifests are replaced.
"""

from dataclasses import replace

import pandas as pd

from core.config import load_settings
from retrieval.index import LocalEmbeddingIndex
from retrieval.llm import build_llm
from retrieval.qa import answer_question


def main() -> None:
    settings = load_settings()
    stages = [
        (settings.paths.clean_json, settings.paths.embeddings_json, settings.baseline_collection_name),
        (settings.paths.corrupted_clean_json, settings.paths.corrupted_embeddings_json, settings.corrupted_collection_name),
        (settings.paths.repaired_clean_json, settings.paths.repaired_embeddings_json, settings.repaired_collection_name),
    ]
    for source, _, _ in stages:
        if not source.exists():
            raise FileNotFoundError(f"Missing stage dataset: {source}. Generate its pipeline artifact first.")
    indexes = []
    for source, manifest, name in stages:
        frame = pd.read_json(source, convert_dates=False)
        index = LocalEmbeddingIndex.build(frame, settings, manifest)
        assert index.collection_name == name
        assert index.collection.count() == len(frame)
        loaded = LocalEmbeddingIndex.load(settings, manifest)
        assert loaded.collection.get()["ids"] == index.collection.get()["ids"]
        if len(frame):
            row = frame.iloc[0]
            hits = loaded.search(row["text_for_embedding"], top_k=len(frame) + 1)
            assert len(hits) == len(frame)
            assert hits[0].paper_id == row["paper_id"]
            assert hits[0].score > 0.99
            answer = answer_question(f"Who authored '{row['title']}'?", settings, loaded)
            assert answer.retrieved_doc_ids
            assert answer.answer == loaded.lookup(row["title"])["metadata"]["authors_joined"]
        assert loaded.search("   ") == []
        try:
            loaded.search("paper", top_k=0)
        except ValueError:
            pass
        else:
            raise AssertionError("top_k=0 should be rejected")
        indexes.append((index, len(frame)))
        print(f"PASS {name}: {len(frame)} records, persisted and queried")

    # Later builds must leave earlier collections intact, including duplicate rows.
    for index, count in indexes:
        assert index.collection.count() == count
    assert len({index.collection.id for index, _ in indexes}) == 3
    mock = build_llm(replace(settings, llm_provider="mock"))
    assert mock.invoke("Test").content
    print("PASS: three isolated collections, RAG metadata answers, and Mock LLM")


if __name__ == "__main__":
    main()
