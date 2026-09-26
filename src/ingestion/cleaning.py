from __future__ import annotations

from datetime import datetime, timezone
import re
import pandas as pd

from core.utils import compact_join, normalize_whitespace
from ingestion.crossref import PaperRecord


def _parse_date(date_str: str):
    if not date_str:
        return None
    clean = date_str[:10].strip()
    for fmt in ("%Y-%m-%d", "%Y-%m", "%Y"):
        try:
            return datetime.strptime(clean, fmt).date()
        except ValueError:
            pass
    return None


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    """Clean raw records thanh dataframe san sang de embed."""
    run_date_val = run_date.date() if isinstance(run_date, datetime) else run_date

    rows: list[dict] = []
    for record in records:
        paper_id = record.paper_id.strip() if record.paper_id else ""
        if not paper_id:
            continue

        title = normalize_whitespace(record.title or "")
        summary = normalize_whitespace(record.summary or "")

        # Loai bo cac the JATS / XML con sot lai neu co
        title = normalize_whitespace(re.sub(r"<[^>]+>", "", title))
        summary = normalize_whitespace(re.sub(r"<[^>]+>", "", summary))

        if not title or len(summary) < 10:
            continue

        authors = [normalize_whitespace(a) for a in record.authors if a and normalize_whitespace(a)]
        authors_joined = compact_join(authors, sep=", ") or "Unknown Author"

        categories = [normalize_whitespace(c) for c in record.categories if c and normalize_whitespace(c)]
        categories_joined = compact_join(categories, sep=", ") or "General"
        primary_category = record.primary_category or (categories[0] if categories else "General")

        pub_date = _parse_date(record.published) or _parse_date(record.updated) or run_date_val
        upd_date = _parse_date(record.updated) or pub_date

        published_str = pub_date.strftime("%Y-%m-%d")
        updated_str = upd_date.strftime("%Y-%m-%d")

        age_days = max(0, (run_date_val - pub_date).days)
        summary_chars = len(summary)

        text_for_embedding = (
            f"Title: {title}\n"
            f"Authors: {authors_joined}\n"
            f"Published Date: {published_str}\n"
            f"Categories: {categories_joined}\n"
            f"Summary: {summary}"
        )

        rows.append(
            {
                "paper_id": paper_id,
                "title": title,
                "summary": summary,
                "summary_chars": summary_chars,
                "authors": authors,
                "authors_joined": authors_joined,
                "categories": categories,
                "categories_joined": categories_joined,
                "primary_category": primary_category,
                "published": published_str,
                "updated": updated_str,
                "age_days": age_days,
                "abs_url": record.abs_url or f"https://doi.org/{paper_id}",
                "pdf_url": record.pdf_url or f"https://doi.org/{paper_id}",
                "comment": record.comment or f"Crossref record {paper_id}",
                "text_for_embedding": text_for_embedding,
            }
        )

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    df.drop_duplicates(subset=["paper_id"], keep="first", inplace=True)
    df.sort_values(by=["published", "paper_id"], ascending=[False, True], inplace=True)
    return df.reset_index(drop=True)

