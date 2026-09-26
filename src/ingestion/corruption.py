from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from core.utils import write_csv, write_json


def _format_text_for_embedding(row: pd.Series | dict[str, Any]) -> str:
    """Helper tái tạo chuỗi text_for_embedding đồng bộ với các trường metadata."""
    title = str(row.get("title", "") or "").strip()
    authors = str(row.get("authors_joined", "") or "").strip()
    published = str(row.get("published", "") or "").strip()
    categories = str(row.get("categories_joined", "") or "").strip()
    summary = str(row.get("summary", "") or "").strip()

    return (
        f"Title: {title}\n"
        f"Authors: {authors}\n"
        f"Published: {published}\n"
        f"Categories: {categories}\n"
        f"Summary: {summary}"
    )


def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path: Path | str) -> pd.DataFrame:
    """Giả lập 6 dạng sự cố dữ liệu thực tế trên DataFrame sạch:
    1. Drop latest records: Bỏ rơi 20% bài báo mới nhất.
    2. Blank summary: Xóa trắng phần tóm tắt ở một số dòng.
    3. Inject noise: Chèn chuỗi ký tự rác vào phần tóm tắt.
    4. Truncate title: Cắt ngắn tiêu đề xuống dưới 8 ký tự ("Draft").
    5. Stale date: Lùi ngày xuất bản về 365 ngày trước (kích hoạt Stale Alert).
    6. Duplicate rows: Nhân đôi các dòng để tạo trùng lặp khóa chính paper_id.

    Tái tạo lại cột `text_for_embedding` và ghi lại audit log vào `output_log_path`.
    """
    if df.empty:
        log_payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "initial_rows": 0,
            "corrupted_rows": 0,
            "corruptions": {},
        }
        write_json(Path(output_log_path), log_payload)
        return df.copy()

    # Sắp xếp theo ngày xuất bản giảm dần để xác định chính xác các bài mới nhất
    corrupted = df.copy()
    if "published" in corrupted.columns:
        corrupted = corrupted.sort_values(by="published", ascending=False).reset_index(drop=True)

    total_initial = len(corrupted)

    # 1. Drop latest records: 20% các bài mới nhất (với 24 bài -> 4 bài)
    drop_count = max(1, int(total_initial * 0.2))
    dropped_records = corrupted.iloc[:drop_count].to_dict(orient="records")

    # Giữ lại các bài còn lại (ví dụ 24 - 4 = 20 bài)
    corrupted = corrupted.iloc[drop_count:].copy().reset_index(drop=True)

    # 2. Blank summary: Xóa trắng summary ở 2 dòng đầu (index 0, 1)
    blank_summary_records = []
    for idx in range(min(2, len(corrupted))):
        paper_id = str(corrupted.at[idx, "paper_id"])
        blank_summary_records.append(
            {
                "paper_id": paper_id,
                "title": str(corrupted.at[idx, "title"]),
                "original_summary_len": len(str(corrupted.at[idx, "summary"] or "")),
            }
        )
        corrupted.at[idx, "summary"] = ""

    # 3. Inject noise: Chèn chuỗi ký tự rác vào tóm tắt ở 2 dòng tiếp theo (index 2, 3)
    injected_noise_records = []
    noise_payload = " [DATA_CORRUPTION_NOISE_###_MALFORMED_PAYLOAD_UNREADABLE_OBSERVABILITY_TRIGGER]"
    for idx in range(2, min(4, len(corrupted))):
        paper_id = str(corrupted.at[idx, "paper_id"])
        original_summary = str(corrupted.at[idx, "summary"] or "")
        corrupted.at[idx, "summary"] = original_summary + noise_payload
        injected_noise_records.append(
            {
                "paper_id": paper_id,
                "title": str(corrupted.at[idx, "title"]),
                "injected_noise": noise_payload.strip(),
            }
        )

    # 4. Truncate title: Cắt ngắn tiêu đề xuống dưới 8 ký tự ("Draft") ở 2 dòng (index 4, 5)
    truncated_title_records = []
    for idx in range(4, min(6, len(corrupted))):
        paper_id = str(corrupted.at[idx, "paper_id"])
        original_title = str(corrupted.at[idx, "title"])
        corrupted.at[idx, "title"] = "Draft"
        truncated_title_records.append(
            {
                "paper_id": paper_id,
                "original_title": original_title,
                "corrupted_title": "Draft",
            }
        )

    # 5. Stale date: Lùi ngày xuất bản về 365 ngày trước ở 6 dòng (index 6..11) để tỷ lệ stale > 25%
    stale_date_records = []
    for idx in range(6, min(12, len(corrupted))):
        paper_id = str(corrupted.at[idx, "paper_id"])
        orig_published = str(corrupted.at[idx, "published"])
        try:
            pub_date = datetime.strptime(orig_published[:10], "%Y-%m-%d").date()
            new_pub_date = pub_date - timedelta(days=365)
            new_published_str = new_pub_date.isoformat()
        except Exception:
            new_published_str = "2025-01-01"

        corrupted.at[idx, "published"] = new_published_str
        if "age_days" in corrupted.columns:
            corrupted.at[idx, "age_days"] = int(corrupted.at[idx, "age_days"]) + 365

        stale_date_records.append(
            {
                "paper_id": paper_id,
                "original_published": orig_published,
                "corrupted_published": new_published_str,
                "age_days": int(corrupted.at[idx, "age_days"]) if "age_days" in corrupted.columns else None,
            }
        )

    # 6. Duplicate rows: Nhân đôi 2 dòng (index 12, 13) để tạo trùng lặp khóa chính
    duplicated_records = []
    dup_indices = list(range(12, min(14, len(corrupted))))
    if dup_indices:
        dup_rows = corrupted.iloc[dup_indices].copy()
        for _, row in dup_rows.iterrows():
            duplicated_records.append(
                {
                    "paper_id": str(row.get("paper_id")),
                    "title": str(row.get("title")),
                }
            )
        corrupted = pd.concat([corrupted, dup_rows], ignore_index=True)

    # 7. Đồng bộ hóa text_for_embedding và summary_chars
    corrupted["text_for_embedding"] = corrupted.apply(_format_text_for_embedding, axis=1)
    if "summary_chars" in corrupted.columns:
        corrupted["summary_chars"] = corrupted["summary"].apply(lambda s: len(str(s or "")))

    # 8. Ghi nhật ký chi tiết vào corruption_log.json
    log_path = Path(output_log_path)
    log_payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "initial_rows": total_initial,
        "corrupted_rows": len(corrupted),
        "summary": {
            "dropped_latest_count": len(dropped_records),
            "blank_summary_count": len(blank_summary_records),
            "injected_noise_count": len(injected_noise_records),
            "truncated_title_count": len(truncated_title_records),
            "stale_date_count": len(stale_date_records),
            "duplicated_count": len(duplicated_records),
        },
        "dropped_latest_records": dropped_records,
        "blank_summary_records": blank_summary_records,
        "injected_noise_records": injected_noise_records,
        "truncated_title_records": truncated_title_records,
        "stale_date_records": stale_date_records,
        "duplicated_records": duplicated_records,
    }
    write_json(log_path, log_payload)

    # Tự động xuất sẵn các file corrupted clean nếu thư mục clean tồn tại
    try:
        clean_dir = log_path.parent.parent / "clean"
        if clean_dir.exists():
            write_json(clean_dir / "papers_clean_corrupted.json", corrupted.to_dict(orient="records"))
            write_csv(corrupted, clean_dir / "papers_clean_corrupted.csv")
    except Exception:
        pass

    return corrupted
