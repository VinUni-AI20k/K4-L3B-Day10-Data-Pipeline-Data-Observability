from __future__ import annotations

from dataclasses import dataclass
import re

from core.config import Settings
from core.utils import first_sentence
from retrieval.index import LocalEmbeddingIndex, SearchResult
from retrieval.llm import build_llm


@dataclass(frozen=True)
class AnswerResult:
    question: str
    answer: str
    answer_source: str
    retrieved_doc_ids: list[str]
    retrieved_contexts: list[str]
    retrieved_titles: list[str]


def _extract_answer(question: str, top_result: SearchResult) -> str:
    lowered = question.lower()
    metadata = top_result.metadata
    if "who authored" in lowered or "list the authors" in lowered:
        return metadata["authors_joined"]
    if "when was" in lowered or "publication date" in lowered or "published on" in lowered:
        return metadata["published"]
    if "what categories" in lowered:
        return metadata["categories_joined"]
    return first_sentence(metadata["summary"])


def _message_text(response) -> str:
    content = getattr(response, "content", response)
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        return "\n".join(
            item.get("text", "") if isinstance(item, dict) else str(item)
            for item in content
        ).strip()
    return str(content).strip()


def _answer_with_llm(question: str, result: SearchResult, settings: Settings) -> str:
    prompt = f"""
Answer the question using only the paper metadata below.
Return only the requested answer, without a preamble or explanation.
- For an authors question, copy the complete author list.
- For a publication-date question, return the ISO date exactly.
- For a categories question, copy the complete category list.
- For a summary question, copy the first complete sentence of Summary exactly.
- If the metadata does not contain the answer, return: I don't know from the indexed corpus.

Question: {question}

Paper metadata:
{result.content}
""".strip()
    response = build_llm(settings=settings, temperature=0.0).invoke(prompt)
    answer = _message_text(response)
    if not answer:
        raise ValueError("Configured LLM returned an empty answer.")
    return answer


def answer_question(question: str, settings: Settings, index: LocalEmbeddingIndex, top_k: int | None = None) -> AnswerResult:
    title_match = re.search(r"'([^']+)'", question)
    exact = index.lookup(title_match.group(1)) if title_match else None
    retrieved = index.search(question, top_k=top_k)
    if exact:
        exact_result = SearchResult(
            paper_id=exact["paper_id"],
            title=exact["title"],
            score=1.0,
            content=exact["content"],
            metadata=exact["metadata"],
        )
        deduped = [exact_result] + [item for item in retrieved if item.paper_id != exact_result.paper_id]
        retrieved = deduped[: (top_k or settings.top_k)]
    if not retrieved:
        answer = "I don't know from the indexed corpus."
        answer_source = "no_context"
    else:
        try:
            answer = _answer_with_llm(question, retrieved[0], settings)
            answer_source = "llm"
        except Exception:
            answer = _extract_answer(question, retrieved[0])
            answer_source = "metadata_fallback"
    return AnswerResult(
        question=question,
        answer=answer,
        answer_source=answer_source,
        retrieved_doc_ids=[item.paper_id for item in retrieved],
        retrieved_contexts=[item.content for item in retrieved],
        retrieved_titles=[item.title for item in retrieved],
    )
