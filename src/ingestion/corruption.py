from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

import pandas as pd


def corrupt_clean_dataframe(
    df: pd.DataFrame, output_log_path: Path | str | None = None
) -> pd.DataFrame:
    """Simulate 6 dang data corruption thuc te:
    1. Drop latest records: Bo roi 20% cac bai bao moi nhat.
    2. Blank summary: Xoa trang phan tom tat o mot so dong.
    3. Inject noise: Chen cac chuoi ky tu rac vao tom tat.
    4. Truncate title: Cat ngan tieu de xuong duoi 8 ky tu.
    5. Stale date: Lui ngay xuat ban ve 365 ngay truoc (vi pham Freshness SLA).
    6. Duplicate rows: Nhan doi cac dong de tao trung lap (vi pham Unique constraint).
    7. Rebuild helper columns va text_for_embedding.
    8. Ghi nhat ky bien doi vao output_log_path (corruption_log.json).
    """
    if df.empty:
        return df.copy()

    # 1. Drop latest records (20% newest records by published date desc)
    df_sorted = df.sort_values(by="published", ascending=False).copy()
    drop_ratio = 0.20
    drop_count = max(1, int(round(len(df_sorted) * drop_ratio)))
    dropped_df = df_sorted.iloc[:drop_count]
    dropped_paper_ids = dropped_df["paper_id"].tolist()
    corrupted_df = df_sorted.iloc[drop_count:].copy().reset_index(drop=True)

    # 2. Blank summary on 2 records
    blank_indices = [0, 1]
    blanked_paper_ids = []
    for idx in blank_indices:
        if idx < len(corrupted_df):
            corrupted_df.loc[idx, "summary"] = ""
            corrupted_df.loc[idx, "summary_chars"] = 0
            blanked_paper_ids.append(corrupted_df.loc[idx, "paper_id"])

    # 3. Inject noise into summary on 2 records
    noise_token = "[CORRUPTED_NOISE_TOKEN_7749_GARBAGE_DATA_STREAM_ERROR_404_NULL_BYTE]"
    noise_indices = [2, 3]
    noise_paper_ids = []
    for idx in noise_indices:
        if idx < len(corrupted_df):
            curr_summary = str(corrupted_df.loc[idx, "summary"])
            corrupted_df.loc[idx, "summary"] = f"{noise_token} {curr_summary} {noise_token}"
            noise_paper_ids.append(corrupted_df.loc[idx, "paper_id"])

    # 4. Truncate title to < 8 chars on 2 records
    truncate_indices = [4, 5]
    truncated_paper_ids = []
    for idx in truncate_indices:
        if idx < len(corrupted_df):
            curr_title = str(corrupted_df.loc[idx, "title"])
            truncated_title = curr_title[:5] if len(curr_title) >= 5 else "Trunc"
            corrupted_df.loc[idx, "title"] = truncated_title
            truncated_paper_ids.append(corrupted_df.loc[idx, "paper_id"])

    # 5. Stale date: shift published date back 365 days for 8 records (> 25% of dataset)
    stale_count = 8
    stale_indices = list(range(len(corrupted_df) - stale_count, len(corrupted_df)))
    staled_paper_ids = []
    for idx in stale_indices:
        if 0 <= idx < len(corrupted_df):
            curr_pub = str(corrupted_df.loc[idx, "published"])
            try:
                pub_date = datetime.strptime(curr_pub[:10], "%Y-%m-%d").date()
                new_pub_date = pub_date - pd.Timedelta(days=365)
                corrupted_df.loc[idx, "published"] = new_pub_date.strftime("%Y-%m-%d")
                corrupted_df.loc[idx, "updated"] = new_pub_date.strftime("%Y-%m-%d")
                corrupted_df.loc[idx, "age_days"] = int(corrupted_df.loc[idx, "age_days"]) + 365
            except Exception:
                corrupted_df.loc[idx, "published"] = "2024-01-01"
                corrupted_df.loc[idx, "age_days"] = 900
            staled_paper_ids.append(corrupted_df.loc[idx, "paper_id"])

    # 6. Duplicate rows: pick 2 rows and append to create duplicate paper_ids
    dup_indices = [0, 1]
    dup_rows = corrupted_df.iloc[dup_indices].copy()
    duplicated_paper_ids = dup_rows["paper_id"].tolist()
    corrupted_df = pd.concat([corrupted_df, dup_rows], ignore_index=True)

    # 7. Rebuild helper columns and text_for_embedding
    for idx, row in corrupted_df.iterrows():
        authors = row["authors"]
        categories = row["categories"]
        authors_joined = ", ".join(authors) if isinstance(authors, list) else str(authors)
        categories_joined = ", ".join(categories) if isinstance(categories, list) else str(categories)
        summary = str(row["summary"])
        title = str(row["title"])
        published = str(row["published"])

        text_for_embedding = (
            f"Title: {title}\n"
            f"Authors: {authors_joined}\n"
            f"Published: {published}\n"
            f"Categories: {categories_joined}\n"
            f"Summary: {summary}"
        )
        corrupted_df.loc[idx, "authors_joined"] = authors_joined
        corrupted_df.loc[idx, "categories_joined"] = categories_joined
        corrupted_df.loc[idx, "summary_chars"] = len(summary)
        corrupted_df.loc[idx, "text_for_embedding"] = text_for_embedding

    # 8. Record corruption log
    log_data: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "original_rows": len(df),
        "corrupted_rows": len(corrupted_df),
        "scenarios": [
            {
                "scenario": "drop_latest_records",
                "description": "Bỏ rơi 20% các bài báo mới nhất dựa trên published date",
                "count": len(dropped_paper_ids),
                "affected_paper_ids": dropped_paper_ids,
                "parameters": {"drop_ratio": drop_ratio, "dropped_count": drop_count},
                "expected_quality_signal": "Giảm retrieval hit rate và token F1 đối với các truy vấn về bài báo mới nhất.",
            },
            {
                "scenario": "blank_summary",
                "description": "Xóa trắng phần tóm tắt ở một số dòng",
                "count": len(blanked_paper_ids),
                "affected_paper_ids": blanked_paper_ids,
                "parameters": {"blanked_count": len(blanked_paper_ids)},
                "expected_quality_signal": "Vi phạm Great Expectations ExpectColumnValueLengthsToBeBetween(min_value=30).",
            },
            {
                "scenario": "inject_noise",
                "description": "Chèn chuỗi ký tự rác vào tóm tắt",
                "count": len(noise_paper_ids),
                "affected_paper_ids": noise_paper_ids,
                "parameters": {"noise_token": noise_token},
                "expected_quality_signal": "Gây nhiễu embedding và suy giảm chất lượng câu trả lời của RAG Agent.",
            },
            {
                "scenario": "truncate_title",
                "description": "Cắt ngắn tiêu đề bài báo xuống dưới 8 ký tự",
                "count": len(truncated_paper_ids),
                "affected_paper_ids": truncated_paper_ids,
                "parameters": {"max_length": 5},
                "expected_quality_signal": "Mất thông tin tiêu đề, làm sai lệch kết quả tìm kiếm ngữ nghĩa theo tiêu đề.",
            },
            {
                "scenario": "stale_date",
                "description": "Lùi ngày xuất bản về 365 ngày trước đối với các bài báo",
                "count": len(staled_paper_ids),
                "affected_paper_ids": staled_paper_ids,
                "parameters": {"days_subtracted": 365, "stale_count": len(staled_paper_ids)},
                "expected_quality_signal": "Vi phạm Freshness SLA (tỷ lệ bài báo age_days > 180 vượt ngưỡng 25%, is_fresh=False).",
            },
            {
                "scenario": "duplicate_rows",
                "description": "Nhân đôi các dòng để tạo trùng lặp",
                "count": len(duplicated_paper_ids),
                "affected_paper_ids": duplicated_paper_ids,
                "parameters": {"duplicated_count": len(duplicated_paper_ids)},
                "expected_quality_signal": "Vi phạm Great Expectations ExpectColumnValuesToBeUnique(column='paper_id').",
            },
        ],
        "total_affected_scenarios": 6,
    }

    if output_log_path:
        target_path = Path(output_log_path)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(
            json.dumps(log_data, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    return corrupted_df

