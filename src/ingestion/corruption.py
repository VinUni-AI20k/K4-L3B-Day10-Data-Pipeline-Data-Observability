from __future__ import annotations

from math import ceil
from pathlib import Path

import pandas as pd

from core.utils import write_json


NOISE = "[CORRUPTED] zxqv987 ### @@@ invalid_payload !!!. "
STALE_SHIFT_DAYS = 730


def _refresh_embedding_fields(df: pd.DataFrame) -> None:
    """Keep derived fields consistent with the deliberately damaged metadata."""
    df["summary_chars"] = df["summary"].str.len()
    df["text_for_embedding"] = df.apply(
        lambda row: (
            f"Title: {row['title']}\n"
            f"Authors: {row['authors_joined']}\n"
            f"Published: {row['published']}\n"
            f"Categories: {row['categories_joined']}\n"
            f"Summary: {row['summary']}"
        ), axis=1,
    )


def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path) -> pd.DataFrame:
    """Inject six deterministic failures without modifying the input frame.

    Input is a clean, unique corpus of at least ten papers. Drop ceil(20%) of
    the newest papers; damage separate summary/title cohorts; age 40% of the
    survivors by 730 days; duplicate 10% of survivors with the same paper_id.
    Rates use integer ceiling. All steps include before/after audit evidence.
    """
    text_columns = ("paper_id", "title", "summary", "published", "authors_joined", "categories_joined")
    missing = sorted(set((*text_columns, "age_days")) - set(df.columns))
    if missing:
        raise ValueError(f"Corruption missing required columns: {', '.join(missing)}")
    if len(df) < 10:
        raise ValueError("Corruption suite requires at least 10 clean papers.")
    for column in text_columns:
        if not df[column].map(lambda value: isinstance(value, str) and bool(value.strip())).all():
            raise ValueError(f"Corruption column {column!r} must contain non-empty strings.")
    if df["paper_id"].duplicated().any():
        raise ValueError("Corruption input paper_id values must be unique.")
    if df["title"].str.len().lt(8).any():
        raise ValueError("Corruption input titles must have at least 8 characters.")
    ages = pd.to_numeric(df["age_days"], errors="coerce")
    if ages.isna().any() or not ages.between(0, 1_000_000).all() or (ages % 1 != 0).any():
        raise ValueError("Corruption age_days values must be finite non-negative whole days.")

    damaged = df.copy(deep=True)
    damaged["age_days"] = ages.astype("int64")
    damaged["_published_at"] = pd.to_datetime(damaged["published"], format="ISO8601", utc=True, errors="coerce")
    if damaged["_published_at"].isna().any():
        raise ValueError("Corruption published values must be valid dates.")
    damaged = damaged.sort_values(["_published_at", "paper_id"], ascending=[False, True]).drop(columns="_published_at").reset_index(drop=True)
    events = []

    def record(scenario, before_rows, changes, parameters):
        events.append({
            "scenario": scenario,
            "parameters": parameters,
            "rows_before": before_rows,
            "rows_after": len(damaged),
            "affected_count": len(changes),
            "affected_paper_ids": [change["paper_id"] for change in changes],
            "changes": changes,
        })

    drop_count = ceil(len(damaged) * 0.20)
    dropped = damaged.iloc[:drop_count]
    changes = [
        {"paper_id": row["paper_id"], "before": {"published": row["published"], "present": True}, "after": {"present": False}}
        for row in dropped.to_dict("records")
    ]
    damaged = damaged.iloc[drop_count:].reset_index(drop=True)
    record("drop_latest_records", len(df), changes, {"fraction": 0.20, "rounding": "ceil"})
    survivors = len(damaged)
    cohort_size = ceil(survivors * 0.20)

    def mutate(scenario, positions, columns, transform, parameters):
        changes = []
        for position in positions:
            before = {column: damaged.at[position, column] for column in columns}
            after = transform(before)
            for column, value in after.items():
                damaged.at[position, column] = value
            # Convert numpy scalars to JSON-native values for the audit log.
            before = {key: value.item() if hasattr(value, "item") else value for key, value in before.items()}
            after = {key: value.item() if hasattr(value, "item") else value for key, value in after.items()}
            changes.append({"paper_id": damaged.at[position, "paper_id"], "before": before, "after": after})
        record(scenario, survivors, changes, parameters)

    mutate("blank_summary", range(cohort_size), ["summary"], lambda old: {"summary": ""}, {"fraction_of_survivors": 0.20})
    mutate("inject_noise", range(cohort_size, cohort_size * 2), ["summary"], lambda old: {"summary": NOISE + old["summary"]}, {"prefix": NOISE})
    mutate("truncate_title", range(cohort_size * 2, cohort_size * 3), ["title"], lambda old: {"title": old["title"][:7]}, {"max_characters": 7})

    def age_record(old):
        date = pd.Timestamp(old["published"]) - pd.Timedelta(days=STALE_SHIFT_DAYS)
        published = date.date().isoformat() if len(old["published"]) == 10 else date.isoformat()
        return {"published": published, "age_days": int(old["age_days"]) + STALE_SHIFT_DAYS}

    mutate("stale_date", range(ceil(survivors * 0.40)), ["published", "age_days"], age_record, {"shift_days": STALE_SHIFT_DAYS, "fraction_of_survivors": 0.40})
    _refresh_embedding_fields(damaged)
    duplicate_count = ceil(survivors * 0.10)
    duplicates = damaged.tail(duplicate_count).copy(deep=True)
    damaged = pd.concat([damaged, duplicates], ignore_index=True)
    changes = [
        {"paper_id": paper_id, "before": {"occurrences": 1}, "after": {"occurrences": 2}}
        for paper_id in duplicates["paper_id"]
    ]
    record("duplicate_rows", survivors, changes, {"fraction_of_survivors": 0.10, "preserve_paper_id": True})
    write_json(Path(output_log_path), {
        "schema_version": 1,
        "input_rows": len(df),
        "output_rows": len(damaged),
        "selection": "published descending, paper_id ascending; deterministic, no random sampling",
        "scenarios": events,
    })
    return damaged
