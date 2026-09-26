"""Expose benchmark creation without eagerly loading the RAG/model stack."""

from .testset import build_test_set

__all__ = ["build_test_set", "EvaluationBundle", "JudgeVerdict", "evaluate_pipeline"]


def __getattr__(name):
    if name in {"EvaluationBundle", "JudgeVerdict", "evaluate_pipeline"}:
        from . import metrics

        value = getattr(metrics, name)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
