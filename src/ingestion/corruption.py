from __future__ import annotations

from pathlib import Path

import pandas as pd

from core.utils import write_json


def _safe_text(value) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def _rebuild_text_for_embedding(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    df["summary_chars"] = df["summary"].fillna("").astype(str).str.len()

    df["text_for_embedding"] = df.apply(
        lambda row: (
            f"Title: {_safe_text(row.get('title'))}\n"
            f"Authors: {_safe_text(row.get('authors_joined'))}\n"
            f"Categories: {_safe_text(row.get('categories_joined'))}\n"
            f"Summary: {_safe_text(row.get('summary'))}"
        ),
        axis=1,
    )

    return df


def corrupt_clean_dataframe(
    df: pd.DataFrame,
    output_log_path: Path,
) -> pd.DataFrame:
    """Inject six deterministic corruption scenarios into cleaned data."""

    if df.empty:
        raise ValueError("Cannot corrupt an empty dataframe.")

    corrupted = df.copy(deep=True).reset_index(drop=True)

    log: dict = {
        "before_rows": len(corrupted),
        "scenarios": {},
    }

    # ---------------------------------------------------------
    # 1. Drop latest ~20% records
    # ---------------------------------------------------------
    published_dates = pd.to_datetime(
        corrupted["published"],
        errors="coerce",
        utc=True,
    )

    drop_count = max(1, round(len(corrupted) * 0.20))

    latest_indices = (
        published_dates
        .sort_values(ascending=False)
        .head(drop_count)
        .index
        .tolist()
    )

    dropped_ids = (
        corrupted.loc[latest_indices, "paper_id"]
        .astype(str)
        .tolist()
    )

    corrupted = (
        corrupted
        .drop(index=latest_indices)
        .reset_index(drop=True)
    )

    log["scenarios"]["drop_latest_records"] = {
        "affected_count": len(dropped_ids),
        "paper_ids": dropped_ids,
    }

    # Số dòng dùng cho mỗi corruption tiếp theo.
    n = len(corrupted)
    chunk = max(1, min(2, n // 6))

    # ---------------------------------------------------------
    # 2. Blank summary
    # ---------------------------------------------------------
    blank_indices = list(range(0, min(chunk, n)))

    blank_ids = corrupted.loc[
        blank_indices, "paper_id"
    ].astype(str).tolist()

    corrupted.loc[blank_indices, "summary"] = ""

    log["scenarios"]["blank_summary"] = {
        "affected_count": len(blank_ids),
        "paper_ids": blank_ids,
    }

    # ---------------------------------------------------------
    # 3. Inject noise
    # ---------------------------------------------------------
    noise_start = chunk
    noise_end = min(noise_start + chunk, n)
    noise_indices = list(range(noise_start, noise_end))

    noise_ids = corrupted.loc[
        noise_indices, "paper_id"
    ].astype(str).tolist()

    corrupted.loc[
        noise_indices,
        "summary",
    ] = (
        "@@@ CORRUPTED_NOISE ### "
        "zxqv 9999 random unrelated tokens "
        "INVALID_DATA INVALID_DATA INVALID_DATA"
    )

    log["scenarios"]["inject_noise"] = {
        "affected_count": len(noise_ids),
        "paper_ids": noise_ids,
    }

    # ---------------------------------------------------------
    # 4. Truncate title (< 8 characters)
    # ---------------------------------------------------------
    title_start = noise_end
    title_end = min(title_start + chunk, n)
    title_indices = list(range(title_start, title_end))

    title_ids = corrupted.loc[
        title_indices, "paper_id"
    ].astype(str).tolist()

    for idx in title_indices:
        title = _safe_text(corrupted.at[idx, "title"])
        corrupted.at[idx, "title"] = title[:5] or "BAD"

    log["scenarios"]["truncate_title"] = {
        "affected_count": len(title_ids),
        "paper_ids": title_ids,
    }

    # ---------------------------------------------------------
    # 5. Stale published date
    # ---------------------------------------------------------
    stale_start = title_end
    stale_end = min(stale_start + chunk, n)
    stale_indices = list(range(stale_start, stale_end))

    stale_ids = corrupted.loc[
        stale_indices, "paper_id"
    ].astype(str).tolist()

    stale_date = (
        pd.Timestamp.now(tz="UTC")
        - pd.Timedelta(days=730)
    ).date().isoformat()

    corrupted.loc[stale_indices, "published"] = stale_date

    log["scenarios"]["stale_date"] = {
        "affected_count": len(stale_ids),
        "paper_ids": stale_ids,
        "new_published_date": stale_date,
    }

    # Recalculate age_days.
    published = pd.to_datetime(
        corrupted["published"],
        errors="coerce",
        utc=True,
    )

    now = pd.Timestamp.now(tz="UTC")

    corrupted["age_days"] = (
        now - published
    ).dt.days.fillna(0).astype(int)

    # ---------------------------------------------------------
    # 6. Duplicate rows
    # ---------------------------------------------------------
    duplicate_count = min(2, len(corrupted))

    duplicate_rows = corrupted.tail(
        duplicate_count
    ).copy()

    duplicate_ids = (
        duplicate_rows["paper_id"]
        .astype(str)
        .tolist()
    )

    corrupted = pd.concat(
        [corrupted, duplicate_rows],
        ignore_index=True,
    )

    log["scenarios"]["duplicate_rows"] = {
        "affected_count": duplicate_count,
        "paper_ids": duplicate_ids,
    }

    # Critical: embedding text must reflect corrupted data.
    corrupted = _rebuild_text_for_embedding(corrupted)

    log["after_rows"] = len(corrupted)

    write_json(output_log_path, log)

    return corrupted