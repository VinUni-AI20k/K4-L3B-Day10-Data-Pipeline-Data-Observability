from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, time, timedelta
from math import ceil

import pandas as pd

from core.config import load_settings, normalized_provider
from core.utils import read_json, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from ingestion.cleaning import build_clean_dataframe
from ingestion.corruption import corrupt_clean_dataframe
from ingestion.crossref import load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_corruption_report
from retrieval.index import LocalEmbeddingIndex
from retrieval.qa import answer_question


def main() -> None:
    """Compare corrupted and repaired data against the saved offline baseline."""
    settings = load_settings()
    if normalized_provider(settings) != "mock":
        raise RuntimeError("Set LLM_PROVIDER=mock for the offline comparison run.")
    paths = settings.paths
    comparison_chroma_dir = paths.chroma_dir / "comparison"
    corrupted_freshness_path = paths.quality_dir / "corrupted_freshness_report.json"
    repaired_freshness_path = paths.quality_dir / "repaired_freshness_report.json"
    repaired_quality_path = paths.quality_dir / "repaired_quality_report.json"

    outputs = (
        paths.corruption_log,
        paths.corrupted_clean_csv, paths.corrupted_clean_json,
        paths.repaired_clean_csv, paths.repaired_clean_json,
        paths.corrupted_embeddings_json, paths.repaired_embeddings_json,
        paths.corrupted_quality_report, repaired_quality_path,
        corrupted_freshness_path, repaired_freshness_path,
        paths.corrupted_metrics, paths.corrupted_answers,
        paths.repaired_metrics, paths.repaired_answers,
        paths.comparison_report,
    )
    existing = [str(path) for path in outputs if path.exists()]
    if comparison_chroma_dir.exists():
        existing.append(str(comparison_chroma_dir))
    if existing:
        raise FileExistsError("Comparison would replace existing data: " + ", ".join(existing))

    inputs = (
        paths.raw_records_json, paths.clean_json, paths.eval_testset,
        paths.baseline_metrics, paths.baseline_answers,
        paths.baseline_quality_report, paths.freshness_report,
    )
    missing = [str(path) for path in inputs if not path.is_file()]
    if missing:
        raise FileNotFoundError("Missing baseline inputs: " + ", ".join(missing))

    baseline_rows = read_json(paths.clean_json)
    baseline_df = pd.DataFrame(baseline_rows)
    test_set = read_json(paths.eval_testset)
    baseline_answers = read_json(paths.baseline_answers)
    baseline_metrics = read_json(paths.baseline_metrics)
    baseline_quality = read_json(paths.baseline_quality_report)
    baseline_freshness = read_json(paths.freshness_report)
    if not baseline_rows or not test_set or len(test_set) != baseline_metrics["samples"]:
        raise ValueError("Baseline papers, test set, and evaluated sample count do not agree")
    if len(test_set) != len(baseline_answers) or any(
        item["id"] != answer["id"]
        or item["question"] != answer["question"]
        or item["ground_truth"] != answer["ground_truth"]
        or item["ground_truth_doc_ids"] != answer["ground_truth_doc_ids"]
        for item, answer in zip(test_set, baseline_answers, strict=True)
    ):
        raise ValueError("Saved baseline answers were not evaluated with the current test set")

    run_days = {
        datetime.fromisoformat(row["published"]).date() + timedelta(days=int(row["age_days"]))
        for row in baseline_rows
    }
    if len(run_days) != 1:
        raise ValueError("Baseline age_days values do not imply one cleaning run date")
    baseline_run_date = datetime.combine(run_days.pop(), time.min, tzinfo=UTC)

    corrupted_df = corrupt_clean_dataframe(baseline_df)
    corruption_log = corrupted_df.attrs["corruption_log"]
    expected_types = {
        "drop_latest", "blank_summary", "inject_noise",
        "truncate_title", "stale_date", "duplicate_doi",
    }
    if {event["type"] for event in corruption_log["events"]} != expected_types:
        raise RuntimeError("The corruption log does not contain all six scenarios")
    if len(corrupted_df) != len(baseline_df) - ceil(len(baseline_df) * 0.20) + 1:
        raise RuntimeError("Corrupted row count is inconsistent with drop and duplicate events")

    raw_records = load_raw_records(paths.raw_records_json)
    repaired_df = build_clean_dataframe(raw_records, baseline_run_date)
    repaired_again = build_clean_dataframe(raw_records, baseline_run_date)
    if repaired_df.to_dict(orient="records") != baseline_rows:
        raise RuntimeError("Repaired content differs from the saved clean baseline")
    if repaired_again.to_dict(orient="records") != repaired_df.to_dict(orient="records"):
        raise RuntimeError("Repair is not deterministic")

    comparison_settings = replace(
        settings, paths=replace(paths, chroma_dir=comparison_chroma_dir)
    )
    write_json(paths.corruption_log, corruption_log)
    write_csv(corrupted_df, paths.corrupted_clean_csv)
    write_json(paths.corrupted_clean_json, corrupted_df.to_dict(orient="records"))
    corrupted_quality = run_data_quality_checks(corrupted_df, settings, report_name=None)
    corrupted_freshness = build_freshness_report(corrupted_df, settings, report_path=None)
    write_json(paths.corrupted_quality_report, corrupted_quality)
    write_json(corrupted_freshness_path, corrupted_freshness)
    corrupted_index = LocalEmbeddingIndex.build(
        corrupted_df, comparison_settings, paths.corrupted_embeddings_json
    )
    if corrupted_index.collection.count() != len(corrupted_df):
        raise RuntimeError("Corrupted collection count does not match its dataframe")
    corrupted_evaluation = evaluate_pipeline(
        settings=comparison_settings, index=corrupted_index,
        test_set_path=paths.eval_testset,
        metrics_output_path=paths.corrupted_metrics,
        answers_output_path=paths.corrupted_answers,
    )

    write_csv(repaired_df, paths.repaired_clean_csv)
    write_json(paths.repaired_clean_json, repaired_df.to_dict(orient="records"))
    repaired_quality = run_data_quality_checks(repaired_df, settings, report_name=None)
    repaired_freshness = build_freshness_report(repaired_df, settings, report_path=None)
    write_json(repaired_quality_path, repaired_quality)
    write_json(repaired_freshness_path, repaired_freshness)
    repaired_index = LocalEmbeddingIndex.build(
        repaired_df, comparison_settings, paths.repaired_embeddings_json
    )
    if repaired_index.collection.count() != len(repaired_df):
        raise RuntimeError("Repaired collection count does not match its dataframe")
    repaired_evaluation = evaluate_pipeline(
        settings=comparison_settings, index=repaired_index,
        test_set_path=paths.eval_testset,
        metrics_output_path=paths.repaired_metrics,
        answers_output_path=paths.repaired_answers,
    )
    for saved in repaired_evaluation.answers:
        repeated = answer_question(saved["question"], settings=comparison_settings, index=repaired_index)
        if repeated.answer != saved["answer"] or repeated.retrieved_doc_ids != saved["retrieved_doc_ids"]:
            raise RuntimeError("Repeated repaired retrieval or answer differed")

    benchmark = {
        "test_set_path": str(paths.eval_testset),
        "question_count": len(test_set),
        "quoted_doi_questions": sum(
            any(f"'{paper_id}'" in item["question"] for paper_id in item["ground_truth_doc_ids"])
            for item in test_set
        ),
    }
    generate_corruption_report(
        report_path=paths.comparison_report,
        baseline_metrics=baseline_metrics,
        corrupted_metrics=corrupted_evaluation.summary,
        repaired_metrics=repaired_evaluation.summary,
        baseline_quality=baseline_quality,
        corrupted_quality=corrupted_quality,
        repaired_quality=repaired_quality,
        baseline_freshness=baseline_freshness,
        corrupted_freshness=corrupted_freshness,
        repaired_freshness=repaired_freshness,
        benchmark=benchmark,
    )
    print(f"Corruption events: {len(corruption_log['events'])}")
    print(f"Collections: {corrupted_index.collection_name}={len(corrupted_df)}, "
          f"{repaired_index.collection_name}={len(repaired_df)}")
    print(f"Baseline metrics: {baseline_metrics}")
    print(f"Corrupted metrics: {corrupted_evaluation.summary}")
    print(f"Repaired metrics: {repaired_evaluation.summary}")
    print(f"Comparison report: {paths.comparison_report}")
