from __future__ import annotations

from datetime import datetime

import pandas as pd

from core.utils import compact_join, normalize_whitespace
from ingestion.crossref import PaperRecord


def build_text_for_embedding(row: dict) -> str:
    """5-phan cau truc: Title / Authors / Categories / Published / Summary."""
    parts = [
        f"Title: {row['title']}",
        f"Authors: {row['authors_joined']}",
        f"Categories: {row['categories_joined']}",
        f"Published: {row['published']}",
        f"Summary: {row['summary']}",
    ]
    return "\n".join(parts)


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    """Clean raw records thanh dataframe san sang de embed."""
    rows: list[dict] = []

    for record in records:
        title = normalize_whitespace(record.title)
        summary = normalize_whitespace(record.summary)
        authors = [normalize_whitespace(a) for a in record.authors if normalize_whitespace(a)]
        categories = [normalize_whitespace(c) for c in record.categories if normalize_whitespace(c)]

        if not record.paper_id or not title or not summary:
            continue

        try:
            published_date = datetime.fromisoformat(record.published) if record.published else None
        except ValueError:
            published_date = None

        if published_date is not None:
            if published_date.tzinfo is None:
                published_date = published_date.replace(tzinfo=run_date.tzinfo)
            age_days = (run_date - published_date).days
        else:
            age_days = None

        authors_joined = compact_join(authors)
        categories_joined = compact_join(categories)

        rows.append(
            {
                "paper_id": record.paper_id,
                "title": title,
                "summary": summary,
                "authors_joined": authors_joined,
                "categories_joined": categories_joined,
                "primary_category": record.primary_category,
                "published": record.published,
                "updated": record.updated,
                "abs_url": record.abs_url,
                "pdf_url": record.pdf_url,
                "comment": record.comment,
                "age_days": age_days,
                "summary_chars": len(summary),
            }
        )

    df = pd.DataFrame(rows)
    if df.empty:
        return df

    df = df.drop_duplicates(subset=["paper_id"], keep="first")
    df = df[df["title"].str.len() > 0]
    df = df[df["summary"].str.len() > 0]

    df["text_for_embedding"] = df.apply(lambda row: build_text_for_embedding(row), axis=1)

    df = df.sort_values(by="published", ascending=False).reset_index(drop=True)
    return df
