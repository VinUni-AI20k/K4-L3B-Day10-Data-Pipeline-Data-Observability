from __future__ import annotations

from dataclasses import asdict
from datetime import UTC, datetime
import re
from typing import Any

import pandas as pd

from core.utils import normalize_whitespace
from ingestion.crossref import PaperRecord


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    """Clean raw records thành dataframe sẵn sàng để embed và đánh chỉ mục.

    Các bước xử lý:
    1. Chuyển đổi records sang DataFrame.
    2. Làm sạch văn bản (loại bỏ JATS XML tags, chuẩn hóa khoảng trắng thừa).
    3. Tính toán cột age_days = (run_date - published).days an toàn theo UTC.
    4. Tạo các cột phụ trợ: authors_joined, categories_joined, summary_chars.
    5. Sinh cột text_for_embedding cấu trúc 5 phần chuẩn hóa.
    6. Khử trùng lặp theo paper_id, loại bỏ bản ghi không hợp lệ.
    7. Sắp xếp dataframe và trả về kết quả.
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

    rows = [asdict(r) for r in records]
    df = pd.DataFrame(rows)

    # 1. Khử trùng lặp theo paper_id
    df = df.drop_duplicates(subset=["paper_id"], keep="first").copy()

    # 2. Làm sạch title và summary (xóa thẻ XML/HTML, normalize whitespace)
    def clean_text(val: Any) -> str:
        s = str(val or "")
        s = re.sub(r"<[^>]+>", "", s)
        return normalize_whitespace(s)

    df["title"] = df["title"].apply(clean_text)
    df["summary"] = df["summary"].apply(clean_text)

    # 3. Tạo cột phụ trợ: authors_joined, categories_joined, summary_chars
    def join_list(val: Any) -> str:
        if isinstance(val, (list, tuple)):
            return ", ".join(str(item).strip() for item in val if str(item).strip())
        return str(val or "")

    df["authors_joined"] = df["authors"].apply(join_list)
    df["categories_joined"] = df["categories"].apply(join_list)
    df["summary_chars"] = df["summary"].str.len()

    # 4. Tính toán age_days
    ref_date = run_date.astimezone(UTC).date() if run_date.tzinfo is not None else run_date.date()

    def parse_age_days(pub_val: Any) -> int:
        try:
          pub_str = str(pub_val)[:10]
          dt = datetime.strptime(pub_str, "%Y-%m-%d").date()
          return max(0, (ref_date - dt).days)
        except Exception:
          return 0

    df["age_days"] = df["published"].apply(parse_age_days)

    # 5. Sinh cột text_for_embedding với cấu trúc 5 phần chuẩn
    def build_embedding_text(row: pd.Series) -> str:
        return (
            f"Title: {row['title']}\n"
            f"Authors: {row['authors_joined']}\n"
            f"Published: {row['published']}\n"
            f"Categories: {row['categories_joined']}\n"
            f"Summary: {row['summary']}"
        )

    df["text_for_embedding"] = df.apply(build_embedding_text, axis=1)

    # 6. Loại bỏ bản ghi không hợp lệ (paper_id hoặc title rỗng)
    df = df[(df["paper_id"].str.strip() != "") & (df["title"].str.strip() != "")].copy()

    # 7. Sắp xếp theo ngày xuất bản giảm dần
    df = df.sort_values(by=["published", "paper_id"], ascending=[False, True]).reset_index(drop=True)

    return df
