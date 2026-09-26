from __future__ import annotations

from math import ceil
from pathlib import Path

import pandas as pd

from core.utils import write_json


def _embedding_text(row: pd.Series) -> str:
    """Use the same five sections as the clean ingestion output."""
    return (
        f"Title: {row['title']}\nSummary: {row['summary']}\nAuthors: {row['authors_joined']}"
        f"\nPublished: {row['published']}\nCategories: {row['categories_joined']}"
    )


def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path=None) -> pd.DataFrame:
    """Apply six reproducible corruptions to a copy of the clean dataframe.

    Pass no path to keep the log in ``result.attrs['corruption_log']`` only.
    """
    required = {
        "paper_id", "title", "summary", "published", "age_days",
        "authors_joined", "categories_joined", "summary_chars", "text_for_embedding",
    }
    missing = required.difference(df.columns)
    if missing:
        raise ValueError(f"Missing clean columns: {', '.join(sorted(missing))}")
    if output_log_path is not None and Path(output_log_path).exists():
        raise FileExistsError(f"Corruption log already exists: {output_log_path}")

    corrupted = df.copy(deep=True).sort_values(
        ["published", "paper_id"], ascending=[False, True]
    ).reset_index(drop=True)
    drop_count = ceil(len(corrupted) * 0.20)
    if len(corrupted) - drop_count < 5:
        raise ValueError("At least five papers must remain after the 20% drop")

    dropped = corrupted.iloc[:drop_count]
    events = [{
        "type": "drop_latest",
        "paper_ids": dropped["paper_id"].tolist(),
        "changes": [
            {"paper_id": row["paper_id"], "published_before": row["published"], "row_present_after": False}
            for _, row in dropped.iterrows()
        ],
    }]
    corrupted = corrupted.iloc[drop_count:].reset_index(drop=True)

    target_ids = sorted(corrupted["paper_id"].astype(str).unique())[:5]
    if len(target_ids) < 5:
        raise ValueError("Five distinct paper IDs are required for the remaining corruptions")

    blank_id, noise_id, title_id, stale_id, duplicate_id = target_ids

    blank_index = corrupted.index[corrupted["paper_id"] == blank_id][0]
    original_summary = str(corrupted.at[blank_index, "summary"])
    corrupted.at[blank_index, "summary"] = ""
    events.append({
        "type": "blank_summary", "paper_ids": [blank_id],
        "changes": [{"paper_id": blank_id, "field": "summary", "before": original_summary, "after": ""}],
    })

    noise_index = corrupted.index[corrupted["paper_id"] == noise_id][0]
    original_summary = str(corrupted.at[noise_index, "summary"])
    noisy_summary = original_summary + " @@##!!?? 0xDEADBEEF @@##!!??"
    corrupted.at[noise_index, "summary"] = noisy_summary
    events.append({
        "type": "inject_noise", "paper_ids": [noise_id],
        "changes": [{"paper_id": noise_id, "field": "summary", "before": original_summary, "after": noisy_summary}],
    })

    title_index = corrupted.index[corrupted["paper_id"] == title_id][0]
    original_title = str(corrupted.at[title_index, "title"])
    short_title = original_title[:7] if len(original_title) > 7 else "BAD"
    corrupted.at[title_index, "title"] = short_title
    events.append({
        "type": "truncate_title", "paper_ids": [title_id],
        "changes": [{"paper_id": title_id, "field": "title", "before": original_title, "after": short_title}],
    })

    stale_index = corrupted.index[corrupted["paper_id"] == stale_id][0]
    original_date = str(corrupted.at[stale_index, "published"])
    original_age = int(corrupted.at[stale_index, "age_days"])
    stale_date = (pd.Timestamp(original_date) - pd.Timedelta(days=365)).date().isoformat()
    corrupted.at[stale_index, "published"] = stale_date
    corrupted.at[stale_index, "age_days"] = original_age + 365
    events.append({
        "type": "stale_date", "paper_ids": [stale_id],
        "changes": [
            {"paper_id": stale_id, "field": "published", "before": original_date, "after": stale_date},
            {"paper_id": stale_id, "field": "age_days", "before": original_age, "after": original_age + 365},
        ],
    })

    duplicate_index = corrupted.index[corrupted["paper_id"] == duplicate_id][0]
    duplicate_row = corrupted.iloc[[duplicate_index]].copy(deep=True)
    count_before = int(corrupted["paper_id"].eq(duplicate_id).sum())
    corrupted = pd.concat([corrupted, duplicate_row], ignore_index=True)
    events.append({
        "type": "duplicate_doi", "paper_ids": [duplicate_id],
        "changes": [{"paper_id": duplicate_id, "field": "row_count_for_paper_id",
                     "before": count_before, "after": count_before + 1}],
    })

    corrupted["summary_chars"] = corrupted["summary"].astype(str).str.len()
    corrupted["text_for_embedding"] = corrupted.apply(_embedding_text, axis=1)
    log = {
        "selection": "Newest 20% by published date, then five lowest remaining DOI values",
        "input_rows": len(df),
        "output_rows": len(corrupted),
        "events": events,
    }
    corrupted.attrs["corruption_log"] = log
    if output_log_path is not None:
        write_json(Path(output_log_path), log)
    return corrupted
