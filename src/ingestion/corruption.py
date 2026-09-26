from __future__ import annotations

from pathlib import Path
from typing import Any
import pandas as pd

from core.utils import write_json


def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path: Path | str) -> pd.DataFrame:
    """Simulate 6 synthetic data corruption scenarios:
    1. Drop 20% of latest records.
    2. Blank summaries.
    3. Inject random noise into summaries.
    4. Truncate titles to < 8 chars (violating GX length expectation).
    5. Stale publication dates (violating Freshness SLA).
    6. Duplicate rows (violating GX uniqueness expectation).
    Rebuilds text_for_embedding and logs operations.
    """
    corrupted_df = df.copy()
    corruption_log: list[dict[str, Any]] = []

    # 1. Drop latest records (~20% newest)
    num_to_drop = max(1, int(len(corrupted_df) * 0.20))
    dropped_records = corrupted_df.iloc[:num_to_drop]
    dropped_ids = dropped_records["paper_id"].tolist()
    corrupted_df = corrupted_df.iloc[num_to_drop:].reset_index(drop=True)
    corruption_log.append(
        {
            "scenario": "drop_latest",
            "description": f"Dropped {num_to_drop} latest records (20% of dataset)",
            "affected_count": num_to_drop,
            "affected_ids": dropped_ids,
        }
    )

    # 2. Blank summary (2 rows)
    blank_indices = [0, 1] if len(corrupted_df) > 1 else [0]
    blank_ids = []
    for idx in blank_indices:
        if idx < len(corrupted_df):
            corrupted_df.at[idx, "summary"] = ""
            blank_ids.append(corrupted_df.at[idx, "paper_id"])
    corruption_log.append(
        {
            "scenario": "blank_summary",
            "description": "Erased paper summary (empty string)",
            "affected_count": len(blank_ids),
            "affected_ids": blank_ids,
        }
    )

    # 3. Inject noise into summary (2 rows)
    noise_indices = [2, 3] if len(corrupted_df) > 3 else []
    noise_ids = []
    for idx in noise_indices:
        if idx < len(corrupted_df):
            corrupted_df.at[idx, "summary"] = "### CORRUPTED RANDOM NOISE &&& MALFORMED TEXT ??? $$$ ###"
            noise_ids.append(corrupted_df.at[idx, "paper_id"])
    corruption_log.append(
        {
            "scenario": "inject_noise",
            "description": "Injected gibberish noise into summary",
            "affected_count": len(noise_ids),
            "affected_ids": noise_ids,
        }
    )

    # 4. Truncate title to < 8 chars (2 rows) -> Triggers GX ExpectColumnValueLengthsToBeBetween
    truncate_indices = [4, 5] if len(corrupted_df) > 5 else []
    truncated_ids = []
    for idx in truncate_indices:
        if idx < len(corrupted_df):
            corrupted_df.at[idx, "title"] = "Bad"
            truncated_ids.append(corrupted_df.at[idx, "paper_id"])
    corruption_log.append(
        {
            "scenario": "truncate_title",
            "description": "Truncated paper title to < 8 chars ('Bad')",
            "affected_count": len(truncated_ids),
            "affected_ids": truncated_ids,
        }
    )

    # 5. Stale date (make > 25% of dataset stale) -> Triggers Freshness SLA violation
    stale_indices = list(range(6, min(14, len(corrupted_df))))
    stale_ids = []
    for idx in stale_indices:
        corrupted_df.at[idx, "published"] = "2018-01-01"
        corrupted_df.at[idx, "age_days"] = 3000
        stale_ids.append(corrupted_df.at[idx, "paper_id"])
    corruption_log.append(
        {
            "scenario": "stale_date",
            "description": "Set published date to 2018-01-01 (age_days = 3000)",
            "affected_count": len(stale_ids),
            "affected_ids": stale_ids,
        }
    )

    # 6. Duplicate rows (2 rows) -> Triggers GX ExpectColumnValuesToBeUnique
    dup_rows = corrupted_df.iloc[[0, 1]].copy()
    duplicated_ids = dup_rows["paper_id"].tolist()
    corrupted_df = pd.concat([corrupted_df, dup_rows], ignore_index=True)
    corruption_log.append(
        {
            "scenario": "duplicate_rows",
            "description": "Appended duplicate rows to cause duplicate paper_id",
            "affected_count": len(duplicated_ids),
            "affected_ids": duplicated_ids,
        }
    )

    # 7. Rebuild text_for_embedding & helper columns
    for idx in range(len(corrupted_df)):
        title = corrupted_df.at[idx, "title"]
        authors = corrupted_df.at[idx, "authors_joined"]
        categories = corrupted_df.at[idx, "categories_joined"]
        published = corrupted_df.at[idx, "published"]
        summary = corrupted_df.at[idx, "summary"]
        corrupted_df.at[idx, "summary_chars"] = len(str(summary))
        corrupted_df.at[idx, "text_for_embedding"] = (
            f"Title: {title}\n"
            f"Authors: {authors}\n"
            f"Categories: {categories}\n"
            f"Published: {published}\n"
            f"Summary: {summary}"
        )

    # 8. Write corruption log
    out_p = Path(output_log_path)
    write_json(out_p, corruption_log)

    return corrupted_df
