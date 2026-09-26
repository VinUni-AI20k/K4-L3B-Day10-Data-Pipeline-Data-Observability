from importlib import import_module

__all__ = [
    "build_agent", "run_agent_question", "MiniLMEmbeddings", "LocalEmbeddingIndex",
    "SearchResult", "build_llm", "AnswerResult", "answer_question",
]


def __getattr__(name):
    modules = {
        "build_agent": ".agent",
        "run_agent_question": ".agent",
        "MiniLMEmbeddings": ".embeddings",
        "LocalEmbeddingIndex": ".index",
        "SearchResult": ".index",
        "build_llm": ".llm",
        "AnswerResult": ".qa",
        "answer_question": ".qa",
    }
    if name not in modules:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    return getattr(import_module(modules[name], __name__), name)
