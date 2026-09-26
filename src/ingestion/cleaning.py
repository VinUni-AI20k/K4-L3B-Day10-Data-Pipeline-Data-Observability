from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import datetime
from pathlib import Path
import re
from typing import Any

import pandas as pd


def build_clean_dataframe(raw_records: list, run_date: Any) -> pd.DataFrame:
    """Clean và biến đổi danh sách bản ghi thô (raw_records) thành DataFrame sẵn sàng cho quá trình Embedding.

    Các bước thực hiện tuần tự:
    1. Khởi tạo DataFrame từ danh sách các đối tượng hoặc dict.
    2. Khử trùng lặp theo khóa chính `paper_id` (giữ bản ghi đầu tiên).
    3. Làm sạch khoảng trắng trên các cột văn bản (title, summary, authors, categories).
    4. Ép kiểu cột `published` về datetime và tính tuổi dữ liệu `age_days`.
    5. Tạo chuỗi ngữ cảnh `text_for_embedding` bằng phương pháp vectorized.
    """
    if not raw_records:
        return pd.DataFrame()

    # 1. Khởi tạo: chuyển đổi danh sách raw_records (object hoặc dict) thành DataFrame
    data = [
        asdict(r) if is_dataclass(r) else (r.__dict__ if hasattr(r, "__dict__") else dict(r))
        for r in raw_records
    ]
    df = pd.DataFrame(data)

    # 2. Khử trùng lặp (Deduplication) dựa trên khóa chính paper_id
    if "paper_id" in df.columns:
        df = df.drop_duplicates(subset=["paper_id"], keep="first").reset_index(drop=True)

    # 3. Làm sạch khoảng trắng: Chuẩn hóa các cột văn bản (title, summary, authors, categories)
    for col in ["title", "summary"]:
        if col in df.columns:
            df[col] = (
                df[col]
                .fillna("")
                .astype(str)
                .str.strip()
                .str.replace(r"\s+", " ", regex=True)
            )

    def _clean_text_or_list(val: Any) -> str:
        if isinstance(val, list):
            cleaned = [re.sub(r"\s+", " ", str(x)).strip() for x in val if x]
            return ", ".join(item for item in cleaned if item)
        if pd.isna(val) or val is None:
            return ""
        return re.sub(r"\s+", " ", str(val)).strip()

    if "authors" in df.columns:
        df["authors"] = df["authors"].apply(_clean_text_or_list)
    else:
        df["authors"] = ""

    if "categories" in df.columns:
        df["categories"] = df["categories"].apply(_clean_text_or_list)
    else:
        df["categories"] = ""

    # Các cột bổ trợ phục vụ downstream retrieval và metrics
    df["authors_joined"] = df["authors"]
    df["categories_joined"] = df["categories"]
    df["summary_chars"] = df["summary"].str.len()

    # 4. Tính tuổi dữ liệu (age_days):
    # Ép kiểu cột published về định dạng datetime
    if "published" in df.columns:
        df["published"] = pd.to_datetime(df["published"], errors="coerce")
        run_dt = pd.to_datetime(run_date)
        pub_dt = df["published"]

        # Đồng bộ hóa timezone giữa run_date và published trước khi trừ ngày
        if run_dt.tzinfo is not None:
            run_dt = run_dt.tz_convert("UTC").tz_localize(None)
        if pub_dt.dt.tz is not None:
            pub_dt = pub_dt.dt.tz_convert("UTC").dt.tz_localize(None)

        # Tính age_days an toàn với các giá trị missing / NaN
        df["age_days"] = (run_dt - pub_dt).dt.days
        published_str = df["published"].dt.strftime("%Y-%m-%d").fillna("")
    else:
        df["age_days"] = float("nan")
        published_str = pd.Series([""] * len(df), index=df.index)

    # 5. Tạo chuỗi ngữ cảnh (text_for_embedding) theo đúng multiline format
    df["text_for_embedding"] = (
        "Title: " + df["title"].fillna("") + "\n"
        + "Authors: " + df["authors"].fillna("") + "\n"
        + "Published: " + published_str + "\n"
        + "Categories: " + df["categories"].fillna("") + "\n"
        + "Summary: " + df["summary"].fillna("")
    )

    return df
