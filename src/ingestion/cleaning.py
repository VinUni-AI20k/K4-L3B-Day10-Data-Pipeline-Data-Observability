from __future__ import annotations

from datetime import datetime, timezone
import re

import pandas as pd

from core.utils import normalize_whitespace
from ingestion.crossref import PaperRecord


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    """Clean raw records thanh dataframe san sang de embed.

    1. Normalize title, summary, authors, categories.
    2. Parse published/updated date.
    3. Tinh age_days = (run_date - published).days.
    4. Tao cot helper:
       - authors_joined
       - categories_joined
       - summary_chars
       - text_for_embedding (cau truc 5 phan: Title, Authors, Published, Categories, Summary)
    5. Drop duplicates theo paper_id va filter row xau.
    6. Sort dataframe va return.
    """
    rows: list[dict] = []

    if isinstance(run_date, datetime):
        current_date = run_date.date()
    else:
        current_date = run_date

    for rec in records:
        paper_id = str(rec.paper_id).strip()
        if not paper_id:
            continue

        title = normalize_whitespace(str(rec.title))

        raw_summary = re.sub(r"<[^>]+>", " ", str(rec.summary))
        summary = normalize_whitespace(raw_summary)

        authors = [normalize_whitespace(str(a)) for a in rec.authors if str(a).strip()]
        if not authors:
            authors = ["Unknown Author"]
        authors_joined = ", ".join(authors)

        categories = [normalize_whitespace(str(c)) for c in rec.categories if str(c).strip()]
        if not categories:
            categories = ["General"]
        categories_joined = ", ".join(categories)
        primary_category = str(rec.primary_category).strip() or categories[0]

        pub_str = str(rec.published).strip()[:10]
        try:
            pub_date = datetime.strptime(pub_str, "%Y-%m-%d").date()
            published = pub_date.isoformat()
            age_days = max(0, (current_date - pub_date).days)
        except Exception:
            published = pub_str or "2026-01-01"
            age_days = 0

        upd_str = str(rec.updated).strip()[:10]
        try:
            upd_date = datetime.strptime(upd_str, "%Y-%m-%d").date()
            updated = upd_date.isoformat()
        except Exception:
            updated = published

        abs_url = str(rec.abs_url).strip()
        pdf_url = str(rec.pdf_url).strip() or abs_url
        comment = str(rec.comment).strip()
        summary_chars = len(summary)

        # Cau truc 5 phan chuan theo tieu chi Rubric
        text_for_embedding = (
            f"Title: {title}\n"
            f"Authors: {authors_joined}\n"
            f"Published: {published}\n"
            f"Categories: {categories_joined}\n"
            f"Summary: {summary}"
        )

        rows.append(
            {
                "paper_id": paper_id,
                "title": title,
                "summary": summary,
                "authors": authors,
                "authors_joined": authors_joined,
                "categories": categories,
                "categories_joined": categories_joined,
                "primary_category": primary_category,
                "published": published,
                "updated": updated,
                "abs_url": abs_url,
                "pdf_url": pdf_url,
                "comment": comment,
                "summary_chars": summary_chars,
                "age_days": age_days,
                "text_for_embedding": text_for_embedding,
            }
        )

    df = pd.DataFrame(rows)

    if df.empty:
        return df

    # Khử trùng lặp theo paper_id
    df = df.drop_duplicates(subset=["paper_id"], keep="first")

    # Loại bỏ bản ghi không hợp lệ
    df = df[df["paper_id"].str.strip() != ""]
    df = df[df["title"].str.strip() != ""]
    df = df[df["summary"].str.strip() != ""]

    # Sắp xếp theo ngày xuất bản mới nhất
    df = df.sort_values(by="published", ascending=False).reset_index(drop=True)

    return df
