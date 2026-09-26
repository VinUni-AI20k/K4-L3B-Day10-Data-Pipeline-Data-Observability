from __future__ import annotations

from datetime import datetime, timezone
import pandas as pd

from ingestion.crossref import PaperRecord


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    """Clean raw records into a pandas DataFrame ready for embedding and quality checks."""
    if not records:
        return pd.DataFrame()

    rows = []
    for r in records:
        title = (r.title or "").strip()
        summary = (r.summary or "").strip()
        paper_id = (r.paper_id or "").strip()
        if not paper_id or not title:
            continue

        authors_list = r.authors if isinstance(r.authors, list) else []
        authors_joined = ", ".join([a.strip() for a in authors_list if a.strip()])

        categories_list = r.categories if isinstance(r.categories, list) else []
        categories_joined = ", ".join([c.strip() for c in categories_list if c.strip()])

        published_str = (r.published or "2026-01-01").strip()
        try:
            pub_dt = datetime.fromisoformat(published_str).replace(tzinfo=timezone.utc)
        except Exception:
            pub_dt = datetime(2026, 1, 1, tzinfo=timezone.utc)

        # Make sure run_date is timezone-aware
        if run_date.tzinfo is None:
            run_date = run_date.replace(tzinfo=timezone.utc)

        age_days = max(0, (run_date - pub_dt).days)

        text_for_embedding = (
            f"Title: {title}\n"
            f"Authors: {authors_joined}\n"
            f"Published: {published_str}\n"
            f"Categories: {categories_joined}\n"
            f"Summary: {summary}"
        )

        rows.append({
            "paper_id": paper_id,
            "title": title,
            "summary": summary,
            "authors": authors_list,
            "authors_joined": authors_joined,
            "categories": categories_list,
            "categories_joined": categories_joined,
            "primary_category": r.primary_category or (categories_list[0] if categories_list else ""),
            "published": published_str,
            "updated": r.updated or published_str,
            "abs_url": r.abs_url,
            "pdf_url": r.pdf_url,
            "comment": r.comment,
            "age_days": age_days,
            "summary_chars": len(summary),
            "text_for_embedding": text_for_embedding,
        })

    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.drop_duplicates(subset=["paper_id"], keep="first").reset_index(drop=True)
    return df
