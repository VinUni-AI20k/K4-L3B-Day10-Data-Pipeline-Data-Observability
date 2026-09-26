from __future__ import annotations

import json
from pathlib import Path
from typing import Any
import pandas as pd


def _rebuild_text_for_embedding(row: pd.Series) -> str:
    """Tái tạo cột text_for_embedding khớp định dạng chuẩn của Bước 3."""
    title = str(row.get("title", "")).strip()
    authors = str(row.get("authors_joined", "")).strip()
    categories = str(row.get("categories_joined", "")).strip()
    summary = str(row.get("summary", "")).strip()

    return (
        f"Title: {title}\n"
        f"Authors: {authors}\n"
        f"Categories: {categories}\n"
        f"Summary: {summary}"
    )


def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path: str | Path) -> pd.DataFrame:
    """Giả lập 6 dạng sự cố dữ liệu thực nghiệm và ghi nhật ký chi tiết."""
    if df.empty:
        return df.copy()

    corrupted_df = df.copy()
    logs: list[dict[str, Any]] = []

    # Đảm bảo cột published là kiểu datetime để tính toán
    if not pd.api.types.is_datetime64_any_dtype(corrupted_df["published"]):
        corrupted_df["published"] = pd.to_datetime(corrupted_df["published"], errors="coerce")

    # 1. Drop latest records: Bỏ rơi 20% các bài báo mới nhất
    corrupted_df = corrupted_df.sort_values(by="published", ascending=False).reset_index(drop=True)
    num_to_drop = max(1, int(len(corrupted_df) * 0.20))
    dropped_rows = corrupted_df.iloc[:num_to_drop]

    for _, row in dropped_rows.iterrows():
        logs.append({
            "corruption_type": "drop_latest_records",
            "paper_id": row["paper_id"],
            "details": f"Dropped latest record published at {row['published']}",
        })

    corrupted_df = corrupted_df.iloc[num_to_drop:].reset_index(drop=True)

    # 2. Blank summary: Xóa trắng phần tóm tắt ở một số dòng (dòng đầu tiên)
    if len(corrupted_df) > 0:
        idx_blank = 0
        old_summary = corrupted_df.at[idx_blank, "summary"]
        corrupted_df.at[idx_blank, "summary"] = ""
        logs.append({
            "corruption_type": "blank_summary",
            "paper_id": corrupted_df.at[idx_blank, "paper_id"],
            "before": old_summary,
            "after": "",
        })

    # 3. Inject noise: Chèn các chuỗi ký tự rác vào summary
    if len(corrupted_df) > 1:
        idx_noise = 1
        noise = " [CORRUPTED_NOISE_#@!$%_GARBAGE_TEXT] "
        old_summary = str(corrupted_df.at[idx_noise, "summary"])
        new_summary = noise + old_summary
        corrupted_df.at[idx_noise, "summary"] = new_summary
        logs.append({
            "corruption_type": "inject_noise",
            "paper_id": corrupted_df.at[idx_noise, "paper_id"],
            "before": old_summary,
            "after": new_summary,
        })

    # 4. Truncate title: Cắt ngắn tiêu đề xuống dưới 8 ký tự
    if len(corrupted_df) > 2:
        idx_trunc = 2
        old_title = str(corrupted_df.at[idx_trunc, "title"])
        new_title = old_title[:6]
        corrupted_df.at[idx_trunc, "title"] = new_title
        logs.append({
            "corruption_type": "truncate_title",
            "paper_id": corrupted_df.at[idx_trunc, "paper_id"],
            "before": old_title,
            "after": new_title,
        })

    # 5. Stale date: Lùi ngày xuất bản về 365 ngày trước
    if len(corrupted_df) > 3:
        idx_stale = 3
        old_date = corrupted_df.at[idx_stale, "published"]
        new_date = old_date - pd.Timedelta(days=365)
        corrupted_df.at[idx_stale, "published"] = new_date
        if "age_days" in corrupted_df.columns:
            corrupted_df.at[idx_stale, "age_days"] = int(corrupted_df.at[idx_stale, "age_days"]) + 365
        logs.append({
            "corruption_type": "stale_date",
            "paper_id": corrupted_df.at[idx_stale, "paper_id"],
            "before": str(old_date),
            "after": str(new_date),
        })

    # 6. Add duplicate rows: Nhân đôi các dòng để tạo trùng lặp
    if len(corrupted_df) > 4:
        dup_row = corrupted_df.iloc[[4]].copy()
        corrupted_df = pd.concat([corrupted_df, dup_row], ignore_index=True)
        logs.append({
            "corruption_type": "duplicate_rows",
            "paper_id": dup_row.iloc[0]["paper_id"],
            "details": "Duplicated row added back into dataframe",
        })

    # 7. Rebuild text_for_embedding và summary_chars
    if "summary_chars" in corrupted_df.columns:
        corrupted_df["summary_chars"] = corrupted_df["summary"].astype(str).str.len()
    corrupted_df["text_for_embedding"] = corrupted_df.apply(_rebuild_text_for_embedding, axis=1)

    # 8. Ghi file nhật ký lỗi (corruption log)
    output_log_path = Path(output_log_path)
    output_log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_log_path, "w", encoding="utf-8") as f:
        json.dump(logs, f, ensure_ascii=False, indent=2, default=str)

    return corrupted_df