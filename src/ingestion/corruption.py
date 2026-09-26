from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from core.utils import write_json
from ingestion.cleaning import rebuild_embedding_columns


STALE_PUBLISHED = "2019-01-01"
NOISE_MARKER = " ###CORRUPT### zzqnoise "


def _age_days_from_published(published: str, run_date: datetime) -> int:
    try:
        published_dt = datetime.strptime(str(published)[:10], "%Y-%m-%d").replace(tzinfo=UTC)
    except ValueError:
        return 9999
    return (run_date.astimezone(UTC) - published_dt).days


def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path) -> pd.DataFrame:
    """Inject six synthetic data faults and persist a corruption log."""
    if df.empty:
        write_json(Path(output_log_path), {"scenarios": [], "row_count_after": 0})
        return df.copy()

    work = df.copy(deep=True).reset_index(drop=True)
    work = work.sort_values(["published", "paper_id"], ascending=[False, True]).reset_index(drop=True)
    log: list[dict] = []

    drop_n = max(1, int(round(len(work) * 0.20)))
    dropped = work.iloc[:drop_n]
    work = work.iloc[drop_n:].reset_index(drop=True)
    log.append(
        {
            "name": "drop_latest_records",
            "description": "Drop the newest 20% of records to simulate a missed incremental load.",
            "count": int(len(dropped)),
            "paper_ids": dropped["paper_id"].tolist(),
        }
    )

    blank_n = min(4, len(work))
    blank_ids = work.iloc[:blank_n]["paper_id"].tolist()
    if blank_n:
        work.loc[work.index[:blank_n], "summary"] = ""
    log.append(
        {
            "name": "blank_summary",
            "description": "Blank summaries so retrieval and answer extraction lose abstract context.",
            "count": blank_n,
            "paper_ids": blank_ids,
        }
    )

    noise_start = blank_n
    noise_end = min(noise_start + 4, len(work))
    noise_ids = work.iloc[noise_start:noise_end]["paper_id"].tolist()
    if noise_end > noise_start:
        slice_idx = work.index[noise_start:noise_end]
        work.loc[slice_idx, "summary"] = work.loc[slice_idx, "summary"].astype(str) + NOISE_MARKER
    log.append(
        {
            "name": "inject_noise",
            "description": "Append garbage tokens to summaries to drift embeddings.",
            "count": len(noise_ids),
            "paper_ids": noise_ids,
        }
    )

    trunc_start = noise_end
    trunc_end = min(trunc_start + 4, len(work))
    trunc_ids = work.iloc[trunc_start:trunc_end]["paper_id"].tolist()
    if trunc_end > trunc_start:
        slice_idx = work.index[trunc_start:trunc_end]
        work.loc[slice_idx, "title"] = work.loc[slice_idx, "title"].astype(str).str.slice(0, 7)
    log.append(
        {
            "name": "truncate_title",
            "description": "Truncate titles to fewer than 8 characters, breaking exact title lookup.",
            "count": len(trunc_ids),
            "paper_ids": trunc_ids,
        }
    )

    stale_start = 0
    stale_end = min(max(8, int(round(len(work) * 0.5))), len(work))
    stale_ids = work.iloc[stale_start:stale_end]["paper_id"].tolist()
    if stale_end > stale_start:
        slice_idx = work.index[stale_start:stale_end]
        work.loc[slice_idx, "published"] = STALE_PUBLISHED
        work.loc[slice_idx, "updated"] = STALE_PUBLISHED
    log.append(
        {
            "name": "stale_date",
            "description": "Move published dates into the distant past to violate the freshness SLA.",
            "count": len(stale_ids),
            "paper_ids": stale_ids,
        }
    )

    dup_n = min(3, len(work))
    duplicates = work.iloc[:dup_n].copy()
    dup_ids = duplicates["paper_id"].tolist()
    work = pd.concat([work, duplicates], ignore_index=True)
    log.append(
        {
            "name": "duplicate_rows",
            "description": "Duplicate rows so paper_id uniqueness checks fail.",
            "count": dup_n,
            "paper_ids": dup_ids,
        }
    )

    run_date = datetime.now(UTC)
    work = rebuild_embedding_columns(work)
    work["age_days"] = [
        _age_days_from_published(str(published), run_date) for published in work["published"].tolist()
    ]
    work["age_days"] = work["age_days"].astype(int)

    write_json(
        Path(output_log_path),
        {
            "scenarios": log,
            "row_count_before": int(len(df)),
            "row_count_after": int(len(work)),
        },
    )
    return work
