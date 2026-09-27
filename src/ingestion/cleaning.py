from __future__ import annotations

from datetime import datetime
from html import unescape
import re

import pandas as pd

from ingestion.crossref import PaperRecord


_COLUMNS = [
    "paper_id", "title", "summary", "authors", "categories", "primary_category",
    "published", "updated", "abs_url", "pdf_url", "comment", "age_days",
    "authors_joined", "categories_joined", "summary_chars", "text_for_embedding",
]


def _clean_text(value: object) -> str:
    text = unescape(str(value or ""))
    text = re.sub(r"<[^>]*>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _date(value: object) -> str:
    try:
        parsed = pd.Timestamp(value)
        return "" if pd.isna(parsed) else parsed.date().isoformat()
    except (TypeError, ValueError, OverflowError):
        return ""


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    """Normalize raw metadata into the schema consumed by the retrieval index."""
    run_day = run_date.date()
    rows = []
    seen_ids: set[str] = set()
    for record in records:
        paper_id = _clean_text(record.paper_id)
        paper_id = re.sub(r"^(?:https?://(?:dx\.)?doi\.org/|doi:)", "", paper_id, flags=re.I).lower()
        title = _clean_text(record.title)
        summary = _clean_text(record.summary)
        published = _date(record.published)
        if not (paper_id and title and summary and published) or paper_id in seen_ids:
            continue
        seen_ids.add(paper_id)

        authors = [_clean_text(author) for author in record.authors]
        authors = list(dict.fromkeys(author for author in authors if author))
        categories = [_clean_text(category) for category in record.categories]
        categories = list(dict.fromkeys(category for category in categories if category))
        authors_joined = ", ".join(authors)
        categories_joined = ", ".join(categories)
        primary_category = _clean_text(record.primary_category) or (categories[0] if categories else "")
        updated = _date(record.updated) or published
        rows.append({
            "paper_id": paper_id,
            "title": title,
            "summary": summary,
            "authors": authors,
            "categories": categories,
            "primary_category": primary_category,
            "published": published,
            "updated": updated,
            "abs_url": _clean_text(record.abs_url),
            "pdf_url": _clean_text(record.pdf_url),
            "comment": _clean_text(record.comment),
            "age_days": (run_day - datetime.fromisoformat(published).date()).days,
            "authors_joined": authors_joined,
            "categories_joined": categories_joined,
            "summary_chars": len(summary),
            "text_for_embedding": (
                f"Title: {title}\nSummary: {summary}\nAuthors: {authors_joined}"
                f"\nPublished: {published}\nCategories: {categories_joined}"
            ),
        })

    return pd.DataFrame(rows, columns=_COLUMNS).sort_values(
        ["published", "paper_id"], ascending=[False, True]
    ).reset_index(drop=True)
