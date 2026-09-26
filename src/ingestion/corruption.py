from __future__ import annotations

import json
import random
import string
from pathlib import Path

import pandas as pd

from core.utils import compact_join, normalize_whitespace, write_json


def _rebuild_text_for_embedding(df: pd.DataFrame) -> pd.DataFrame:
    """Rebuild text_for_embedding column from current field values."""
    df = df.copy()
    df["text_for_embedding"] = df.apply(
        lambda row: (
            f"Title: {row.get('title', '')}\n"
            f"Authors: {row.get('authors_joined', '')}\n"
            f"Categories: {row.get('categories_joined', '')}\n"
            f"Published: {row.get('published', '')}\n"
            f"Summary: {row.get('summary', '')}"
        ).strip(),
        axis=1,
    )
    return df


def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path) -> pd.DataFrame:
    """Simulate 6 types of data corruption on the clean dataframe.

    Corruption types:
    1. Drop latest records    — remove ~20% of newest rows
    2. Blank summary          — clear summary for ~15% of rows
    3. Inject noise           — inject random chars into summary for ~15% of rows
    4. Truncate title         — shorten title to <8 chars for ~10% of rows
    5. Stale date             — push published date back 400+ days for ~10% of rows
    6. Duplicate rows         — duplicate ~10% of rows

    Writes corruption log to output_log_path.
    Returns corrupted dataframe.
    """
    rng = random.Random(42)
    log: list[dict] = []
    df = df.copy().reset_index(drop=True)
    total = len(df)

    # ── 1. Drop latest records (~20% of newest) ──────────────────────
    n_drop = max(1, int(total * 0.20))
    df_sorted_by_date = df.sort_values("published", ascending=False)
    drop_indices = list(df_sorted_by_date.index[:n_drop])
    dropped_ids = df.loc[drop_indices, "paper_id"].tolist()
    df = df.drop(index=drop_indices).reset_index(drop=True)
    log.append({
        "corruption_type": "drop_latest_records",
        "affected_count": n_drop,
        "affected_ids": dropped_ids,
        "description": f"Dropped {n_drop} most-recent records ({n_drop/total*100:.0f}% of total).",
    })

    # ── 2. Blank summary ────────────────────────────────────────────
    n_blank = max(1, int(len(df) * 0.15))
    blank_indices = rng.sample(range(len(df)), n_blank)
    blank_ids = df.loc[blank_indices, "paper_id"].tolist()
    df.loc[blank_indices, "summary"] = ""
    df.loc[blank_indices, "summary_chars"] = 0
    log.append({
        "corruption_type": "blank_summary",
        "affected_count": n_blank,
        "affected_ids": blank_ids,
        "description": f"Blanked summary for {n_blank} rows.",
    })

    # ── 3. Inject noise ─────────────────────────────────────────────
    n_noise = max(1, int(len(df) * 0.15))
    noise_indices = rng.sample(range(len(df)), n_noise)
    noise_ids = df.loc[noise_indices, "paper_id"].tolist()
    noise_chars = string.punctuation + "😵🔥💥###$$$@@@"
    for idx in noise_indices:
        junk = "".join(rng.choices(noise_chars, k=30))
        df.loc[idx, "summary"] = junk + " " + str(df.loc[idx, "summary"])
    log.append({
        "corruption_type": "inject_noise",
        "affected_count": n_noise,
        "affected_ids": noise_ids,
        "description": f"Injected random noise characters into summary for {n_noise} rows.",
    })

    # ── 4. Truncate title ──────────────────────────────────────────
    n_trunc = max(1, int(len(df) * 0.10))
    trunc_indices = rng.sample(range(len(df)), n_trunc)
    trunc_ids = df.loc[trunc_indices, "paper_id"].tolist()
    for idx in trunc_indices:
        df.loc[idx, "title"] = str(df.loc[idx, "title"])[:7]  # < 8 chars
    log.append({
        "corruption_type": "truncate_title",
        "affected_count": n_trunc,
        "affected_ids": trunc_ids,
        "description": f"Truncated title to <8 characters for {n_trunc} rows.",
    })

    # ── 5. Stale date ──────────────────────────────────────────────
    n_stale = max(1, int(len(df) * 0.10))
    stale_indices = rng.sample(range(len(df)), n_stale)
    stale_ids = df.loc[stale_indices, "paper_id"].tolist()
    for idx in stale_indices:
        df.loc[idx, "published"] = "2020-01-01"
        df.loc[idx, "updated"] = "2020-01-01"
        if "age_days" in df.columns:
            df.loc[idx, "age_days"] = 2400  # definitely stale
    log.append({
        "corruption_type": "stale_date",
        "affected_count": n_stale,
        "affected_ids": stale_ids,
        "description": f"Set published date to 2020-01-01 (>400 days ago) for {n_stale} rows.",
    })

    # ── 6. Duplicate rows ─────────────────────────────────────────
    n_dup = max(1, int(len(df) * 0.10))
    dup_indices = rng.sample(range(len(df)), n_dup)
    dup_ids = df.loc[dup_indices, "paper_id"].tolist()
    dup_rows = df.loc[dup_indices].copy()
    df = pd.concat([df, dup_rows], ignore_index=True)
    log.append({
        "corruption_type": "duplicate_rows",
        "affected_count": n_dup,
        "affected_ids": dup_ids,
        "description": f"Duplicated {n_dup} rows.",
    })

    # ── Rebuild text_for_embedding ───────────────────────────────
    df = _rebuild_text_for_embedding(df)

    # ── Write corruption log ─────────────────────────────────────
    write_json(Path(output_log_path), log)

    total_after = len(df)
    print(f"[corruption] Applied 6 corruption types. Rows: {total} → {total_after}")
    for entry in log:
        print(f"  • {entry['corruption_type']}: {entry['description']}")

    return df
