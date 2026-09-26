from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


def corrupt_clean_dataframe(
    clean_df: pd.DataFrame | None = None,
    log_path: str | Path | None = None,
    *,
    df: pd.DataFrame | None = None,
    output_log_path: str | Path | None = None,
    seed: int = 42,
) -> pd.DataFrame:
    """Giả lập 6 dạng sự cố dữ liệu thực tế (Data Corruption Suite) trên Clean DataFrame.

    Các dạng lỗi thực hiện tuần tự:
    1. Drop latest records: Sắp xếp theo published giảm dần, cắt bỏ 20% bản ghi mới nhất.
    2. Blank summary: Chọn ngẫu nhiên 10% số dòng còn lại, xóa trắng summary ("").
    3. Inject noise: Chọn ngẫu nhiên 10% số dòng khác, chèn chuỗi ký tự rác vào cuối summary.
    4. Truncate title: Chọn ngẫu nhiên 10% số dòng khác, cắt ngắn title còn 7 ký tự đầu.
    5. Stale date: Chọn ngẫu nhiên 10% số dòng, trừ 365 ngày (published) và cộng 365 ngày (age_days).
    6. Duplicate rows: Chọn ngẫu nhiên 5 dòng, nhân đôi và nối thêm vào cuối DataFrame.

    Sau khi tiêm lỗi:
    - Cập nhật lại cột `summary_chars` và tái cấu trúc `text_for_embedding` theo chuẩn multiline 5 trường.
    - Xuất nhật ký `corruption_log` ra file JSON tại `log_path`.

    Args:
        clean_df: DataFrame sạch đầu vào (baseline).
        log_path: Đường dẫn lưu file corruption_log.json.
        df: Alias cho clean_df nếu được gọi theo tên cũ.
        output_log_path: Alias cho log_path nếu được gọi theo tên cũ.
        seed: Random seed để đảm bảo tính tái lập (mặc định: 42).

    Returns:
        pd.DataFrame: DataFrame mới đã bị làm bẩn (không làm biến đổi DataFrame gốc).
    """
    # Đồng bộ hóa tham số gọi hàm
    source_df = clean_df if clean_df is not None else df
    target_log_path = log_path if log_path is not None else output_log_path

    if source_df is None or source_df.empty:
        return pd.DataFrame()

    # Thiết lập random seed để kết quả tái lập hoàn toàn
    np.random.seed(seed)

    # 0. Tạo bản sao độc lập, tuyệt đối không sửa trực tiếp trên DataFrame gốc
    corrupted_df = source_df.copy()

    # Khởi tạo dictionary corruption_log để theo dõi chi tiết từng lỗi
    corruption_log: dict[str, Any] = {
        "metadata": {
            "initial_rows": len(source_df),
            "random_seed": seed,
        },
        "drop_latest_records": {
            "count": 0,
            "paper_ids": [],
        },
        "blank_summary": {
            "count": 0,
            "paper_ids": [],
        },
        "inject_noise": {
            "count": 0,
            "paper_ids": [],
        },
        "truncate_title": {
            "count": 0,
            "paper_ids": [],
        },
        "stale_date": {
            "count": 0,
            "paper_ids": [],
        },
        "duplicate_rows": {
            "count": 0,
            "paper_ids": [],
        },
    }

    # =========================================================================
    # Lỗi 1: Drop latest records (cắt bỏ 20% số dòng mới nhất theo published)
    # =========================================================================
    if "published" in corrupted_df.columns and len(corrupted_df) > 0:
        # Chuyển đổi tạm để sắp xếp chính xác theo thời gian giảm dần
        temp_pub = pd.to_datetime(corrupted_df["published"], errors="coerce")
        sorted_indices = temp_pub.sort_values(ascending=False).index
        corrupted_df = corrupted_df.loc[sorted_indices].reset_index(drop=True)

        n_drop = int(len(corrupted_df) * 0.20)
        if n_drop > 0:
            dropped_rows = corrupted_df.iloc[:n_drop]
            dropped_ids = (
                dropped_rows["paper_id"].tolist() if "paper_id" in dropped_rows.columns else []
            )
            corrupted_df = corrupted_df.iloc[n_drop:].reset_index(drop=True)

            corruption_log["drop_latest_records"]["count"] = len(dropped_ids)
            corruption_log["drop_latest_records"]["paper_ids"] = dropped_ids

    total_remaining = len(corrupted_df)
    if total_remaining == 0:
        return corrupted_df

    # =========================================================================
    # Lỗi 2: Blank summary (chọn ngẫu nhiên 10% số dòng còn lại, xóa trắng summary)
    # =========================================================================
    n_blank = max(1, int(total_remaining * 0.10)) if total_remaining >= 10 else min(1, total_remaining)
    blank_indices = np.random.choice(corrupted_df.index, size=n_blank, replace=False).tolist()

    if "summary" in corrupted_df.columns:
        corrupted_df.loc[blank_indices, "summary"] = ""

    blank_ids = (
        corrupted_df.loc[blank_indices, "paper_id"].tolist()
        if "paper_id" in corrupted_df.columns
        else []
    )
    corruption_log["blank_summary"]["count"] = len(blank_ids)
    corruption_log["blank_summary"]["paper_ids"] = blank_ids

    # =========================================================================
    # Lỗi 3: Inject noise (chọn ngẫu nhiên 10% số dòng khác, chèn rác vào summary)
    # =========================================================================
    available_for_noise = [idx for idx in corrupted_df.index if idx not in blank_indices]
    n_noise = max(1, int(total_remaining * 0.10))
    if len(available_for_noise) >= n_noise:
        noise_indices = np.random.choice(available_for_noise, size=n_noise, replace=False).tolist()
    else:
        noise_indices = available_for_noise

    noise_token = " <ERR_500_NULL>!@#%^&*"
    if "summary" in corrupted_df.columns and noise_indices:
        corrupted_df.loc[noise_indices, "summary"] = (
            corrupted_df.loc[noise_indices, "summary"].fillna("").astype(str) + noise_token
        )

    noise_ids = (
        corrupted_df.loc[noise_indices, "paper_id"].tolist()
        if "paper_id" in corrupted_df.columns
        else []
    )
    corruption_log["inject_noise"]["count"] = len(noise_ids)
    corruption_log["inject_noise"]["paper_ids"] = noise_ids

    # =========================================================================
    # Lỗi 4: Truncate title (chọn ngẫu nhiên 10% số dòng khác, cắt ngắn title <= 7 ký tự)
    # =========================================================================
    # Ưu tiên các dòng chưa bị làm trắng summary để lỗi phân bổ đều
    available_for_trunc = [idx for idx in corrupted_df.index if idx not in blank_indices]
    n_trunc = max(1, int(total_remaining * 0.10))
    if len(available_for_trunc) >= n_trunc:
        trunc_indices = np.random.choice(available_for_trunc, size=n_trunc, replace=False).tolist()
    else:
        trunc_indices = np.random.choice(corrupted_df.index, size=n_trunc, replace=False).tolist()

    if "title" in corrupted_df.columns and trunc_indices:
        corrupted_df.loc[trunc_indices, "title"] = (
            corrupted_df.loc[trunc_indices, "title"].fillna("").astype(str).str[:7]
        )

    trunc_ids = (
        corrupted_df.loc[trunc_indices, "paper_id"].tolist()
        if "paper_id" in corrupted_df.columns
        else []
    )
    corruption_log["truncate_title"]["count"] = len(trunc_ids)
    corruption_log["truncate_title"]["paper_ids"] = trunc_ids

    # =========================================================================
    # Lỗi 5: Stale date (chọn ngẫu nhiên 10% số dòng, trừ 365 ngày và đồng bộ age_days)
    # =========================================================================
    n_stale = max(1, int(total_remaining * 0.10))
    stale_indices = np.random.choice(corrupted_df.index, size=n_stale, replace=False).tolist()

    if "published" in corrupted_df.columns and stale_indices:
        pub_series = pd.to_datetime(corrupted_df.loc[stale_indices, "published"], errors="coerce")
        new_dates = pub_series - pd.Timedelta(days=365)
        if pd.api.types.is_datetime64_any_dtype(corrupted_df["published"]):
            corrupted_df.loc[stale_indices, "published"] = new_dates
        else:
            corrupted_df.loc[stale_indices, "published"] = new_dates.dt.strftime("%Y-%m-%d").astype(str)

    if "age_days" in corrupted_df.columns and stale_indices:
        corrupted_df.loc[stale_indices, "age_days"] = (
            corrupted_df.loc[stale_indices, "age_days"].fillna(0) + 365
        )

    stale_ids = (
        corrupted_df.loc[stale_indices, "paper_id"].tolist()
        if "paper_id" in corrupted_df.columns
        else []
    )
    corruption_log["stale_date"]["count"] = len(stale_ids)
    corruption_log["stale_date"]["paper_ids"] = stale_ids

    # =========================================================================
    # Lỗi 6: Duplicate rows (lấy ngẫu nhiên 5 dòng, nhân đôi và concat vào cuối DataFrame)
    # =========================================================================
    n_dup = min(5, len(corrupted_df))
    if n_dup > 0:
        dup_indices = np.random.choice(corrupted_df.index, size=n_dup, replace=False).tolist()
        duplicates = corrupted_df.loc[dup_indices].copy()
        dup_ids = (
            duplicates["paper_id"].tolist() if "paper_id" in duplicates.columns else []
        )
        corrupted_df = pd.concat([corrupted_df, duplicates], ignore_index=True)

        corruption_log["duplicate_rows"]["count"] = len(dup_ids)
        corruption_log["duplicate_rows"]["paper_ids"] = dup_ids

    # =========================================================================
    # 7. Cập nhật lại các trường phái sinh và tái tạo chuỗi text_for_embedding
    # =========================================================================
    if "summary" in corrupted_df.columns:
        corrupted_df["summary_chars"] = corrupted_df["summary"].fillna("").astype(str).str.len()

    if "published" in corrupted_df.columns:
        published_str = (
            pd.to_datetime(corrupted_df["published"], errors="coerce")
            .dt.strftime("%Y-%m-%d")
            .fillna("")
        )
    else:
        published_str = pd.Series([""] * len(corrupted_df), index=corrupted_df.index)

    corrupted_df["text_for_embedding"] = (
        "Title: " + corrupted_df["title"].fillna("").astype(str) + "\n"
        + "Authors: " + corrupted_df["authors"].fillna("").astype(str) + "\n"
        + "Published: " + published_str + "\n"
        + "Categories: " + corrupted_df["categories"].fillna("").astype(str) + "\n"
        + "Summary: " + corrupted_df["summary"].fillna("").astype(str)
    )

    # =========================================================================
    # 8. Lưu trữ nhật ký corruption_log ra file JSON
    # =========================================================================
    corruption_log["metadata"]["final_rows"] = len(corrupted_df)

    if target_log_path:
        out_path = Path(target_log_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(corruption_log, f, indent=2, ensure_ascii=False)

    return corrupted_df
