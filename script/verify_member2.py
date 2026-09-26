"""Verify member 2 independently, or consume the team's actual clean JSON.

Snapshot fixture mode is explicit: it is NOT the production cleaning pipeline,
GX validation, embedding evaluation, or a measurement of retrieval quality.
"""
from __future__ import annotations

import argparse
from collections import Counter
from hashlib import sha256
from pathlib import Path
import sys

import pandas as pd
from pandas.testing import assert_frame_equal

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from core.utils import read_json, write_json
from evaluation.testset import build_test_set
from ingestion.corruption import NOISE, corrupt_clean_dataframe


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--snapshot-fixture", action="store_true")
    source.add_argument("--clean-json", type=Path, default=ROOT / "data/clean/papers_clean.json")
    parser.add_argument("--run-date", default="2026-09-26", help="Reference date for snapshot fixture age_days")
    args = parser.parse_args()
    if args.snapshot_fixture:
        source_path = ROOT / "data/raw/crossref_records.json"
        df = pd.DataFrame(read_json(source_path))
        # The bundled parsed snapshot is already plain text. This adapter only
        # supplies clean-schema helpers so the assigned modules can be tested.
        df["authors_joined"] = df["authors"].map(lambda items: ", ".join(items))
        df["categories_joined"] = df["categories"].map(lambda items: ", ".join(items))
        df["age_days"] = (pd.Timestamp(args.run_date, tz="UTC") - pd.to_datetime(df["published"], utc=True)).dt.days
        df["summary_chars"] = df["summary"].str.len()
        df["text_for_embedding"] = df.apply(lambda row: f"Title: {row['title']}\nAuthors: {row['authors_joined']}\nPublished: {row['published']}\nCategories: {row['categories_joined']}\nSummary: {row['summary']}", axis=1)
        write_json(ROOT / "data/eval/member2_snapshot_fixture.json", df.to_dict("records"))
        corrupted_path = ROOT / "data/eval/member2_corrupted_fixture.json"
    else:
        source_path = args.clean_json.resolve()
        if not source_path.is_file():
            parser.error("Clean JSON is missing. Supply --clean-json or explicitly use --snapshot-fixture.")
        df = pd.DataFrame(read_json(source_path))
        corrupted_path = ROOT / "data/clean/papers_clean_corrupted.json"

    original = df.copy(deep=True)
    testset_path = ROOT / "data/eval/test_set.json"
    log_path = ROOT / "data/results/corruption_log.json"
    benchmark = build_test_set(df, testset_path)
    benchmark_hash = sha256(testset_path.read_bytes()).hexdigest()
    corrupted = corrupt_clean_dataframe(df, log_path)
    assert_frame_equal(df, original)
    if sha256(testset_path.read_bytes()).hexdigest() != benchmark_hash:
        raise AssertionError("Corruption changed the benchmark.")
    log = read_json(log_path)
    if len(benchmark) != 10 or len(log["scenarios"]) != 6:
        raise AssertionError("Expected ten questions and six corruption scenarios.")
    write_json(corrupted_path, corrupted.to_dict("records"))

    def signals(frame):
        return {
            "rows": len(frame),
            "unique_papers": int(frame["paper_id"].nunique()),
            "blank_summaries": int(frame["summary"].eq("").sum()),
            "noisy_summaries": int(frame["summary"].str.startswith(NOISE).sum()),
            "short_titles": int(frame["title"].str.len().lt(8).sum()),
            "duplicate_rows_by_paper_id": int(frame["paper_id"].duplicated().sum()),
            "stale_rows_over_180_days": int(frame["age_days"].gt(180).sum()),
            "stale_fraction": float(frame["age_days"].gt(180).mean()),
        }

    surviving_ids = set(corrupted["paper_id"])
    validation = {
        "status": "passed",
        "scope": "member2 module verification; not end-to-end RAG or GX validation",
        "input_mode": "snapshot_fixture" if args.snapshot_fixture else "team_clean_json",
        "source_file": source_path.name,
        "source_sha256": sha256(source_path.read_bytes()).hexdigest(),
        "fixture_run_date": args.run_date if args.snapshot_fixture else None,
        "benchmark_sha256": benchmark_hash,
        "benchmark_questions": len(benchmark),
        "question_types": dict(Counter(item["question_type"] for item in benchmark)),
        "input_unchanged": True,
        "benchmark_unchanged_by_corruption": True,
        "scenarios": {event["scenario"]: event["affected_count"] for event in log["scenarios"]},
        "baseline_data_signals": signals(df),
        "corrupted_data_signals": signals(corrupted),
        "benchmark_questions_with_removed_document": sum(not any(doc_id in surviving_ids for doc_id in item["ground_truth_doc_ids"]) for item in benchmark),
        "rag_metrics": "not measured; pipeline, cleaning and quality modules are separate team deliverables",
    }
    write_json(ROOT / "data/results/member2_validation.json", validation)
    print(f"PASS: {len(benchmark)} benchmark questions; {len(log['scenarios'])} corruption scenarios; {len(df)} -> {len(corrupted)} rows.")
    print(f"Input mode: {validation['input_mode']}; evidence: data/results/member2_validation.json")


if __name__ == "__main__":
    main()
