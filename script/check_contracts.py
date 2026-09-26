"""Validate pipeline artifacts against the team contracts in docs/rules/C*.md.

Usage: python script/check_contracts.py <kind> [path]
kinds: raw, clean, testset, quality, freshness, corruption_log, metrics, fixtures
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
FIXTURES = ROOT / "docs" / "rules" / "fixtures"

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
RAW_FIELDS = [
    "paper_id", "title", "summary", "authors", "categories", "primary_category",
    "published", "updated", "abs_url", "pdf_url", "comment",
]
CLEAN_COLUMNS = RAW_FIELDS + [
    "age_days", "authors_joined", "categories_joined", "summary_chars", "text_for_embedding",
]
QUESTION_TYPES = {"summary", "authors", "date", "categories"}
CHECK_IDS = [
    "row_count", "paper_id_not_null", "title_not_null", "summary_not_null", "paper_id_unique",
    "title_length", "summary_length", "summary_no_noise", "freshness_sla",
]
SCENARIOS = [
    "drop_latest_records", "blank_summary", "inject_noise",
    "truncate_title", "stale_date", "duplicate_rows",
]
METRIC_KEYS = ["samples", "retrieval_hit_rate", "mean_token_f1", "judge_accuracy", "mean_judge_score", "ragas"]
FRESHNESS_KEYS = [
    "latest_published", "oldest_published", "stale_rows", "total_rows",
    "stale_ratio", "threshold_days", "max_stale_ratio", "is_fresh", "generated_at",
]
QUALITY_KEYS = [
    "report_name", "success", "gx_success", "row_count", "passed_checks",
    "failed_checks", "total_checks", "checks", "freshness", "generated_at",
]
CHECK_KEYS = ["id", "expectation", "column", "dimension", "success", "observed_value", "unexpected_count", "threshold"]

DEFAULT_PATHS = {
    "raw": DATA / "raw" / "crossref_records.json",
    "clean": DATA / "clean" / "papers_clean.json",
    "testset": DATA / "eval" / "test_set.json",
    "quality": DATA / "quality" / "baseline_quality_report.json",
    "freshness": DATA / "quality" / "freshness_report.json",
    "corruption_log": DATA / "results" / "corruption_log.json",
    "metrics": DATA / "results" / "baseline_metrics.json",
}


def _missing(obj: dict, keys: list[str], where: str) -> list[str]:
    return [f"{where}: missing key '{key}'" for key in keys if key not in obj]


def _no_none(obj: dict, where: str) -> list[str]:
    return [f"{where}: '{key}' is None/NaN" for key, value in obj.items() if value is None or value != value]


def check_raw(payload) -> list[str]:
    if not isinstance(payload, list) or not payload:
        return ["raw: expected non-empty list"]
    errors: list[str] = []
    for i, rec in enumerate(payload):
        where = f"raw[{i}]"
        errors += _missing(rec, RAW_FIELDS, where)
        if extra := set(rec) - set(RAW_FIELDS):
            errors.append(f"{where}: unexpected keys {sorted(extra)}")
        null_errors = _no_none(rec, where)
        if null_errors:
            errors += null_errors
            continue
        for key in ("paper_id", "title", "summary"):
            if not str(rec.get(key, "")).strip():
                errors.append(f"{where}: '{key}' is empty")
        for key in ("published", "updated"):
            if not DATE_RE.match(str(rec.get(key, ""))):
                errors.append(f"{where}: '{key}' not YYYY-MM-DD")
        for key in ("authors", "categories"):
            if not isinstance(rec.get(key), list):
                errors.append(f"{where}: '{key}' must be list")
    return errors


def check_clean(payload, strict_quality: bool = True) -> list[str]:
    if not isinstance(payload, list) or not payload:
        return ["clean: expected non-empty list of records"]
    errors: list[str] = []
    if list(payload[0].keys()) != CLEAN_COLUMNS:
        errors.append(f"clean: column order must be CLEAN_COLUMNS, got {list(payload[0].keys())}")
    ids = [row.get("paper_id") for row in payload]
    if strict_quality and len(ids) != len(set(ids)):
        errors.append("clean: paper_id not unique")
    for i, row in enumerate(payload):
        where = f"clean[{i}]"
        errors += _missing(row, CLEAN_COLUMNS, where)
        null_errors = _no_none(row, where)
        if null_errors:
            errors += null_errors
            continue
        if not DATE_RE.match(str(row.get("published", ""))):
            errors.append(f"{where}: 'published' not YYYY-MM-DD string")
        if not isinstance(row.get("age_days"), int) or row["age_days"] < 0:
            errors.append(f"{where}: 'age_days' must be int >= 0")
        if row.get("authors_joined") != ", ".join(row.get("authors", [])):
            errors.append(f"{where}: authors_joined != ', '.join(authors)")
        if row.get("categories_joined") != ", ".join(row.get("categories", [])):
            errors.append(f"{where}: categories_joined != ', '.join(categories)")
        if row.get("summary_chars") != len(row.get("summary", "")):
            errors.append(f"{where}: summary_chars != len(summary)")
        expected_text = "\n".join([
            f"Title: {row.get('title')}",
            f"Authors: {row.get('authors_joined')}",
            f"Published: {row.get('published')}",
            f"Categories: {row.get('categories_joined')}",
            f"Summary: {row.get('summary')}",
        ])
        if row.get("text_for_embedding") != expected_text:
            errors.append(f"{where}: text_for_embedding does not match C2 section 3 format")
    return errors


def check_testset(payload) -> list[str]:
    if not isinstance(payload, list) or len(payload) != 10:
        return [f"testset: expected list of 10 items, got {len(payload) if isinstance(payload, list) else type(payload)}"]
    errors: list[str] = []
    counts = {t: 0 for t in QUESTION_TYPES}
    for i, item in enumerate(payload):
        where = f"testset[{i}]"
        keys = ["id", "question_type", "question", "ground_truth", "ground_truth_doc_ids"]
        errors += _missing(item, keys, where)
        if item.get("id") != f"q{i + 1:02d}":
            errors.append(f"{where}: id must be q{i + 1:02d}")
        qtype = item.get("question_type")
        if qtype not in QUESTION_TYPES:
            errors.append(f"{where}: bad question_type {qtype!r}")
        else:
            counts[qtype] += 1
        if not re.search(r"'[^']+'", str(item.get("question", ""))):
            errors.append(f"{where}: question must contain the title in single quotes")
        ids = item.get("ground_truth_doc_ids")
        if not isinstance(ids, list) or len(ids) != 1:
            errors.append(f"{where}: ground_truth_doc_ids must be a 1-element list")
    if counts != {"summary": 3, "authors": 3, "date": 2, "categories": 2}:
        errors.append(f"testset: type distribution must be 3/3/2/2, got {counts}")
    return errors


def check_freshness(payload) -> list[str]:
    errors = _missing(payload, FRESHNESS_KEYS, "freshness")
    if not errors and payload["is_fresh"] != (payload["stale_ratio"] <= payload["max_stale_ratio"]):
        errors.append("freshness: is_fresh inconsistent with stale_ratio")
    return errors


def check_quality(payload) -> list[str]:
    errors = _missing(payload, QUALITY_KEYS, "quality")
    if errors:
        return errors
    ids = [check.get("id") for check in payload["checks"]]
    if ids != CHECK_IDS:
        errors.append(f"quality: checks ids/order must be {CHECK_IDS}, got {ids}")
    for i, check in enumerate(payload["checks"]):
        errors += _missing(check, CHECK_KEYS, f"quality.checks[{i}]")
    passed = sum(1 for check in payload["checks"] if check.get("success"))
    if passed != payload["passed_checks"] or payload["total_checks"] != len(payload["checks"]):
        errors.append("quality: passed/total counts inconsistent with checks[]")
    errors += _missing(payload["freshness"], ["stale_rows", "total_rows", "stale_ratio", "is_fresh"], "quality.freshness")
    if payload["success"] != (payload["gx_success"] and payload["freshness"].get("is_fresh")):
        errors.append("quality: success must equal gx_success and freshness.is_fresh")
    return errors


def check_corruption_log(payload) -> list[str]:
    errors = _missing(payload, ["seed", "input_rows", "output_rows", "generated_at", "scenarios"], "corruption_log")
    if errors:
        return errors
    names = [scenario.get("name") for scenario in payload["scenarios"]]
    if names != SCENARIOS:
        errors.append(f"corruption_log: scenarios must be {SCENARIOS}, got {names}")
    for i, scenario in enumerate(payload["scenarios"]):
        where = f"corruption_log.scenarios[{i}]"
        errors += _missing(scenario, ["name", "description", "params", "affected_rows", "affected_paper_ids"], where)
        if scenario.get("affected_rows") != len(scenario.get("affected_paper_ids", [])):
            errors.append(f"{where}: affected_rows != len(affected_paper_ids)")
    return errors


def check_metrics(payload) -> list[str]:
    errors = _missing(payload, METRIC_KEYS, "metrics")
    if extra := set(payload) - set(METRIC_KEYS):
        errors.append(f"metrics: unexpected keys {sorted(extra)}")
    return errors


CHECKERS = {
    "raw": check_raw,
    "clean": check_clean,
    "testset": check_testset,
    "quality": check_quality,
    "freshness": check_freshness,
    "corruption_log": check_corruption_log,
    "metrics": check_metrics,
}

FIXTURE_FILES = {
    "clean": "clean.sample.json",
    "testset": "test_set.sample.json",
    "quality": "quality.sample.json",
    "freshness": "freshness.sample.json",
    "corruption_log": "corruption_log.sample.json",
    "metrics": "metrics.sample.json",
}


def run(kind: str, path: Path) -> bool:
    if not path.exists():
        print(f"[FAIL] {kind}: file not found: {path}")
        return False
    errors = CHECKERS[kind](json.loads(path.read_text(encoding="utf-8")))
    shown = path.relative_to(ROOT) if path.is_relative_to(ROOT) else path
    if errors:
        print(f"[FAIL] {kind}: {shown}")
        for error in errors[:20]:
            print(f"   - {error}")
        if len(errors) > 20:
            print(f"   ... {len(errors) - 20} more")
        return False
    print(f"[OK]   {kind}: {shown}")
    return True


def main(argv: list[str]) -> int:
    if len(argv) < 2 or argv[1] not in {*CHECKERS, "fixtures"}:
        print(__doc__)
        return 2
    kind = argv[1]
    if kind == "fixtures":
        results = [run(k, FIXTURES / name) for k, name in FIXTURE_FILES.items()]
        return 0 if all(results) else 1
    path = Path(argv[2]) if len(argv) > 2 else DEFAULT_PATHS[kind]
    return 0 if run(kind, path.resolve()) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
