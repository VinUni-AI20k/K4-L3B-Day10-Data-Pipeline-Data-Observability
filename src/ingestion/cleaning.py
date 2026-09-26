from __future__ import annotations

from datetime import UTC, datetime

import pandas as pd

from core.utils import normalize_whitespace
from ingestion.crossref import PaperRecord


CLEAN_COLUMNS = [
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
    """Normalize raw papers into a deterministic embedding-ready dataframe."""
    if not records:
        return pd.DataFrame(columns=CLEAN_COLUMNS)

    rows = []
    for record in records:
        paper_id = normalize_whitespace(record.paper_id)
        title = normalize_whitespace(record.title)
        summary = normalize_whitespace(record.summary)
        if not paper_id or not title or not summary:
            continue

        authors = _normalize_list(record.authors)
        categories = _normalize_list(record.categories)
        published = pd.to_datetime(record.published, errors="coerce", utc=True)
        updated = pd.to_datetime(record.updated, errors="coerce", utc=True)
        if pd.isna(published):
            continue
        if pd.isna(updated):
            updated = published

        authors_joined = ", ".join(authors)
        categories_joined = ", ".join(categories)
        published_text = published.date().isoformat()
        rows.append(
            {
                "paper_id": paper_id,
                "title": title,
                "summary": summary,
                "authors": authors,
                "categories": categories,
                "primary_category": normalize_whitespace(record.primary_category)
                or (categories[0] if categories else ""),
                "published": published_text,
                "updated": updated.date().isoformat(),
                "abs_url": normalize_whitespace(record.abs_url),
                "pdf_url": normalize_whitespace(record.pdf_url),
                "comment": normalize_whitespace(record.comment),
                "authors_joined": authors_joined,
                "categories_joined": categories_joined,
                "summary_chars": len(summary),
                "text_for_embedding": (
                    f"Title: {title}\n"
                    f"Authors: {authors_joined}\n"
                    f"Published: {published_text}\n"
                    f"Categories: {categories_joined}\n"
                    f"Summary: {summary}"
                ),
            }
        )

    if not rows:
        return pd.DataFrame(columns=CLEAN_COLUMNS)

    df = pd.DataFrame(rows).drop_duplicates(subset=["paper_id"], keep="first")
    normalized_run_date = _as_utc_timestamp(run_date)
    published_dates = pd.to_datetime(df["published"], errors="coerce", utc=True)
    df["age_days"] = (normalized_run_date.normalize() - published_dates).dt.days.astype("int64")
    return df[CLEAN_COLUMNS].sort_values(["published", "paper_id"], ascending=[False, True]).reset_index(drop=True)


def _normalize_list(values: list[str]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for value in values or []:
        text = normalize_whitespace(str(value))
        if text and text.casefold() not in seen:
            normalized.append(text)
            seen.add(text.casefold())
    return normalized


def _as_utc_timestamp(value: datetime) -> pd.Timestamp:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return pd.Timestamp(value).tz_convert("UTC")
