from __future__ import annotations

from dataclasses import dataclass
import re

from core.config import Settings
from retrieval.index import LocalEmbeddingIndex, SearchResult


@dataclass(frozen=True)
class AnswerResult:
    question: str
    answer: str
    retrieved_doc_ids: list[str]
    retrieved_contexts: list[str]
    retrieved_titles: list[str]


def _extract_answer(question: str, top_result: SearchResult) -> str:
    """Return the requested field from the highest-ranked paper.

    Benchmark questions are written in Vietnamese, while the original routing
    keywords only covered English.  Metadata answers are deterministic and
    avoid asking the LLM to infer a value that is already present in the index.
    """
    lowered = question.casefold()
    metadata = top_result.metadata
    if any(keyword in lowered for keyword in ("who authored", "list the authors", "author", "tác giả")):
        return str(metadata.get("authors_joined", ""))
    if any(
        keyword in lowered
        for keyword in ("when was", "publication date", "published on", "ngày công bố", "công bố vào", "ngày tháng năm")
    ):
        return str(metadata.get("published", ""))
    if any(keyword in lowered for keyword in ("what categories", "category", "categories", "lĩnh vực", "phân loại")):
        return str(metadata.get("categories_joined", ""))
    return str(metadata.get("summary", ""))


def generate_rag_answer(question: str, contexts: list[str], settings: Settings) -> str:
    """Sử dụng LLM model cấu hình trong .env (Gemini, OpenAI, v.v.) để sinh câu trả lời RAG."""
    from retrieval.llm import build_llm

    if not contexts:
        return "I don't know from the indexed corpus."

    joined_contexts = "\n\n".join(f"--- Document [{i+1}] ---\n{c}" for i, c in enumerate(contexts))
    prompt = f"""You are an expert AI assistant answering questions about scholarly papers based solely on the provided contexts.

{joined_contexts}

Question: {question}

Instructions:
1. Provide a direct, concise, and accurate answer grounded strictly in the given documents.
2. If the answer cannot be determined from the documents, clearly say: "I don't know from the indexed corpus."
3. Do not assume or extrapolate beyond the provided text.
"""
    try:
        llm = build_llm(settings=settings, temperature=0.0)
        response = llm.invoke(prompt)
        return getattr(response, "content", str(response)).strip()
    except Exception as exc:
        return ""


def answer_question(
    question: str,
    settings: Settings,
    index: LocalEmbeddingIndex,
    top_k: int | None = None,
    use_llm: bool = False,
) -> AnswerResult:
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
    elif use_llm:
        # Gọi mô hình LLM từ provider trong .env
        llm_answer = generate_rag_answer(question, [item.content for item in retrieved], settings)
        answer = llm_answer if llm_answer else _extract_answer(question, retrieved[0])
    else:
        answer = _extract_answer(question, retrieved[0])
    return AnswerResult(
        question=question,
        answer=answer,
        retrieved_doc_ids=[item.paper_id for item in retrieved],
        retrieved_contexts=[item.content for item in retrieved],
        retrieved_titles=[item.title for item in retrieved],
    )
