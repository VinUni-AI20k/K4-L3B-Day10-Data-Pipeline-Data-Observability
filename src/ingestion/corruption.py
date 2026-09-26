from __future__ import annotations

import json
from pathlib import Path
from typing import Any
import pandas as pd


def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path: Any) -> pd.DataFrame:
    """Inject 6 data corruption scenarios into clean DataFrame and log changes."""
    if df.empty:
        return df.copy()

    corrupted_df = df.copy()
    logs: list[dict[str, Any]] = []

    # 1. Drop latest records (drop 20% of newest records)
    drop_count = max(1, int(len(corrupted_df) * 0.2))
    dropped_ids = list(corrupted_df.tail(drop_count)["paper_id"])
    corrupted_df = corrupted_df.iloc[:-drop_count].copy()
    logs.append({
        "scenario": "drop_latest_records",
        "dropped_count": drop_count,
        "dropped_paper_ids": dropped_ids,
    })

    if corrupted_df.empty:
        corrupted_df = df.copy()

    # 2. Blank summary (clear summary for 2 rows)
    indices_to_blank = list(corrupted_df.index[:2])
    for idx in indices_to_blank:
        pid = corrupted_df.loc[idx, "paper_id"]
        corrupted_df.loc[idx, "summary"] = ""
        corrupted_df.loc[idx, "summary_chars"] = 0
        logs.append({
            "scenario": "blank_summary",
            "paper_id": pid,
            "action": "summary cleared to blank",
        })

    # 3. Inject noise into summary (for next 2 rows)
    indices_to_noise = list(corrupted_df.index[2:4])
    for idx in indices_to_noise:
        if idx in corrupted_df.index:
            pid = corrupted_df.loc[idx, "paper_id"]
            noisy_text = str(corrupted_df.loc[idx, "summary"]) + " [CORRUPTED_NOISE_ERR_99999]"
            corrupted_df.loc[idx, "summary"] = noisy_text
            corrupted_df.loc[idx, "summary_chars"] = len(noisy_text)
            logs.append({
                "scenario": "inject_noise",
                "paper_id": pid,
                "action": "appended corruption noise string to summary",
            })

    # 4. Truncate title < 8 chars (for next 2 rows)
    indices_to_truncate = list(corrupted_df.index[4:6])
    for idx in indices_to_truncate:
        if idx in corrupted_df.index:
            pid = corrupted_df.loc[idx, "paper_id"]
            orig_title = str(corrupted_df.loc[idx, "title"])
            truncated = orig_title[:5]
            corrupted_df.loc[idx, "title"] = truncated
            logs.append({
                "scenario": "truncate_title",
                "paper_id": pid,
                "original_title": orig_title,
                "truncated_title": truncated,
            })

    # 5. Stale date (shift published date back 365 days)
    indices_to_stale = list(corrupted_df.index[6:9])
    for idx in indices_to_stale:
        if idx in corrupted_df.index:
            pid = corrupted_df.loc[idx, "paper_id"]
            current_age = int(corrupted_df.loc[idx, "age_days"])
            corrupted_df.loc[idx, "age_days"] = current_age + 365
            corrupted_df.loc[idx, "published"] = "2024-01-01"
            logs.append({
                "scenario": "stale_date",
                "paper_id": pid,
                "action": "aged published date back by 365 days",
            })

    # 6. Duplicate rows (duplicate first 3 rows)
    dup_rows = corrupted_df.head(3).copy()
    corrupted_df = pd.concat([corrupted_df, dup_rows], ignore_index=True)
    logs.append({
        "scenario": "duplicate_rows",
        "duplicated_count": len(dup_rows),
    })

    # Rebuild text_for_embedding for all rows
    rebuilt_texts = []
    for _, row in corrupted_df.iterrows():
        title = str(row["title"])
        authors_joined = str(row["authors_joined"]) if "authors_joined" in row else str(row.get("authors", ""))
        published = str(row["published"])
        categories_joined = str(row["categories_joined"]) if "categories_joined" in row else str(row.get("categories", ""))
        summary = str(row["summary"])

        text = (
            f"Title: {title}\n"
            f"Authors: {authors_joined}\n"
            f"Published: {published}\n"
            f"Categories: {categories_joined}\n"
            f"Summary: {summary}"
        )
        rebuilt_texts.append(text)

    corrupted_df["text_for_embedding"] = rebuilt_texts

    log_file = Path(output_log_path)
    log_file.parent.mkdir(parents=True, exist_ok=True)
    with open(log_file, "w", encoding="utf-8") as f:
        json.dump(logs, f, ensure_ascii=False, indent=2)

    return corrupted_df
