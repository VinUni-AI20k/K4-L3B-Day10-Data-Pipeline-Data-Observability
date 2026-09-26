from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd

from core.utils import compact_join, normalize_whitespace
from ingestion.crossref import PaperRecord


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    """Clean raw records thanh dataframe san sang de embed."""
    rows = []
    for record in records:
        title = normalize_whitespace(record.title)
        summary = normalize_whitespace(record.summary)
        if not record.paper_id or not title or not summary:
            continue

        authors_joined = compact_join(a.strip() for a in record.authors)
        categories_joined = compact_join(c.strip() for c in record.categories)

        published_dt = pd.to_datetime(record.published, errors="coerce", utc=True)
        if pd.isna(published_dt):
            continue
        age_days = (run_date.replace(tzinfo=timezone.utc) - published_dt.to_pydatetime()).days

        text_for_embedding = (
            f"Title: {title}\n"
            f"Authors: {authors_joined}\n"
            f"Published: {record.published}\n"
            f"Categories: {categories_joined}\n"
            f"Summary: {summary}"
        )

        rows.append(
            {
                "paper_id": record.paper_id,
                "title": title,
                "summary": summary,
                "authors": record.authors,
                "authors_joined": authors_joined,
                "categories": record.categories,
                "categories_joined": categories_joined,
                "primary_category": record.primary_category,
                "published": record.published,
                "updated": record.updated,
                "abs_url": record.abs_url,
                "pdf_url": record.pdf_url,
                "age_days": age_days,
                "summary_chars": len(summary),
                "text_for_embedding": text_for_embedding,
            }
        )

    df = pd.DataFrame(rows)
    if df.empty:
        return df

    df = df.drop_duplicates(subset="paper_id", keep="first")
    df = df.sort_values(by="published", ascending=False).reset_index(drop=True)
    return df
