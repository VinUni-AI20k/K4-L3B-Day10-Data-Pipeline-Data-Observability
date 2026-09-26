from __future__ import annotations

from datetime import datetime

import pandas as pd

from core.utils import normalize_whitespace
from ingestion.crossref import PaperRecord


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    """Build a deduplicated, embedding-ready dataframe from raw records."""
    run_day = run_date.date()
    rows: list[dict] = []

    for raw_record in records:
        record = raw_record if isinstance(raw_record, PaperRecord) else PaperRecord(**raw_record)
        paper_id = normalize_whitespace(record.paper_id)
        title = normalize_whitespace(record.title)
        if not paper_id or not title:
            continue

        published_timestamp = pd.to_datetime(record.published, errors="coerce")
        if pd.isna(published_timestamp):
            continue
        published_day = published_timestamp.date()
        published = published_day.isoformat()
        authors = [normalize_whitespace(author) for author in record.authors if normalize_whitespace(author)]
        categories = [
            normalize_whitespace(category)
            for category in record.categories
            if normalize_whitespace(category)
        ]
        authors_joined = ", ".join(authors)
        categories_joined = ", ".join(categories)
        summary = normalize_whitespace(record.summary)

        rows.append(
            {
                "paper_id": paper_id,
                "title": title,
                "summary": summary,
                "authors": authors,
                "authors_joined": authors_joined,
                "categories": categories,
                "categories_joined": categories_joined,
                "primary_category": normalize_whitespace(record.primary_category),
                "published": published,
                "updated": normalize_whitespace(record.updated),
                "abs_url": normalize_whitespace(record.abs_url),
                "pdf_url": normalize_whitespace(record.pdf_url),
                "comment": normalize_whitespace(record.comment),
                "age_days": (run_day - published_day).days,
                "summary_chars": len(summary),
                "text_for_embedding": (
                    f"Title: {title}\n"
                    f"Authors: {authors_joined}\n"
                    f"Published: {published}\n"
                    f"Categories: {categories_joined}\n"
                    f"Summary: {summary}"
                ),
            }
        )

    dataframe = pd.DataFrame(rows)
    if dataframe.empty:
        return dataframe
    return (
        dataframe.drop_duplicates(subset="paper_id", keep="first")
        .sort_values("paper_id")
        .reset_index(drop=True)
    )
