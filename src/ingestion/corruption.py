from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import pandas as pd

from core.utils import write_csv, write_json

logger = logging.getLogger(__name__)


def drop_latest_records(df: pd.DataFrame, ratio: float = 0.2) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Kịch bản 1: Cắt bỏ ratio (20%) bản ghi mới nhất theo ngày xuất bản."""
    df_sorted = df.copy()
    if "published" in df_sorted.columns:
        df_sorted = df_sorted.sort_values(by="published", ascending=False).reset_index(drop=True)

    num_drop = max(1, int(len(df_sorted) * ratio))
    dropped_slice = df_sorted.iloc[:num_drop]
    remaining_df = df_sorted.iloc[num_drop:].reset_index(drop=True)

    dropped_ids = dropped_slice["paper_id"].tolist() if "paper_id" in dropped_slice.columns else []
    log = {
        "scenario": "drop_latest_records",
        "ratio": ratio,
        "dropped_count": num_drop,
        "dropped_paper_ids": dropped_ids,
    }
    return remaining_df, log


def blank_summary(df: pd.DataFrame, sample_ratio: float = 0.25) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Kịch bản 2: Xóa rỗng trường tóm tắt (summary = '') ở một số bản ghi."""
    df_corrupted = df.copy()
    num_blank = max(1, int(len(df_corrupted) * sample_ratio))
    target_indices = [i for i in range(0, len(df_corrupted), 4)][:num_blank]

    affected_ids = []
    for idx in target_indices:
        df_corrupted.at[idx, "summary"] = ""
        df_corrupted.at[idx, "summary_chars"] = 0
        if "paper_id" in df_corrupted.columns:
            affected_ids.append(df_corrupted.at[idx, "paper_id"])

    log = {
        "scenario": "blank_summary",
        "sample_ratio": sample_ratio,
        "affected_count": len(affected_ids),
        "affected_paper_ids": affected_ids,
    }
    return df_corrupted, log


def inject_noise(df: pd.DataFrame, sample_ratio: float = 0.25) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Kịch bản 3: Chèn chuỗi ký tự rác vào trường tóm tắt gây nhiễu embedding."""
    df_corrupted = df.copy()
    num_noise = max(1, int(len(df_corrupted) * sample_ratio))
    target_indices = [i for i in range(1, len(df_corrupted), 4)][:num_noise]

    noise_tag = "@@#$! CORRUPTED DATA !$%#@@ "
    affected_ids = []
    for idx in target_indices:
        current_summary = str(df_corrupted.at[idx, "summary"])
        df_corrupted.at[idx, "summary"] = noise_tag + current_summary
        df_corrupted.at[idx, "summary_chars"] = len(df_corrupted.at[idx, "summary"])
        if "paper_id" in df_corrupted.columns:
            affected_ids.append(df_corrupted.at[idx, "paper_id"])

    log = {
        "scenario": "inject_noise",
        "sample_ratio": sample_ratio,
        "noise_tag": noise_tag.strip(),
        "affected_count": len(affected_ids),
        "affected_paper_ids": affected_ids,
    }
    return df_corrupted, log


def truncate_title(df: pd.DataFrame, sample_ratio: float = 0.25) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Kịch bản 4: Cắt ngắn tiêu đề bài báo xuống dưới 8 ký tự vi phạm GX Expectation."""
    df_corrupted = df.copy()
    num_trunc = max(1, int(len(df_corrupted) * sample_ratio))
    target_indices = [i for i in range(2, len(df_corrupted), 4)][:num_trunc]

    affected_ids = []
    for idx in target_indices:
        current_title = str(df_corrupted.at[idx, "title"])
        truncated = current_title[:5] if len(current_title) >= 5 else "AI..."
        df_corrupted.at[idx, "title"] = truncated
        if "paper_id" in df_corrupted.columns:
            affected_ids.append(df_corrupted.at[idx, "paper_id"])

    log = {
        "scenario": "truncate_title",
        "sample_ratio": sample_ratio,
        "max_length": 5,
        "affected_count": len(affected_ids),
        "affected_paper_ids": affected_ids,
    }
    return df_corrupted, log


