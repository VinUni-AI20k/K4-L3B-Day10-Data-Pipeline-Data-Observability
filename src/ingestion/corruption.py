from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from math import ceil
from pathlib import Path
from typing import Any

import pandas as pd

from core.utils import write_json


_NOISE_MARKER = "<<NOISE::@@##%%>>"


def _is_missing(value: Any) -> bool:
    """Return whether *value* is a scalar missing value."""

    if value is None:
        return True
    if isinstance(value, (list, tuple, set, dict)):
        return False
    missing = pd.isna(value)
    try:
        return bool(missing)
    except (TypeError, ValueError):
        return False


def _as_text(value: Any) -> str:
    if _is_missing(value):
        return ""
    return str(value).strip()


def _join_values(value: Any) -> str:
    if _is_missing(value):
        return ""
    if isinstance(value, (list, tuple, set)):
        return ", ".join(item for item in (_as_text(item) for item in value) if item)
    return _as_text(value)


def _date_text(value: Any) -> str:
    """Format a date-like value without discarding an unparseable value."""

    if _is_missing(value):
        return ""
    parsed = pd.to_datetime(value, errors="coerce", utc=True)
    if pd.isna(parsed):
        return _as_text(value)
    return parsed.date().isoformat()


def _infer_run_date(df: pd.DataFrame) -> date:
    """Infer the cleaning run date from the existing ``age_days`` values."""

    if "published" not in df.columns or "age_days" not in df.columns:
        return datetime.now(UTC).date()

    published = pd.to_datetime(df["published"], errors="coerce", utc=True)
    ages = pd.to_numeric(df["age_days"], errors="coerce")
    candidates: list[date] = []
    for published_value, age_value in zip(published, ages, strict=False):
        if pd.isna(published_value) or pd.isna(age_value):
            continue
        candidates.append(published_value.date() + timedelta(days=int(age_value)))
    if not candidates:
        return datetime.now(UTC).date()
    candidates.sort()
    return candidates[len(candidates) // 2]


def _stable_indices(df: pd.DataFrame) -> list[Any]:
    return sorted(
        list(df.index),
        key=lambda index: (_as_text(df.at[index, "paper_id"]).casefold(), str(index)),
    )


def _select_indices(df: pd.DataFrame, count: int, excluded: set[Any]) -> list[Any]:
    if count <= 0:
        return []
    return [index for index in _stable_indices(df) if index not in excluded][:count]


def _affected_ids(df: pd.DataFrame, indices: list[Any]) -> list[str]:
    return [_as_text(df.at[index, "paper_id"]) for index in indices]


def _rebuild_derived_columns(df: pd.DataFrame, run_date: date) -> pd.DataFrame:
    """Recompute fields consumed by quality checks and vector indexing."""

    frame = df.copy(deep=True)
    for column, default in (("authors", []), ("categories", [])):
        if column not in frame.columns:
            frame[column] = [list(default) for _ in range(len(frame))]

    frame["paper_id"] = frame["paper_id"].map(_as_text)
    frame["title"] = frame["title"].map(_as_text)
    frame["summary"] = frame["summary"].map(_as_text)
    frame["published"] = frame["published"].map(_date_text)
    if "updated" in frame.columns:
        frame["updated"] = frame["updated"].map(_date_text)

    frame["authors_joined"] = frame["authors"].map(_join_values)
    frame["categories_joined"] = frame["categories"].map(_join_values)
    frame["summary_chars"] = frame["summary"].map(len)

    published = pd.to_datetime(frame["published"], errors="coerce", utc=True)
    frame["age_days"] = [
        None if pd.isna(value) else int((run_date - value.date()).days)
        for value in published
    ]

    frame["text_for_embedding"] = frame.apply(
        lambda row: "\n".join(
            [
                f"Title: {_as_text(row['title'])}",
                f"Authors: {_as_text(row['authors_joined'])}",
                f"Categories: {_as_text(row['categories_joined'])}",
                f"Published: {_as_text(row['published'])}",
                f"Summary: {_as_text(row['summary'])}",
            ]
        ),
        axis=1,
    )
    return frame


def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path) -> pd.DataFrame:
    """Create a deterministic six-scenario corruption fixture.

    The input dataframe is never mutated. Each scenario is applied to a
    deterministic, mostly disjoint set of records so quality signals can be
    attributed to a specific corruption in the generated log.
    """

    if not isinstance(df, pd.DataFrame):
        raise TypeError("df must be a pandas DataFrame")
    if df.empty:
        raise ValueError("Cannot corrupt an empty dataframe.")
    required_columns = {"paper_id", "title", "summary", "published"}
    missing_columns = sorted(required_columns.difference(df.columns))
    if missing_columns:
        raise ValueError(f"Clean dataframe is missing required columns: {missing_columns}")
    if output_log_path is None:
        raise ValueError("output_log_path is required")

    run_date = _infer_run_date(df)
    original = df.copy(deep=True).reset_index(drop=True)
    corrupted = original.copy(deep=True)
    scenarios: list[dict[str, Any]] = []

    # 1. Remove the newest fifth of the corpus. ``ceil`` guarantees that a
    # small but non-empty fixture still demonstrates this failure mode.
    drop_count = min(max(1, ceil(len(corrupted) * 0.20)), max(0, len(corrupted) - 1))
    published_dates = pd.to_datetime(corrupted["published"], errors="coerce", utc=True)
    drop_indices = list(
        published_dates.sort_values(ascending=False, na_position="last").index[:drop_count]
    )
    dropped_ids = _affected_ids(corrupted, drop_indices)
    corrupted = corrupted.drop(index=drop_indices).reset_index(drop=True)
    scenarios.append(
        {
            "name": "drop_latest_records",
            "affected_count": len(dropped_ids),
            "affected_paper_ids": dropped_ids,
            "parameters": {"fraction": 0.20, "selection": "latest published records"},
        }
    )

    # The remaining mutations are selected without replacement where the
    # dataset is large enough, making each of the six effects visible.
    scenario_count = max(1, ceil(len(corrupted) * 0.10))
    reserved: set[Any] = set()

    # 2. Blank summaries: a completeness failure.
    blank_indices = _select_indices(corrupted, scenario_count, reserved)
    reserved.update(blank_indices)
    for index in blank_indices:
        corrupted.at[index, "summary"] = ""
    scenarios.append(
        {
            "name": "blank_summary",
            "affected_count": len(blank_indices),
            "affected_paper_ids": _affected_ids(corrupted, blank_indices),
            "parameters": {"fraction_of_remaining": 0.10, "replacement": ""},
        }
    )

    # 3. Inject non-semantic noise into summaries. The marker remains in the
    # embedding text after rebuilding so the retrieval impact is observable.
    noise_indices = _select_indices(corrupted, scenario_count, reserved)
    reserved.update(noise_indices)
    for index in noise_indices:
        summary = _as_text(corrupted.at[index, "summary"])
        corrupted.at[index, "summary"] = f"{summary} {_NOISE_MARKER}".strip()
    scenarios.append(
        {
            "name": "inject_noise",
            "affected_count": len(noise_indices),
            "affected_paper_ids": _affected_ids(corrupted, noise_indices),
            "parameters": {"fraction_of_remaining": 0.10, "marker": _NOISE_MARKER},
        }
    )

    # 4. Truncate titles to seven characters, below the quality threshold of
    # eight characters stated in the lab checkpoint.
    title_indices = _select_indices(corrupted, scenario_count, reserved)
    reserved.update(title_indices)
    for index in title_indices:
        title = _as_text(corrupted.at[index, "title"])
        corrupted.at[index, "title"] = title[:7] or "???"
    scenarios.append(
        {
            "name": "truncate_title",
            "affected_count": len(title_indices),
            "affected_paper_ids": _affected_ids(corrupted, title_indices),
            "parameters": {"fraction_of_remaining": 0.10, "max_length": 7},
        }
    )

    # 5. Move publication dates exactly 365 days into the past, while leaving
    # the raw source untouched for repair.
    stale_indices = _select_indices(corrupted, scenario_count, reserved)
    reserved.update(stale_indices)
    stale_date = (run_date - timedelta(days=365)).isoformat()
    for index in stale_indices:
        corrupted.at[index, "published"] = stale_date
    scenarios.append(
        {
            "name": "stale_date",
            "affected_count": len(stale_indices),
            "affected_paper_ids": _affected_ids(corrupted, stale_indices),
            "parameters": {
                "fraction_of_remaining": 0.10,
                "days_back": 365,
                "replacement_date": stale_date,
            },
        }
    )

    # 6. Add one exact duplicate row. Keeping the duplicate paper_id is
    # intentional: the uniqueness expectation must detect this corruption.
    duplicate_candidates = _select_indices(corrupted, 1, reserved)
    if not duplicate_candidates:
        duplicate_candidates = _stable_indices(corrupted)[:1]
    duplicate_ids: list[str] = []
    if duplicate_candidates:
        duplicate_index = duplicate_candidates[0]
        duplicate_ids = _affected_ids(corrupted, [duplicate_index])
        duplicate_row = corrupted.loc[[duplicate_index]].copy()
        corrupted = pd.concat([corrupted, duplicate_row], ignore_index=True)
    scenarios.append(
        {
            "name": "duplicate_rows",
            "affected_count": len(duplicate_ids),
            "affected_paper_ids": duplicate_ids,
            "parameters": {"rows_added": len(duplicate_ids), "mode": "exact row copy"},
        }
    )

    corrupted = _rebuild_derived_columns(corrupted.reset_index(drop=True), run_date)
    log_payload = {
        "schema_version": 1,
        "created_at_utc": datetime.now(UTC).isoformat(),
        "input_rows": int(len(original)),
        "output_rows": int(len(corrupted)),
        "unique_output_paper_ids": int(corrupted["paper_id"].nunique(dropna=False)),
        "scenarios": scenarios,
        "scenario_names": [scenario["name"] for scenario in scenarios],
    }
    write_json(Path(output_log_path), log_payload)
    return corrupted
