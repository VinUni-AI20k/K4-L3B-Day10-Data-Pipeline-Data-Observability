from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from core.config import Settings
from retrieval.index import LocalEmbeddingIndex
from retrieval.llm import build_llm


class SimplePaperAgent:
    def __init__(self, settings: Settings, index: LocalEmbeddingIndex):
        self.settings = settings
        self.index = index
        self.llm = build_llm(settings=settings, temperature=0.0)

    def _semantic_search(self, query: str, top_k: int = 4) -> str:
        results = self.index.search(query, top_k=top_k)
        if not results:
            return "No relevant papers found in the local corpus."
        lines: list[str] = []
        for result in results:
            lines.append(
                f"paper_id: {result.paper_id}\n"
                f"title: {result.title}\n"
                f"score: {result.score:.4f}\n"
                f"{result.content}"
            )
        return "\n\n".join(lines)

    def _lookup_paper(self, paper_id_or_title: str) -> str:
        record = self.index.lookup(paper_id_or_title)
        if not record:
            return "No exact paper match found."
        return (
            f"paper_id: {record['paper_id']}\n"
            f"title: {record['title']}\n"
            f"{record['content']}"
        )

    def invoke(self, payload: dict[str, Any]) -> dict[str, Any]:
        messages = payload.get("messages", [])
        if not messages:
            return {"messages": [SimpleNamespace(content="No question provided.")]}

        last_message = messages[-1]
        if isinstance(last_message, dict):
            question = str(last_message.get("content", "")).strip()
        else:
            question = str(getattr(last_message, "content", "")).strip()

        if not question:
            return {"messages": [SimpleNamespace(content="No question provided.")]}

        context = self._semantic_search(question, top_k=self.settings.top_k)
        exact = self.index.lookup(question)
        if exact:
            context = (
                f"paper_id: {exact['paper_id']}\n"
                f"title: {exact['title']}\n"
                f"{exact['content']}\n\n"
                f"Additional context:\n{context}"
            )

        prompt = (
            "You answer questions about the indexed scholarly paper corpus sourced from Crossref.\n"
            "Use the retrieved corpus context below and answer factually.\n"
            "If the corpus does not support the answer, say so clearly.\n\n"
            f"Question: {question}\n\nContext:\n{context}"
        )

        response = self.llm.invoke(prompt)
        answer = getattr(response, "content", str(response))
        return {"messages": [SimpleNamespace(content=str(answer))]}


def build_agent(settings: Settings, index: LocalEmbeddingIndex) -> SimplePaperAgent:
    return SimplePaperAgent(settings=settings, index=index)


def run_agent_question(agent: Any, question: str) -> str:
    result = agent.invoke({"messages": [{"role": "user", "content": question}]})
    messages = result.get("messages", [])
    if not messages:
        return ""
    final_message = messages[-1]
    return getattr(final_message, "content", str(final_message))
