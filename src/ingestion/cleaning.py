import re
from dataclasses import asdict
from datetime import date, datetime

import pandas as pd

from ingestion.crossref import PaperRecord


def _normalize_space(text: str | None) -> str:
    if not text:
        return ""
    return re.sub(r"\s+", " ", str(text)).strip()


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    """Clean raw records thanh dataframe san sang de embed.

    1. Normalize title, summary, authors, categories.
    2. Parse published/updated date.
    3. Tinh age_days.
    4. Tao cot helper:
       - authors_joined
       - categories_joined
       - summary_chars
       - text_for_embedding
    5. Drop duplicates va filter row xau.
    6. Sort dataframe va return.
    """
    if not records:
        return pd.DataFrame()

    rows: list[dict] = []
    run_date_val = run_date.date() if isinstance(run_date, datetime) else run_date

    for record in records:
        rec_dict = asdict(record)

        paper_id = _normalize_space(rec_dict.get("paper_id"))
        title = _normalize_space(rec_dict.get("title"))
        summary = _normalize_space(rec_dict.get("summary"))

        # Skip invalid rows
        if not paper_id or not title:
            continue

        raw_authors = rec_dict.get("authors") or []
        authors = [_normalize_space(a) for a in raw_authors if _normalize_space(a)]
        authors_joined = ", ".join(authors) if authors else "Unknown"

        raw_categories = rec_dict.get("categories") or []
        categories = [_normalize_space(c) for c in raw_categories if _normalize_space(c)]
        categories_joined = ", ".join(categories) if categories else "General"
        primary_category = categories[0] if categories else "General"

        published_str = _normalize_space(rec_dict.get("published")) or "2026-01-01"
        try:
            pub_date = datetime.strptime(published_str, "%Y-%m-%d").date()
        except ValueError:
            pub_date = date(2026, 1, 1)
            published_str = "2026-01-01"

        age_days = max(0, (run_date_val - pub_date).days)
        summary_chars = len(summary)

        text_for_embedding = (
            f"Title: {title}\n"
            f"Authors: {authors_joined}\n"
            f"Published: {published_str}\n"
            f"Categories: {categories_joined}\n"
            f"Summary: {summary}"
        )

        rec_dict.update({
            "paper_id": paper_id,
            "title": title,
            "summary": summary,
            "authors": authors,
            "authors_joined": authors_joined,
            "categories": categories,
            "categories_joined": categories_joined,
            "primary_category": primary_category,
            "published": published_str,
            "updated": _normalize_space(rec_dict.get("updated")) or published_str,
            "abs_url": _normalize_space(rec_dict.get("abs_url")),
            "pdf_url": _normalize_space(rec_dict.get("pdf_url")),
            "comment": _normalize_space(rec_dict.get("comment")),
            "age_days": age_days,
            "summary_chars": summary_chars,
            "text_for_embedding": text_for_embedding,
        })
        rows.append(rec_dict)

    df = pd.DataFrame(rows)

    # Khử trùng lặp bản ghi theo paper_id
    df = df.drop_duplicates(subset=["paper_id"], keep="first")

    # Sắp xếp theo ngày xuất bản mới nhất
    df = df.sort_values(by="published", ascending=False).reset_index(drop=True)

    return df
