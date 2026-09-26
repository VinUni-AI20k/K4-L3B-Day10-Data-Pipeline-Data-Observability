from __future__ import annotations

from datetime import datetime, timezone
import re

import pandas as pd

from ingestion.crossref import PaperRecord


def _clean_text(text: str) -> str:
    """Làm sạch các thẻ HTML/JATS XML và chuẩn hóa khoảng trắng."""
    if not text or not isinstance(text, str):
        return ""
    cleaned = re.sub(r"<[^>]+>", " ", text)
    return " ".join(cleaned.split())


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    """Làm sạch raw records thành pandas DataFrame sẵn sàng để index ChromaDB & đánh giá.

    Quy trình:
    1. Chuyển list PaperRecord thành danh sách dict.
    2. Chuẩn hóa title, summary, authors, categories (loại bỏ JATS XML tag).
    3. Tính toán trường `age_days = (run_date - published).days`.
    4. Tạo các cột helper: authors_joined, categories_joined, summary_chars, text_for_embedding (5 phần).
    5. Khử trùng lặp theo paper_id và lọc các bản ghi không hợp lệ.
    """
    rows = []
    # Đảm bảo run_date có timezone UTC để tính toán chính xác
    if run_date.tzinfo is None:
        run_date_utc = run_date.replace(tzinfo=timezone.utc)
    else:
        run_date_utc = run_date.astimezone(timezone.utc)

    for r in records:
        paper_id = str(r.paper_id).strip()
        title = _clean_text(r.title)
        summary = _clean_text(r.summary)

        # Xử lý authors
        authors = [a.strip() for a in r.authors if a.strip()] if r.authors else ["Unknown Author"]
        authors_joined = ", ".join(authors)

        # Xử lý categories
        categories = [c.strip() for c in r.categories if c.strip()] if r.categories else ["General"]
        categories_joined = ", ".join(categories)
        primary_category = r.primary_category if r.primary_category else categories[0]

        # Xử lý published date & age_days
        published_str = str(r.published).strip()
        age_days = 0
        try:
            pub_dt = pd.to_datetime(published_str, errors="coerce", utc=True)
            if pd.notna(pub_dt):
                delta = run_date_utc - pub_dt.to_pydatetime()
                age_days = max(0, delta.days)
        except Exception:
            age_days = 0

        # Ghép trường text_for_embedding chuẩn cấu trúc 5 phần
        text_for_embedding = (
            f"Title: {title}\n"
            f"Authors: {authors_joined}\n"
            f"Categories: {categories_joined}\n"
            f"Published Date: {published_str}\n"
            f"Summary: {summary}"
        ).strip()

        row = {
            "paper_id": paper_id,
            "title": title,
            "summary": summary,
            "authors": authors,
            "authors_joined": authors_joined,
            "categories": categories,
            "categories_joined": categories_joined,
            "primary_category": primary_category,
            "published": published_str,
            "updated": r.updated if r.updated else published_str,
            "age_days": int(age_days),
            "summary_chars": len(summary),
            "text_for_embedding": text_for_embedding,
            "abs_url": r.abs_url,
            "pdf_url": r.pdf_url,
            "comment": r.comment,
        }
        rows.append(row)

    df = pd.DataFrame(rows)

    if df.empty:
        return df

    # Khử trùng lặp theo paper_id (giữ bản ghi đầu tiên)
    df = df.drop_duplicates(subset=["paper_id"], keep="first").reset_index(drop=True)

    # Lọc các dòng hợp lệ: có paper_id và title không rỗng
    df = df[df["paper_id"].astype(bool) & (df["title"].str.len() > 0)].reset_index(drop=True)

    # Sắp xếp theo published date giảm dần
    df = df.sort_values(by=["published", "paper_id"], ascending=[False, True]).reset_index(drop=True)

    return df
