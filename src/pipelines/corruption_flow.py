from __future__ import annotations

from datetime import UTC, datetime, time, timedelta
from math import ceil

import pandas as pd

from core.config import Settings, normalized_provider
from core.utils import read_json, write_csv, write_json
from evaluation.metrics import evaluate_pipeline, evaluate_abstention_challenges
from evaluation.testset import validate_test_set
from ingestion.cleaning import build_clean_dataframe
from ingestion.corruption import corrupt_clean_dataframe
from ingestion.crossref import load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_corruption_report
from pipelines.runs import RunStore, cli_run, digest
from retrieval.index import LocalEmbeddingIndex
from retrieval.qa import answer_question


def run_corruption_pipeline(settings: Settings, baseline_settings: Settings) -> dict:
    """Measure corruption and repair into a fresh, isolated attempt."""
    if normalized_provider(settings) != "mock":
        raise ValueError("Use the mock provider for the reproducible offline comparison")
    paths, baseline_paths = settings.paths, baseline_settings.paths
    if paths.corruption_log.exists() or paths.comparison_report.exists():
        raise FileExistsError("Comparison output already exists; use the managed CLI")
    baseline_rows = read_json(baseline_paths.clean_json)
    baseline_df = pd.DataFrame(baseline_rows)
    test_set = read_json(baseline_paths.eval_testset)
    validate_test_set(test_set, baseline_df)
    baseline_answers = read_json(baseline_paths.baseline_answers)
    baseline_metrics = read_json(baseline_paths.baseline_metrics)
    baseline_quality = read_json(baseline_paths.baseline_quality_report)
    baseline_freshness = read_json(baseline_paths.freshness_report)
    if not baseline_quality["success"] or not baseline_freshness["is_fresh"]:
        raise RuntimeError("The saved baseline did not pass quality/freshness")
    if baseline_metrics["samples"] != len(test_set) or len(baseline_answers) != len(test_set):
        raise ValueError("Baseline sample counts disagree")
    if any(any(item[key] != answer[key] for key in (
            "id", "question_type", "question", "ground_truth", "ground_truth_doc_ids"))
           for item, answer in zip(test_set, baseline_answers, strict=True)):
        raise ValueError("Baseline answers do not belong to the frozen benchmark")
    run_days = {datetime.fromisoformat(row["published"]).date() + timedelta(days=int(row["age_days"]))
                for row in baseline_rows}
    if len(run_days) != 1:
        raise ValueError("Baseline ages imply inconsistent run dates")
    run_at = datetime.combine(run_days.pop(), time.min, tzinfo=UTC)
    write_json(paths.eval_testset, test_set)

    print("[1/4] Inject six deterministic corruptions", flush=True)
    corrupted_df = corrupt_clean_dataframe(baseline_df)
    log = corrupted_df.attrs["corruption_log"]
    expected = {"drop_latest", "blank_summary", "inject_noise", "truncate_title", "stale_date", "duplicate_doi"}
    if {event["type"] for event in log["events"]} != expected:
        raise RuntimeError("Corruption did not apply all six scenarios")
    if len(corrupted_df) != len(baseline_df) - ceil(len(baseline_df) * .20) + 1:
        raise RuntimeError("Unexpected corrupted row count")
    write_json(paths.corruption_log, log)
    corrupted_quality = run_data_quality_checks(corrupted_df, settings, report_name="corrupted")
    corrupted_freshness = build_freshness_report(
        corrupted_df, settings, paths.quality_dir / "corrupted_freshness_report.json")
    if corrupted_quality["success"]:
        raise RuntimeError("No quality alert detected; refusing to claim an automatic repair")
    write_csv(corrupted_df, paths.corrupted_clean_csv)
    write_json(paths.corrupted_clean_json, corrupted_df.to_dict(orient="records"))
    print("[2/4] Evaluate corrupted corpus in its own collection", flush=True)
    corrupted_index = LocalEmbeddingIndex.build(corrupted_df, settings, paths.corrupted_embeddings_json)
    try:
        corrupted_evaluation = evaluate_pipeline(
            settings, corrupted_index, paths.eval_testset, paths.corrupted_metrics, paths.corrupted_answers)
        dropped = next(e["paper_ids"] for e in log["events"] if e["type"] == "drop_latest")
        evaluate_abstention_challenges(
            settings, corrupted_index, paths.corrupted_answers.with_name("corrupted_challenges.json"),
            extra_questions=[f"Who authored the paper '{doi}'?" for doi in dropped])
    finally:
        corrupted_index.close()

    print("[3/4] Quality alert triggers repair from immutable raw", flush=True)
    raw = load_raw_records(paths.raw_records_json)
    repaired_df = build_clean_dataframe(raw, run_at)
    if repaired_df.to_dict(orient="records") != baseline_rows:
        raise RuntimeError("Repaired content differs from baseline")
    if build_clean_dataframe(raw, run_at).to_dict(orient="records") != baseline_rows:
        raise RuntimeError("Repeated repair differs")
    repaired_quality = run_data_quality_checks(repaired_df, settings, report_name="repaired")
    repaired_freshness = build_freshness_report(
        repaired_df, settings, paths.quality_dir / "repaired_freshness_report.json")
    if not repaired_quality["success"] or not repaired_freshness["is_fresh"]:
        raise RuntimeError("Repaired quality gate failed; no repaired index was published")
    write_csv(repaired_df, paths.repaired_clean_csv)
    write_json(paths.repaired_clean_json, repaired_df.to_dict(orient="records"))
    repaired_index = LocalEmbeddingIndex.build(repaired_df, settings, paths.repaired_embeddings_json)
    try:
        repaired_evaluation = evaluate_pipeline(
            settings, repaired_index, paths.eval_testset, paths.repaired_metrics, paths.repaired_answers)
        for saved in repaired_evaluation.answers:
            repeated = answer_question(saved["question"], settings, repaired_index)
            if repeated.answer != saved["answer"] or repeated.retrieved_doc_ids != saved["retrieved_doc_ids"]:
                raise RuntimeError("Repeated repaired query differs")
        evaluate_abstention_challenges(
            settings, repaired_index, paths.repaired_answers.with_name("repaired_challenges.json"))
    finally:
        repaired_index.close()
    if repaired_evaluation.summary != baseline_metrics:
        raise RuntimeError("Repaired metrics did not recover the same offline baseline")
    benchmark = {
        "test_set_path": "../eval/test_set.json", "question_count": len(test_set),
        "test_set_sha256": digest(paths.eval_testset),
        "quoted_doi_questions": sum(any(f"'{doi}'" in q["question"] for doi in q["ground_truth_doc_ids"])
                                    for q in test_set),
    }
    print("[4/4] Generate measured three-state report", flush=True)
    generate_corruption_report(
        paths.comparison_report, baseline_metrics, corrupted_evaluation.summary, repaired_evaluation.summary,
        baseline_quality, corrupted_quality, repaired_quality,
        baseline_freshness, corrupted_freshness, repaired_freshness, benchmark,
    )
    return {
        "baseline": baseline_metrics, "corrupted": corrupted_evaluation.summary,
        "repaired": repaired_evaluation.summary, "test_set_sha256": benchmark["test_set_sha256"],
        "repair_trigger": "corrupted_quality_failed", "repair_content_equal": True,
        "quality": {"baseline": baseline_quality["success"], "corrupted": corrupted_quality["success"],
                    "repaired": repaired_quality["success"]},
    }


def main() -> None:
    settings, root = cli_run("Measure corruption and repair, or reuse a verified comparison")
    with RunStore(settings, root).locked() as run:
        baseline = run.completed_settings("baseline")
        result = run.execute("comparison", lambda output: run_corruption_pipeline(output, baseline))
        for state in ("baseline", "corrupted", "repaired"):
            print(f"{state}: {result[state]}")
        print(f"Run manifest: {run.path}")
