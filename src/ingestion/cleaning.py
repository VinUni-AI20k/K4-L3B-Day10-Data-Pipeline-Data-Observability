from __future__ import annotations

from datetime import datetime
import re
import pandas as pd

from core.utils import compact_join, normalize_whitespace
from ingestion.crossref import PaperRecord


def _clean_text(val: str) -> str:
    cleaned = re.sub(r"<[^>]+>", " ", str(val or ""))
    return normalize_whitespace(cleaned)


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    """Clean raw records into a standardized DataFrame ready for embedding and quality checks."""
    rows = []
    for r in records:
        title = _clean_text(r.title)
        summary = _clean_text(r.summary)
        paper_id = r.paper_id.strip()
        if not paper_id or not title:
            continue

        authors = [normalize_whitespace(a) for a in r.authors if normalize_whitespace(a)]
        categories = [normalize_whitespace(c) for c in r.categories if normalize_whitespace(c)]
        authors_joined = compact_join(authors, ", ")
        categories_joined = compact_join(categories, ", ")

        published = r.published[:10] if r.published else "2026-01-01"
        updated = r.updated[:10] if r.updated else published

        # Compute age_days
        try:
            pub_date = datetime.fromisoformat(published)
            if run_date.tzinfo and not pub_date.tzinfo:
                pub_date = pub_date.replace(tzinfo=run_date.tzinfo)
            elif not run_date.tzinfo and pub_date.tzinfo:
                pub_date = pub_date.replace(tzinfo=None)
            age_days = max(0, (run_date - pub_date).days)
        except Exception:
            age_days = 0

        summary_chars = len(summary)

        # 5-part structure: Title, Authors, Categories, Published, Summary
        text_for_embedding = (
            f"Title: {title}\n"
            f"Authors: {authors_joined}\n"
            f"Categories: {categories_joined}\n"
            f"Published: {published}\n"
            f"Summary: {summary}"
        )

        rows.append(
            {
                "paper_id": paper_id,
                "title": title,
                "summary": summary,
                "authors": authors,
                "categories": categories,
                "primary_category": r.primary_category or (categories[0] if categories else "General"),
                "published": published,
                "updated": updated,
                "abs_url": r.abs_url,
                "pdf_url": r.pdf_url,
                "comment": r.comment,
                "authors_joined": authors_joined,
                "categories_joined": categories_joined,
                "summary_chars": summary_chars,
                "age_days": age_days,
                "text_for_embedding": text_for_embedding,
            }
        )

    df = pd.DataFrame(rows)
    if df.empty:
        return df

    # Deduplicate by paper_id and sort
    df = df.drop_duplicates(subset=["paper_id"], keep="first")
    df = df.sort_values(by=["published", "paper_id"], ascending=[False, True]).reset_index(drop=True)
    return df
