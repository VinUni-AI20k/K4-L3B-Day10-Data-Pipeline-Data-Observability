from __future__ import annotations

from math import ceil
from pathlib import Path

import pandas as pd

from core.utils import write_json


def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path: Path) -> pd.DataFrame:
    """Inject deterministic data failures and record every affected row.

    The input dataframe is never modified.  Deterministic selections make the
    corrupted dataset and its metrics reproducible across repeated runs.
    """
    required_columns = {
        "paper_id",
        "title",
        "summary",
        "published",
        "authors_joined",
        "categories_joined",
    }
    missing_columns = required_columns.difference(df.columns)
    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"Cannot corrupt dataframe; missing columns: {missing}")

    corrupted = df.copy(deep=True).reset_index(drop=True)
    log: list[dict[str, object]] = []
    if corrupted.empty:
        write_json(output_log_path, log)
        return corrupted

    def add_log(action: str, row: pd.Series, changes: dict[str, object]) -> None:
        log.append(
            {
                "action": action,
                "paper_id": str(row["paper_id"]),
                "changes": changes,
            }
        )

    # 1. Remove the newest 20 percent of records (round up so a small input is affected).
    published_dates = pd.to_datetime(corrupted["published"], errors="coerce", utc=True)
    drop_count = min(len(corrupted), max(1, ceil(len(corrupted) * 0.20)))
    latest_indexes = published_dates.nlargest(drop_count).index
    for index in latest_indexes:
        row = corrupted.loc[index]
        add_log("drop_latest_records", row, {"dropped": True, "published": str(row["published"])})
    corrupted = corrupted.drop(index=latest_indexes).reset_index(drop=True)

    def selected_indexes(start: int, count: int = 2) -> list[int]:
        return list(range(start, min(start + count, len(corrupted))))

    # Use non-overlapping rows where possible, making the six failures easy to inspect.
    blank_indexes = selected_indexes(0)
    noise_indexes = selected_indexes(len(blank_indexes))
    title_indexes = selected_indexes(len(blank_indexes) + len(noise_indexes))
    stale_indexes = selected_indexes(len(blank_indexes) + len(noise_indexes) + len(title_indexes))

    # 2. Remove summaries.
    for index in blank_indexes:
        before = str(corrupted.at[index, "summary"])
        corrupted.at[index, "summary"] = ""
        add_log("blank_summary", corrupted.loc[index], {"summary": {"before": before, "after": ""}})

    # 3. Add malformed text to summaries.
    noise = " @@###CORRUPTED_TEXT###@@ "
    for index in noise_indexes:
        before = str(corrupted.at[index, "summary"])
        after = f"{before}{noise}"
        corrupted.at[index, "summary"] = after
        add_log("inject_noise", corrupted.loc[index], {"summary": {"before": before, "after": after}})

    # 4. Make titles invalid for the title-length quality expectation.
    for index in title_indexes:
        before = str(corrupted.at[index, "title"])
        after = before[:7]
        corrupted.at[index, "title"] = after
        add_log("truncate_title", corrupted.loc[index], {"title": {"before": before, "after": after}})

    # 5. Set publication dates to exactly 365 days ago and update the derived age.
    stale_date = (pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=365)).strftime("%Y-%m-%d")
    for index in stale_indexes:
        before = str(corrupted.at[index, "published"])
        corrupted.at[index, "published"] = stale_date
        corrupted.at[index, "age_days"] = 365
        add_log(
            "stale_date",
            corrupted.loc[index],
            {"published": {"before": before, "after": stale_date}, "age_days": {"after": 365}},
        )

    # Recreate derived fields after mutations so the corrupted data reaches the vector store.
    corrupted["summary_chars"] = corrupted["summary"].fillna("").astype(str).str.len()
    corrupted["text_for_embedding"] = corrupted.apply(
        lambda row: (
            f"Title: {row['title']}\n"
            f"Authors: {row['authors_joined']}\n"
            f"Published: {row['published']}\n"
            f"Categories: {row['categories_joined']}\n"
            f"Summary: {row['summary']}"
        ),
        axis=1,
    )

    # 6. Append copies with the same paper_id to deliberately violate uniqueness.
    duplicate_count = min(2, len(corrupted))
    duplicates = corrupted.iloc[:duplicate_count].copy()
    for _, row in duplicates.iterrows():
        add_log("duplicate_rows", row, {"duplicated": True})
    corrupted = pd.concat([corrupted, duplicates], ignore_index=True)

    write_json(output_log_path, log)
    return corrupted
