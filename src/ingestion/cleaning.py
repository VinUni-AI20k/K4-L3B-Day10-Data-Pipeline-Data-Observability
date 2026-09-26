from __future__ import annotations

from datetime import datetime
import html
import re
from collections.abc import Iterable

import pandas as pd

from core.utils import normalize_whitespace
from ingestion.crossref import PaperRecord


_MARKUP_PATTERN = re.compile(r"<[^>]+>")


def _clean_text(value: object) -> str:
    """Return plain, whitespace-normalized text for a raw scalar value."""
    if value is None:
        return ""
    without_markup = _MARKUP_PATTERN.sub(" ", html.unescape(str(value)))
    return normalize_whitespace(without_markup)


def _clean_list(values: Iterable[object] | None) -> list[str]:
    """Normalize a string collection and remove duplicates while preserving order."""
    cleaned: list[str] = []
    seen: set[str] = set()
    for value in values or []:
        item = _clean_text(value)
        key = item.casefold()
        if item and key not in seen:
            cleaned.append(item)
            seen.add(key)
    return cleaned


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    """Clean Crossref records into the stable dataframe contract used downstream."""
    columns = [
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
        "authors_joined",
        "categories_joined",
        "summary_chars",
        "age_days",
        "text_for_embedding",
    ]

    run_timestamp = pd.Timestamp(run_date)
    if run_timestamp.tzinfo is None:
        run_timestamp = run_timestamp.tz_localize("UTC")
    else:
        run_timestamp = run_timestamp.tz_convert("UTC")
    run_day = run_timestamp.normalize()

    cleaned_rows: list[dict[str, object]] = []
    seen_paper_ids: set[str] = set()

    for record in records:
        paper_id = _clean_text(record.paper_id)
        title = _clean_text(record.title)
        summary = _clean_text(record.summary)
        published_at = pd.to_datetime(record.published, errors="coerce", utc=True)

        # These fields form the minimum useful document contract for retrieval.
        if not paper_id or not title or not summary or pd.isna(published_at):
            continue

        paper_id_key = paper_id.casefold()
        if paper_id_key in seen_paper_ids:
            continue
        seen_paper_ids.add(paper_id_key)

        authors = _clean_list(record.authors)
        categories = _clean_list(record.categories)
        primary_category = _clean_text(record.primary_category)
        if not categories:
            categories = [primary_category] if primary_category else ["Uncategorized"]
        if not primary_category:
            primary_category = categories[0]

        updated_at = pd.to_datetime(record.updated, errors="coerce", utc=True)
        published = published_at.date().isoformat()
        updated = "" if pd.isna(updated_at) else updated_at.date().isoformat()
        authors_joined = ", ".join(authors)
        categories_joined = ", ".join(categories)
        age_days = int((run_day - published_at.normalize()).days)

        text_for_embedding = "\n".join(
            [
                f"Title: {title}",
                f"Authors: {authors_joined}",
                f"Categories: {categories_joined}",
                f"Published: {published}",
                f"Summary: {summary}",
            ]
        )

        cleaned_rows.append(
            {
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
                "authors_joined": authors_joined,
                "categories_joined": categories_joined,
                "summary_chars": len(summary),
                "age_days": age_days,
                "text_for_embedding": text_for_embedding,
            }
        )

    if not cleaned_rows:
        return pd.DataFrame(columns=columns)

    return (
        pd.DataFrame(cleaned_rows, columns=columns)
        .sort_values(["published", "paper_id"], ascending=[False, True], kind="stable")
        .reset_index(drop=True)
    )
