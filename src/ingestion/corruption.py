from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from core.utils import write_json


def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path: Path | str) -> pd.DataFrame:
    """Simulate 6 kịch bản data corruption trong production."""
    corrupted = df.copy()
    corruption_log: dict[str, Any] = {"scenarios": [], "initial_rows": len(df)}

    # 1. Drop mot so latest records (20% bản ghi mới nhất)
    n_drop = max(1, int(len(corrupted) * 0.20))
    dropped_ids = corrupted.iloc[:n_drop]["paper_id"].tolist()
    corrupted = corrupted.iloc[n_drop:].copy().reset_index(drop=True)
    corruption_log["scenarios"].append(
        {"name": "drop_latest_records", "dropped_count": n_drop, "paper_ids": dropped_ids}
    )

    # 2. Blank summary o 3 dong
    blank_indices = [0, 1, 2]
    blank_ids = []
    for idx in blank_indices:
        if idx < len(corrupted):
            corrupted.loc[idx, "summary"] = ""
            corrupted.loc[idx, "summary_chars"] = 0
            blank_ids.append(corrupted.loc[idx, "paper_id"])
    corruption_log["scenarios"].append(
        {"name": "blank_summary", "affected_count": len(blank_ids), "paper_ids": blank_ids}
    )

    # 3. Inject noise vao text (3 dong tiep theo)
    noise_indices = [3, 4, 5]
    noise_ids = []
    noise_payload = " [ERR_CORRUPT_NULL_BYTE_GARBAGE_NOISE_###] "
    for idx in noise_indices:
        if idx < len(corrupted):
            current_summary = str(corrupted.loc[idx, "summary"])
            corrupted.loc[idx, "summary"] = noise_payload * 3 + current_summary
            corrupted.loc[idx, "summary_chars"] = len(corrupted.loc[idx, "summary"])
            noise_ids.append(corrupted.loc[idx, "paper_id"])
    corruption_log["scenarios"].append(
        {"name": "inject_noise", "affected_count": len(noise_ids), "paper_ids": noise_ids}
    )

    # 4. Lam title bi truncate (< 8 ky tu)
    trunc_indices = [6, 7]
    trunc_ids = []
    for idx in trunc_indices:
        if idx < len(corrupted):
            corrupted.loc[idx, "title"] = str(corrupted.loc[idx, "title"])[:5]
            trunc_ids.append(corrupted.loc[idx, "paper_id"])
    corruption_log["scenarios"].append(
        {"name": "truncate_title", "affected_count": len(trunc_ids), "paper_ids": trunc_ids}
    )

    # 5. Lam published date cu di de vi pham Freshness SLA (> 180 ngay)
    stale_count = max(7, int(len(corrupted) * 0.40))
    stale_ids = []
    for idx in range(min(stale_count, len(corrupted))):
        corrupted.loc[idx, "published"] = "2020-01-01"
        corrupted.loc[idx, "age_days"] = 2400
        stale_ids.append(corrupted.loc[idx, "paper_id"])
    corruption_log["scenarios"].append(
        {"name": "stale_date", "affected_count": len(stale_ids), "paper_ids": stale_ids}
    )

    # 6. Add duplicate rows (nhan ban 3 dong)
    dup_rows = corrupted.iloc[:3].copy()
    dup_ids = dup_rows["paper_id"].tolist()
    corrupted = pd.concat([corrupted, dup_rows], ignore_index=True)
    corruption_log["scenarios"].append(
        {"name": "duplicate_rows", "duplicated_count": len(dup_rows), "paper_ids": dup_ids}
    )

    # 7. Rebuild text_for_embedding cho toan bo cac dong da bien doi
    corrupted["text_for_embedding"] = (
        "Title: " + corrupted["title"].astype(str) + "\n"
        + "Authors: " + corrupted["authors_joined"].astype(str) + "\n"
        + "Published Date: " + corrupted["published"].astype(str) + "\n"
        + "Categories: " + corrupted["categories_joined"].astype(str) + "\n"
        + "Summary: " + corrupted["summary"].astype(str)
    )

    corruption_log["final_rows"] = len(corrupted)

    # 8. Ghi corruption log
    write_json(Path(output_log_path), corruption_log)
    return corrupted

