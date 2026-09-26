from __future__ import annotations

from pathlib import Path
from typing import Any
import json

import pandas as pd


def _empty_frame() -> pd.DataFrame:
    return pd.DataFrame()


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"status": "missing", "path": str(path), "data": None, "error": None}
    try:
        with path.open(encoding="utf-8") as handle:
            return {"status": "ok", "path": str(path), "data": json.load(handle), "error": None}
    except (OSError, ValueError, TypeError) as exc:
        return {"status": "invalid", "path": str(path), "data": None, "error": str(exc)}


def read_csv(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"status": "missing", "path": str(path), "data": _empty_frame(), "error": None}
    try:
        return {"status": "ok", "path": str(path), "data": pd.read_csv(path), "error": None}
    except (OSError, ValueError, pd.errors.ParserError) as exc:
        return {"status": "invalid", "path": str(path), "data": _empty_frame(), "error": str(exc)}


def _record_list(result: dict[str, Any]) -> list[dict[str, Any]]:
    data = result.get("data")
    return data if isinstance(data, list) else []


def _dict_result(result: dict[str, Any]) -> dict[str, Any]:
    data = result.get("data")
    return data if isinstance(data, dict) else {}


def _file_artifacts(settings: Any) -> dict[str, dict[str, Any]]:
    paths = settings.paths
    return {
        "raw_response": read_json(paths.raw_api_response),
        "raw_records": read_json(paths.raw_records_json),
        "clean_json": read_json(paths.clean_json),
        "clean_csv": read_csv(paths.clean_csv),
        "embeddings": read_json(paths.embeddings_json),
        "test_set": read_json(paths.eval_testset),
        "baseline_metrics": read_json(paths.baseline_metrics),
        "baseline_answers": read_json(paths.baseline_answers),
        "baseline_quality": read_json(paths.baseline_quality_report),
        "freshness": read_json(paths.freshness_report),
        "phase1_report": {
            "status": "ok" if paths.baseline_report.exists() else "missing",
            "path": str(paths.baseline_report),
            "data": paths.baseline_report.read_text(encoding="utf-8") if paths.baseline_report.exists() else None,
            "error": None,
        },
        "corruption_log": read_json(paths.corruption_log),
        "corrupted_metrics": read_json(paths.corrupted_metrics),
        "corrupted_answers": read_json(paths.corrupted_answers),
        "corrupted_quality": read_json(paths.corrupted_quality_report),
        "corrupted_clean": read_csv(paths.corrupted_clean_csv),
        "repaired_metrics": read_json(paths.repaired_metrics),
        "repaired_answers": read_json(paths.repaired_answers),
        "repaired_clean": read_csv(paths.repaired_clean_csv),
        "comparison_report": {
            "status": "ok" if paths.comparison_report.exists() else "missing",
            "path": str(paths.comparison_report),
            "data": paths.comparison_report.read_text(encoding="utf-8") if paths.comparison_report.exists() else None,
            "error": None,
        },
    }


def _pipeline_steps(settings: Any, artifacts: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    paths = settings.paths

    def state(ok: bool, evidence: str, command: str) -> dict[str, Any]:
        return {"status": "PASS" if ok else "NOT RUN", "evidence": evidence, "command": command}

    raw_ok = all(artifacts[key]["status"] == "ok" for key in ("raw_response", "raw_records"))
    clean_ok = artifacts["clean_csv"]["status"] == "ok" and not artifacts["clean_csv"]["data"].empty
    quality_data = _dict_result(artifacts["baseline_quality"])
    quality_ok = artifacts["baseline_quality"]["status"] == "ok" and isinstance(quality_data.get("success"), bool)
    index_ok = artifacts["embeddings"]["status"] == "ok" and paths.chroma_dir.exists() and any(paths.chroma_dir.rglob("*"))
    evaluation_ok = artifacts["baseline_metrics"]["status"] == "ok" and bool(_dict_result(artifacts["baseline_metrics"]))
    corruption_ok = all(artifacts[key]["status"] == "ok" for key in ("corruption_log", "corrupted_metrics"))
    repair_ok = all(artifacts[key]["status"] == "ok" for key in ("repaired_metrics", "comparison_report"))
    return [
        {"step": "Ingestion", **state(raw_ok, "raw/crossref_response.json + raw/crossref_records.json", "python script/run_phase1.py")},
        {"step": "Cleaning", **state(clean_ok, "clean/papers_clean.csv", "python script/run_phase1.py")},
        {"step": "Quality gate", **state(quality_ok, "quality/baseline_quality_report.json", "python script/run_phase1.py")},
        {"step": "Embedding / indexing", **state(index_ok, "embeddings/papers_embeddings.json + data/chroma/", "python script/run_phase1.py")},
        {"step": "Evaluation", **state(evaluation_ok, "results/baseline_metrics.json", "python script/run_phase1.py")},
        {"step": "Corruption", **state(corruption_ok, "results/corruption_log.json + corrupted_metrics.json", "python script/run_corruption_flow.py")},
        {"step": "Repair", **state(repair_ok, "results/repaired_metrics.json + reports/corruption_report.md", "python script/run_corruption_flow.py")},
    ]


def _clean_frame(artifacts: dict[str, dict[str, Any]]) -> pd.DataFrame:
    csv_data = artifacts["clean_csv"].get("data")
    return csv_data.copy() if isinstance(csv_data, pd.DataFrame) else _empty_frame()


def load_dashboard_data(settings: Any) -> dict[str, Any]:
    """Read local artifacts only and normalize them for the dashboard."""
    artifacts = _file_artifacts(settings)
    clean_df = _clean_frame(artifacts)
    freshness = _dict_result(artifacts["freshness"])
    quality = _dict_result(artifacts["baseline_quality"])
    mtimes = []
    for result in artifacts.values():
        path = Path(result["path"])
        if result["status"] == "ok" and path.exists():
            mtimes.append(path.stat().st_mtime)
    latest_mtime = max(mtimes) if mtimes else None
    return {
        "artifacts": artifacts,
        "clean_df": clean_df,
        "raw_records": _record_list(artifacts["raw_records"]),
        "quality": quality,
        "freshness": freshness,
        "pipeline_steps": _pipeline_steps(settings, artifacts),
        "latest_mtime": latest_mtime,
    }


def numeric_metrics(metrics: dict[str, Any]) -> dict[str, float]:
    return {
        key: float(value)
        for key, value in metrics.items()
        if isinstance(value, (int, float)) and not isinstance(value, bool)
    }


def comparison_frame(data: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for label, artifact_key in (("Baseline", "baseline_metrics"), ("Corrupted", "corrupted_metrics"), ("Repaired", "repaired_metrics")):
        result = data["artifacts"][artifact_key]
        for metric, value in numeric_metrics(_dict_result(result)).items():
            rows.append({"state": label, "metric": metric, "value": value})
    return pd.DataFrame(rows, columns=["state", "metric", "value"])
