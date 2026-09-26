from __future__ import annotations

from datetime import datetime, timezone
import re
from typing import Sequence

import pandas as pd

from ingestion.crossref import PaperRecord


def _clean_str(text: str | None) -> str:
    """Loại bỏ khoảng trắng thừa và chuẩn hóa chuỗi."""
    if not text:
        return ""
    return " ".join(str(text).split())


def _parse_date(date_str: str | None) -> datetime | None:
    """Parse chuỗi ngày tháng theo các format phổ biến."""
    if not date_str:
        return None
    cleaned = _clean_str(date_str)
    for fmt in ("%Y-%m-%d", "%Y-%m", "%Y"):
        try:
            return datetime.strptime(cleaned, fmt)
        except ValueError:
            continue
    return None


def format_text_for_embedding(
    title: str,
    authors_joined: str,
    published: str,
    categories_joined: str,
    summary: str,
) -> str:
    """Tạo đoạn văn bản ngữ cảnh chuẩn hóa phục vụ embedding."""
    return (
        f"Title: {title}\n"
        f"Authors: {authors_joined}\n"
        f"Published: {published}\n"
        f"Categories: {categories_joined}\n"
        f"Summary: {summary}"
    )


def build_clean_dataframe(records: Sequence[PaperRecord], run_date: datetime) -> pd.DataFrame:
    """Làm sạch danh sách raw PaperRecord thành DataFrame chuẩn hóa để embed.

    Các bước thực hiện:
    1. Chuẩn hóa title, summary, authors, categories.
    2. Parse published/updated date.
    3. Tính tuổi đời dữ liệu age_days = (run_date - published).days.
    4. Tạo các cột helper:
       - authors_joined
       - categories_joined
       - summary_chars
       - text_for_embedding
    5. Khử trùng lặp theo paper_id và lọc bỏ bản ghi không hợp lệ.
    6. Sắp xếp DataFrame (theo published giảm dần, paper_id).
    """
    if not records:
        return pd.DataFrame(
            columns=[
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
        )

    run_d = run_date.date() if isinstance(run_date, datetime) else run_date

    cleaned_rows = []
    seen_ids = set()

    for r in records:
        paper_id = _clean_str(r.paper_id)
        title = _clean_str(r.title)

        # Lọc bản ghi thiếu paper_id hoặc title
        if not paper_id or not title:
            continue

        # Khử trùng lặp theo paper_id (giữ bản ghi đầu tiên)
        if paper_id in seen_ids:
            continue
        seen_ids.add(paper_id)

        summary = _clean_str(r.summary)

        # Chuẩn hóa authors
        authors = [_clean_str(a) for a in (r.authors or []) if _clean_str(a)]
        authors_joined = ", ".join(authors)

        # Chuẩn hóa categories
        categories = [_clean_str(c) for c in (r.categories or []) if _clean_str(c)]
        categories_joined = ", ".join(categories)

        primary_category = _clean_str(r.primary_category)
        if not primary_category and categories:
            primary_category = categories[0]

        # Chuẩn hóa date và tính age_days
        published_str = _clean_str(r.published)
        updated_str = _clean_str(r.updated) or published_str

        pub_dt = _parse_date(published_str)
        if pub_dt:
            age_days = max(0, (run_d - pub_dt.date()).days)
            published_formatted = pub_dt.strftime("%Y-%m-%d")
        else:
            age_days = 0
            published_formatted = published_str

        summary_chars = len(summary)

        # Ghép nối text_for_embedding theo chuẩn quy định
        text_for_embedding = format_text_for_embedding(
            title=title,
            authors_joined=authors_joined,
            published=published_formatted,
            categories_joined=categories_joined,
            summary=summary,
        )

        cleaned_rows.append(
            {
                "paper_id": paper_id,
                "title": title,
                "summary": summary,
                "authors": authors,
                "categories": categories,
                "primary_category": primary_category,
                "published": published_formatted,
                "updated": updated_str,
                "abs_url": _clean_str(r.abs_url),
                "pdf_url": _clean_str(r.pdf_url),
                "comment": _clean_str(r.comment),
                "authors_joined": authors_joined,
                "categories_joined": categories_joined,
                "summary_chars": summary_chars,
                "age_days": int(age_days),
                "text_for_embedding": text_for_embedding,
            }
        )

    df = pd.DataFrame(cleaned_rows)

    if not df.empty:
        # Sắp xếp theo published giảm dần (mới nhất lên đầu), sau đó theo paper_id
        df = df.sort_values(by=["published", "paper_id"], ascending=[False, True]).reset_index(drop=True)

    return df