def stale_date(df: pd.DataFrame, sample_ratio: float = 0.3) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Kịch bản 5: Lùi ngày xuất bản về 10 năm trước để vi phạm Freshness SLA (>25% bài quá 180 ngày)."""
    df_corrupted = df.copy()
    num_stale = max(1, int(len(df_corrupted) * sample_ratio))
    target_indices = [i for i in range(3, len(df_corrupted), 3)][:num_stale]
    if len(target_indices) < num_stale:
        remaining = [i for i in range(len(df_corrupted)) if i not in target_indices]
        target_indices.extend(remaining[: num_stale - len(target_indices)])

    affected_ids = []
    for idx in target_indices:
        df_corrupted.at[idx, "published"] = "2016-01-01"
        df_corrupted.at[idx, "age_days"] = 3800
        if "paper_id" in df_corrupted.columns:
            affected_ids.append(df_corrupted.at[idx, "paper_id"])

    log = {
        "scenario": "stale_date",
        "sample_ratio": sample_ratio,
        "stale_published_date": "2016-01-01",
        "stale_age_days": 3800,
        "affected_count": len(affected_ids),
        "affected_paper_ids": affected_ids,
    }
    return df_corrupted, log


def duplicate_rows(df: pd.DataFrame, num_dups: int = 3) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Kịch bản 6: Nhân bản các dòng dữ liệu để vi phạm ràng buộc Uniqueness (paper_id)."""
    if len(df) == 0:
        return df, {"scenario": "duplicate_rows", "duplicated_count": 0, "duplicated_paper_ids": []}

    dup_slice = df.iloc[: min(num_dups, len(df))].copy()
    df_corrupted = pd.concat([df, dup_slice], ignore_index=True)
    dup_ids = dup_slice["paper_id"].tolist() if "paper_id" in dup_slice.columns else []

    log = {
        "scenario": "duplicate_rows",
        "duplicated_count": len(dup_slice),
        "duplicated_paper_ids": dup_ids,
    }
    return df_corrupted, log


def rebuild_text_for_embedding(df: pd.DataFrame) -> pd.DataFrame:
    """Tái cấu trúc lại trường text_for_embedding 5 phần phản ánh dữ liệu bẩn."""
    df_rebuilt = df.copy()
    texts = []
    for _, row in df_rebuilt.iterrows():
        title = str(row.get("title", "")).strip()
        authors_joined = str(row.get("authors_joined", "")).strip()
        categories_joined = str(row.get("categories_joined", "")).strip()
        published_str = str(row.get("published", "")).strip()
        summary = str(row.get("summary", "")).strip()

        text = (
            f"Title: {title}\n"
            f"Authors: {authors_joined}\n"
            f"Categories: {categories_joined}\n"
            f"Published Date: {published_str}\n"
            f"Summary: {summary}"
        ).strip()
        texts.append(text)

    df_rebuilt["text_for_embedding"] = texts
    return df_rebuilt


def corrupt_dataset(
    df: pd.DataFrame,
    settings: Any | None = None,
    output_log_path: Path | str | None = None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Tiêm đủ 6 kịch bản lỗi vào DataFrame, cập nhật text_for_embedding và lưu nhật ký lỗi."""
    logger.info("Bắt đầu tiêm 6 kịch bản lỗi vào dữ liệu sạch...")
    initial_count = len(df)

    # 1. Drop latest records
    cur_df, drop_log = drop_latest_records(df, ratio=0.2)

    # 2. Blank summary
    cur_df, blank_log = blank_summary(cur_df, sample_ratio=0.25)

    # 3. Inject noise
    cur_df, noise_log = inject_noise(cur_df, sample_ratio=0.25)

    # 4. Truncate title
    cur_df, trunc_log = truncate_title(cur_df, sample_ratio=0.25)

    # 5. Stale date (vi phạm Freshness SLA)
    cur_df, stale_log = stale_date(cur_df, sample_ratio=0.3)

    # 6. Duplicate rows (vi phạm Unique)
    cur_df, dup_log = duplicate_rows(cur_df, num_dups=3)

    # 7. Rebuild text_for_embedding
    cur_df = rebuild_text_for_embedding(cur_df)

    # Tổng hợp nhật ký lỗi
    corruption_log = {
        "drop_latest_records": drop_log,
        "blank_summary": blank_log,
        "inject_noise": noise_log,
        "truncate_title": trunc_log,
        "stale_date": stale_log,
        "duplicate_rows": dup_log,
        "records_before_corruption": initial_count,
        "records_after_corruption": len(cur_df),
    }

    # Xác định đường dẫn file log
    log_path: Path
    if output_log_path is not None:
        log_path = Path(output_log_path)
    elif settings is not None and hasattr(settings, "paths"):
        log_path = settings.paths.corruption_log
    else:
        log_path = Path("data/results/corruption_log.json")

    write_json(log_path, corruption_log)
    logger.info("Đã lưu corruption log vào %s", log_path)

    # Lưu dữ liệu corrupted nếu có cấu hình settings
    if settings is not None and hasattr(settings, "paths"):
        write_csv(cur_df, settings.paths.corrupted_clean_csv)
        write_json(settings.paths.corrupted_clean_json, cur_df.to_dict(orient="records"))
        logger.info("Đã lưu artifacts corrupted vào %s và %s", settings.paths.corrupted_clean_csv, settings.paths.corrupted_clean_json)

    return cur_df, corruption_log


def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path: Path | str | None = None) -> pd.DataFrame:
    """Wrapper cho phép gọi nhanh hàm tiêm lỗi và trả về DataFrame corrupted."""
    corrupted_df, _ = corrupt_dataset(df, output_log_path=output_log_path)
    return corrupted_df
