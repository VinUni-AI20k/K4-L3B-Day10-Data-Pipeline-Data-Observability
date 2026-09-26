from __future__ import annotations

from datetime import datetime

import pandas as pd

from core.utils import normalize_whitespace
from ingestion.crossref import PaperRecord


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    """Clean raw records thành dataframe sẵn sàng để embed.

    1. Normalize title, summary, authors, categories.
    2. Parse published/updated date.
    3. Tính age_days = (run_date - published).days.
    4. Tạo các cột helper:
       - authors_joined
       - categories_joined
       - summary_chars
       - text_for_embedding theo template:
         Title: <Tiêu đề bài báo>
         Authors: <Danh sách tác giả>
         Published: <Ngày xuất bản>
         Categories: <Lĩnh vực chuyên môn>
         Summary: <Tóm tắt nội dung>
    5. Drop duplicates theo paper_id và filter row xấu.
    6. Sort dataframe theo published giảm dần và return.
    """
    rows = []
    # Đảm bảo run_date so sánh cùng timezone nếu published có/không có timezone
    # Thông thường published là date-only YYYY-MM-DD
    target_date = run_date.date() if isinstance(run_date, datetime) else run_date

    for r in records:
        paper_id = (r.paper_id or "").strip()
        if not paper_id:
            continue

        title = normalize_whitespace(r.title or "")
        summary = normalize_whitespace(r.summary or "")
        if not title:
            continue

        authors_list = [normalize_whitespace(a) for a in (r.authors or []) if a]
        authors_joined = ", ".join(authors_list)

        categories_list = [normalize_whitespace(c) for c in (r.categories or []) if c]
        categories_joined = ", ".join(categories_list)
        primary_category = (
            normalize_whitespace(r.primary_category)
            if r.primary_category
            else (categories_list[0] if categories_list else "Computer Science")
        )

        published_str = (r.published or "").strip()
        try:
            pub_date = datetime.strptime(published_str[:10], "%Y-%m-%d").date()
        except Exception:
            pub_date = target_date
            published_str = pub_date.isoformat()

        age_days = (target_date - pub_date).days

        updated_str = (r.updated or "").strip() or published_str
        abs_url = (r.abs_url or "").strip()
        pdf_url = (r.pdf_url or "").strip()
        comment = (r.comment or "").strip()

        # Format chuẩn theo hướng dẫn:
        # Title: <Tiêu đề bài báo>
        # Authors: <Danh sách tác giả>
        # Published: <Ngày xuất bản>
        # Categories: <Lĩnh vực chuyên môn>
        # Summary: <Tóm tắt nội dung>
        text_for_embedding = (
            f"Title: {title}\n"
            f"Authors: {authors_joined}\n"
            f"Published: {published_str}\n"
            f"Categories: {categories_joined}\n"
            f"Summary: {summary}"
        )

        rows.append(
            {
                "paper_id": paper_id,
                "title": title,
                "summary": summary,
                "authors": authors_list,
                "authors_joined": authors_joined,
                "categories": categories_list,
                "categories_joined": categories_joined,
                "primary_category": primary_category,
                "published": published_str,
                "updated": updated_str,
                "age_days": age_days,
                "summary_chars": len(summary),
                "text_for_embedding": text_for_embedding,
                "abs_url": abs_url,
                "pdf_url": pdf_url,
                "comment": comment,
            }
        )

    df = pd.DataFrame(rows)
    if df.empty:
        return df

    # Khử trùng lặp theo paper_id (giữ bản ghi đầu tiên)
    df = df.drop_duplicates(subset=["paper_id"], keep="first")

    # Sắp xếp theo ngày xuất bản giảm dần
    df = df.sort_values(by="published", ascending=False).reset_index(drop=True)

    return df

