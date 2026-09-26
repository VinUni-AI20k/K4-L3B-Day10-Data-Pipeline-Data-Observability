from __future__ import annotations

from datetime import datetime

import pandas as pd

from core.utils import compact_join, normalize_whitespace
from ingestion.crossref import PaperRecord


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    """Clean raw PaperRecord list into a DataFrame ready for embedding.

    Steps:
    1. Normalize title, summary, authors, categories
    2. Parse published / updated dates
    3. Compute age_days = (run_date - published).days
    4. Build helper columns: authors_joined, categories_joined, summary_chars, text_for_embedding
    5. Drop duplicates on paper_id, filter bad rows
    6. Sort by published desc and return
    """
    rows = []
    for rec in records:
        title = normalize_whitespace(rec.title)
        summary = normalize_whitespace(rec.summary)
        authors = [normalize_whitespace(a) for a in rec.authors if a.strip()]
        categories = [normalize_whitespace(c) for c in rec.categories if c.strip()]

        # Parse published date
        try:
            pub_date = datetime.fromisoformat(rec.published).date()
        except Exception:
            pub_date = None

        # age_days relative to run_date (make both tz-naive for comparison)
        if pub_date is not None:
            run_naive = run_date.replace(tzinfo=None) if run_date.tzinfo else run_date
            age_days = (run_naive.date() - pub_date).days
        else:
            age_days = None

        authors_joined = compact_join(authors)
        categories_joined = compact_join(categories)
        summary_chars = len(summary)

        text_for_embedding = (
            f"Title: {title}\n"
            f"Authors: {authors_joined}\n"
            f"Categories: {categories_joined}\n"
            f"Published: {rec.published}\n"
            f"Summary: {summary}"
        ).strip()

        rows.append(
            {
                "paper_id": rec.paper_id,
                "title": title,
                "summary": summary,
                "authors": authors,
                "categories": categories,
                "primary_category": rec.primary_category,
                "published": rec.published,
                "updated": rec.updated,
                "abs_url": rec.abs_url,
                "pdf_url": rec.pdf_url,
                "comment": rec.comment,
                "age_days": age_days,
                "authors_joined": authors_joined,
                "categories_joined": categories_joined,
                "summary_chars": summary_chars,
                "text_for_embedding": text_for_embedding,
            }
        )

    df = pd.DataFrame(rows)

    # Filter: must have paper_id, title, text_for_embedding
    df = df[df["paper_id"].notna() & (df["paper_id"] != "")]
    df = df[df["title"].notna() & (df["title"] != "")]
    df = df[df["text_for_embedding"].notna() & (df["text_for_embedding"] != "")]

    # Drop duplicates on paper_id (keep first)
    df = df.drop_duplicates(subset=["paper_id"], keep="first")

    # Sort by published descending
    df = df.sort_values("published", ascending=False, ignore_index=True)

    return df
