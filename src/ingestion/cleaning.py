from __future__ import annotations

from dataclasses import asdict, fields
from datetime import datetime

import pandas as pd

from ingestion.crossref import PaperRecord
from core.utils import normalize_whitespace


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    """Normalize records and prepare embedding text without modifying the source.

    Skip missing IDs, titles, summaries or invalid publication dates. Missing or
    invalid updated dates fall back to published. Dates are exported as ISO date
    strings; age is measured in UTC (naive run_date is assumed to be UTC).
    Keep the first valid occurrence of each DOI and sort newest publications first.
    Future publication dates retain negative ages for downstream quality checks.
    """
    run_timestamp = pd.Timestamp(run_date)
    if pd.isna(run_timestamp):
        raise ValueError("run_date must be a valid datetime")
    run_timestamp = (
        run_timestamp.tz_localize("UTC") if run_timestamp.tzinfo is None
        else run_timestamp.tz_convert("UTC")
    )
    columns = [field.name for field in fields(PaperRecord)] + [
        "age_days", "authors_joined", "categories_joined", "summary_chars",
        "text_for_embedding",
    ]
    rows = []
    for record in records:
        row = asdict(record)
        for key, value in row.items():
            if isinstance(value, str):
                row[key] = normalize_whitespace(value)
        row["paper_id"] = (row["paper_id"] or "").lower()
        for key in ("authors", "categories"):
            row[key] = [
                cleaned for value in row[key] or []
                if isinstance(value, str) and (cleaned := normalize_whitespace(value))
            ]
        published = pd.to_datetime(row["published"], errors="coerce", utc=True)
        if not all(row[key] for key in ("paper_id", "title", "summary")) or pd.isna(published):
            continue
        updated = pd.to_datetime(row["updated"], errors="coerce", utc=True)
        if pd.isna(updated):
            updated = published
        row["published"] = published.date().isoformat()
        row["updated"] = updated.date().isoformat()
        row["age_days"] = (run_timestamp - published.normalize()).days
        row["authors_joined"] = ", ".join(row["authors"])
        row["categories_joined"] = ", ".join(row["categories"])
        row["summary_chars"] = len(row["summary"])
        row["text_for_embedding"] = (
            f"Title: {row['title']}\n"
            f"Authors: {row['authors_joined']}\n"
            f"Published: {row['published']}\n"
            f"Categories: {row['categories_joined']}\n"
            f"Summary: {row['summary']}"
        )
        rows.append(row)
    df = pd.DataFrame(rows, columns=columns).astype({"age_days": "int64", "summary_chars": "int64"})
    return (
        df.drop_duplicates(subset="paper_id", keep="first")
        .sort_values(["published", "paper_id"], ascending=[False, True])
        .reset_index(drop=True)
    )
