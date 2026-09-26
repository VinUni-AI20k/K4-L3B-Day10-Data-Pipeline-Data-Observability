from __future__ import annotations

from datetime import timedelta

import pandas as pd

from core.utils import write_json

NOISE_STRING = " ###CORRUPTED_NOISE_$$$ "


def _rebuild_text_for_embedding(row: pd.Series) -> str:
    return (
        f"Title: {row['title']}\n"
        f"Authors: {row['authors_joined']}\n"
        f"Published: {row['published']}\n"
        f"Categories: {row['categories_joined']}\n"
        f"Summary: {row['summary']}"
    )


def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path) -> pd.DataFrame:
    """Simulate nhieu dang data corruption tren clean dataframe."""
    corrupted = df.sort_values(by="published", ascending=False).reset_index(drop=True)
    log: dict[str, list[str]] = {
        "dropped_latest": [],
        "blanked_summary": [],
        "noise_injected": [],
        "truncated_title": [],
        "stale_date": [],
        "duplicated": [],
    }

    n = len(corrupted)

    # 1. Drop latest 20% of records.
    drop_count = max(1, int(n * 0.2))
    dropped_ids = corrupted.iloc[:drop_count]["paper_id"].tolist()
    log["dropped_latest"] = dropped_ids
    corrupted = corrupted.iloc[drop_count:].reset_index(drop=True)
    n = len(corrupted)

    # 2. Blank summary on some rows.
    blank_count = max(1, int(n * 0.15))
    blank_idx = corrupted.index[:blank_count]
    log["blanked_summary"] = corrupted.loc[blank_idx, "paper_id"].tolist()
    corrupted.loc[blank_idx, "summary"] = ""

    # 3. Inject noise into summary text.
    noise_idx = corrupted.index[blank_count : blank_count + max(1, int(n * 0.15))]
    log["noise_injected"] = corrupted.loc[noise_idx, "paper_id"].tolist()
    corrupted.loc[noise_idx, "summary"] = corrupted.loc[noise_idx, "summary"] + NOISE_STRING

    # 4. Truncate titles below 8 characters.
    truncate_idx = corrupted.index[: max(1, int(n * 0.15))]
    log["truncated_title"] = corrupted.loc[truncate_idx, "paper_id"].tolist()
    corrupted.loc[truncate_idx, "title"] = corrupted.loc[truncate_idx, "title"].str.slice(0, 6)

    # 5. Push published date back by 365 days (stale).
    stale_idx = corrupted.index[: max(1, int(n * 0.2))]
    log["stale_date"] = corrupted.loc[stale_idx, "paper_id"].tolist()
    stale_dates = pd.to_datetime(corrupted.loc[stale_idx, "published"], errors="coerce") - timedelta(days=365)
    corrupted.loc[stale_idx, "published"] = stale_dates.dt.strftime("%Y-%m-%d")
    corrupted.loc[stale_idx, "age_days"] = corrupted.loc[stale_idx, "age_days"] + 365

    # 6. Duplicate some rows.
    dup_count = max(1, int(n * 0.15))
    duplicate_rows = corrupted.iloc[:dup_count].copy()
    log["duplicated"] = duplicate_rows["paper_id"].tolist()
    corrupted = pd.concat([corrupted, duplicate_rows], ignore_index=True)

    # 7. Rebuild text_for_embedding and summary_chars after edits.
    corrupted["summary_chars"] = corrupted["summary"].str.len()
    corrupted["text_for_embedding"] = corrupted.apply(_rebuild_text_for_embedding, axis=1)

    write_json(output_log_path, log)
    return corrupted
