from importlib import import_module

from .testset import build_test_set

__all__ = ["EvaluationBundle", "JudgeVerdict", "evaluate_pipeline", "build_test_set"]


def __getattr__(name):
    if name in {"EvaluationBundle", "JudgeVerdict", "evaluate_pipeline"}:
        return getattr(import_module(".metrics", __name__), name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
