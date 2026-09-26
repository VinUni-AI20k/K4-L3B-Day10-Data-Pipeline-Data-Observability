from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from html import unescape
import re
from typing import Any

import pandas as pd

from core.utils import normalize_whitespace
from ingestion.crossref import PaperRecord


_OUTPUT_COLUMNS = [
    "paper_id",
    "title",
    "summary",
    "authors",
    "categories",
    "primary_category",
    "published",
    "updated",
    "abs_url",
    "pdf_url",
    "comment",
    "age_days",
    "authors_joined",
    "categories_joined",
    "summary_chars",
    "text_for_embedding",
]


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    """Clean raw Crossref records into an embedding-ready dataframe.

    Invalid records and duplicate DOIs are removed. Date columns are returned
    as ISO date strings so that the dataframe can be written to JSON/CSV and
    used as ChromaDB metadata without additional conversion.
    """
    if not records:
        return pd.DataFrame(columns=_OUTPUT_COLUMNS)

    df = pd.DataFrame(asdict(record) for record in records)

    text_columns = [
        "paper_id",
        "title",
        "summary",
        "primary_category",
        "abs_url",
        "pdf_url",
        "comment",
    ]
    for column in text_columns:
        df[column] = df[column].map(_clean_text)

    df["authors"] = df["authors"].map(_clean_string_list)
    df["categories"] = df["categories"].map(_clean_string_list)
    df["primary_category"] = df.apply(
        lambda row: row["primary_category"]
        or (row["categories"][0] if row["categories"] else ""),
        axis=1,
    )

    published_dates = pd.to_datetime(df["published"], errors="coerce", utc=True)
    updated_dates = pd.to_datetime(df["updated"], errors="coerce", utc=True)
    updated_dates = updated_dates.fillna(published_dates)

    # A useful downstream document needs an identifier, searchable text, and a
    # valid publication date. Crossref may still return incomplete rows despite
    # source-side filters, so enforce those requirements here as well.
    valid_rows = (
        df["paper_id"].ne("")
        & df["title"].ne("")
        & df["summary"].ne("")
        & published_dates.notna()
    )
    df = df.loc[valid_rows].copy()
    published_dates = published_dates.loc[valid_rows]
    updated_dates = updated_dates.loc[valid_rows]

    if df.empty:
        return pd.DataFrame(columns=_OUTPUT_COLUMNS)

    # DOI comparison is case-insensitive. Keep the first occurrence so repeated
    # cleaning runs are deterministic and idempotent.
    df["_paper_id_key"] = df["paper_id"].str.casefold()
    duplicate_rows = df["_paper_id_key"].duplicated(keep="first")
    df = df.loc[~duplicate_rows].copy()
    published_dates = published_dates.loc[df.index]
    updated_dates = updated_dates.loc[df.index]

    run_timestamp = pd.Timestamp(run_date)
    if pd.isna(run_timestamp):
        raise ValueError("run_date must be a valid datetime.")
    if run_timestamp.tzinfo is None:
        run_timestamp = run_timestamp.tz_localize("UTC")
    else:
        run_timestamp = run_timestamp.tz_convert("UTC")

    df["published"] = published_dates.dt.strftime("%Y-%m-%d")
    df["updated"] = updated_dates.dt.strftime("%Y-%m-%d")
    df["age_days"] = (
        run_timestamp.normalize() - published_dates.dt.normalize()
    ).dt.days.astype("int64")
    df["authors_joined"] = df["authors"].map(lambda values: ", ".join(values))
    df["categories_joined"] = df["categories"].map(
        lambda values: ", ".join(values)
    )
    df["summary_chars"] = df["summary"].str.len().astype("int64")
    df["text_for_embedding"] = df.apply(_embedding_text, axis=1)

    df = df.sort_values(
        by=["published", "paper_id"],
        ascending=[False, True],
        kind="stable",
    ).reset_index(drop=True)
    return df[_OUTPUT_COLUMNS]


def _clean_text(value: Any) -> str:
    """Remove markup and normalize whitespace from a scalar value."""
    if value is None or (not isinstance(value, (list, dict)) and pd.isna(value)):
        return ""
    text = value if isinstance(value, str) else str(value)
    text = re.sub(r"<[^>]*>", " ", text)
    return normalize_whitespace(unescape(text))


def _clean_string_list(value: Any) -> list[str]:
    values = value if isinstance(value, (list, tuple, set)) else [value]
    cleaned: list[str] = []
    seen: set[str] = set()
    for item in values:
        text = _clean_text(item)
        key = text.casefold()
        if text and key not in seen:
            cleaned.append(text)
            seen.add(key)
    return cleaned


def _embedding_text(row: pd.Series) -> str:
    """Build the five-part document consumed by the embedding model."""
    return "\n".join(
        [
            f"Title: {row['title']}",
            f"Authors: {row['authors_joined']}",
            f"Published: {row['published']}",
            f"Categories: {row['categories_joined']}",
            f"Summary: {row['summary']}",
        ]
    )
