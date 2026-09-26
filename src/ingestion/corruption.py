from __future__ import annotations

from datetime import UTC, datetime
import math

import pandas as pd

from core.utils import normalize_whitespace, write_json


def _clean_text(value: object) -> str:
    return "" if pd.isna(value) else normalize_whitespace(str(value))


def _rebuild_text(row: pd.Series) -> str:
    return (
        f"Title: {_clean_text(row.get('title', ''))}\n"
        f"Authors: {_clean_text(row.get('authors_joined', ''))}\n"
        f"Published: {_clean_text(row.get('published', ''))}\n"
        f"Categories: {_clean_text(row.get('categories_joined', ''))}\n"
        f"Summary: {_clean_text(row.get('summary', ''))}"
    )


def _refresh_derived_columns(dataframe: pd.DataFrame) -> pd.DataFrame:
    result = dataframe.copy()
    result["summary"] = result["summary"].map(_clean_text)
    result["title"] = result["title"].map(_clean_text)
    result["published"] = pd.to_datetime(result["published"], errors="coerce").dt.date.astype("string")
    run_day = datetime.now(UTC).date()
    result["age_days"] = (pd.to_datetime(result["published"], errors="coerce").dt.date - run_day).map(
        lambda value: -value.days if pd.notna(value) else None
    )
    result["summary_chars"] = result["summary"].str.len()
    result["text_for_embedding"] = result.apply(_rebuild_text, axis=1)
    return result


def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path) -> pd.DataFrame:
    """Apply six deterministic corruption scenarios and persist an audit log."""
    if df.empty:
        raise ValueError("Cannot corrupt an empty clean dataframe.")
    required = {"paper_id", "title", "summary", "published", "text_for_embedding"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Clean dataframe is missing columns: {sorted(missing)}")

    corrupted = df.copy().reset_index(drop=True)
    events: list[dict[str, object]] = []

    published = pd.to_datetime(corrupted["published"], errors="coerce")
    drop_count = max(1, math.ceil(len(corrupted) * 0.20))
    latest_indexes = published.sort_values(ascending=False).index[:drop_count].tolist()
    dropped_ids = corrupted.loc[latest_indexes, "paper_id"].astype(str).tolist()
    corrupted = corrupted.drop(index=latest_indexes).reset_index(drop=True)
    events.append({"type": "drop_latest_records", "affected_rows": drop_count, "paper_ids": dropped_ids})

    if not corrupted.empty:
        corrupted.loc[0, "summary"] = ""
        events.append({"type": "blank_summary", "affected_rows": 1, "paper_ids": [str(corrupted.loc[0, "paper_id"])]})
    if len(corrupted) > 1:
        corrupted.loc[1, "summary"] = f"{corrupted.loc[1, 'summary']} !!! noise_@@@ ###"
        events.append({"type": "inject_noise", "affected_rows": 1, "paper_ids": [str(corrupted.loc[1, "paper_id"])]})
    if len(corrupted) > 2:
        original_title = str(corrupted.loc[2, "title"])
        corrupted.loc[2, "title"] = original_title[:7]
        events.append({"type": "truncate_title", "affected_rows": 1, "paper_ids": [str(corrupted.loc[2, "paper_id"])]})
    if len(corrupted) > 3:
        corrupted.loc[3, "published"] = "2000-01-01"
        events.append({"type": "stale_date", "affected_rows": 1, "paper_ids": [str(corrupted.loc[3, "paper_id"])]})
    if not corrupted.empty:
        duplicate = corrupted.iloc[[0]].copy()
        corrupted = pd.concat([corrupted, duplicate], ignore_index=True)
        events.append({"type": "duplicate_rows", "affected_rows": 1, "paper_ids": [str(duplicate.iloc[0]["paper_id"])]})

    corrupted = _refresh_derived_columns(corrupted)
    write_json(output_log_path, {"scenarios": events, "total_scenarios": len(events), "input_rows": len(df), "output_rows": len(corrupted)})
    return corrupted
