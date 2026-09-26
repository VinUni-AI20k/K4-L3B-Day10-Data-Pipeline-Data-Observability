from __future__ import annotations

import json
import pandas as pd


def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path) -> pd.DataFrame:
    corrupted_df = df.copy()
    logs = []
    
    if len(corrupted_df) > 0:
        # Force parsing from string to avoid int64 timestamp issues when loaded from JSON
        corrupted_df["published_date"] = pd.to_datetime(corrupted_df["published"], errors="coerce").dt.tz_localize(None)

        original_len = len(corrupted_df)
        drop_count = max(1, int(original_len * 0.2))
        corrupted_df = corrupted_df.sort_values(by="published_date", ascending=False)
        corrupted_df = corrupted_df.iloc[drop_count:]
        logs.append(f"Dropped {drop_count} latest records")
    
    if len(corrupted_df) > 0:
        idx = corrupted_df.index[0]
        corrupted_df.at[idx, "summary"] = ""
        logs.append(f"Blanked summary for paper_id {corrupted_df.at[idx, 'paper_id']}")
        
        if len(corrupted_df) > 1:
            idx = corrupted_df.index[1]
            corrupted_df.at[idx, "summary"] = "NOISE_CORRUPTION " + str(corrupted_df.at[idx, "summary"])
            logs.append(f"Injected noise into summary for paper_id {corrupted_df.at[idx, 'paper_id']}")
            
        if len(corrupted_df) > 2:
            idx = corrupted_df.index[2]
            corrupted_df.at[idx, "title"] = str(corrupted_df.at[idx, "title"])[:7]
            logs.append(f"Truncated title for paper_id {corrupted_df.at[idx, 'paper_id']}")
            
        if len(corrupted_df) > 3:
            idx = corrupted_df.index[3]
            old_date = corrupted_df.at[idx, "published_date"]
            corrupted_df.at[idx, "published_date"] = old_date - pd.Timedelta(days=365)
            corrupted_df.at[idx, "age_days"] = corrupted_df.at[idx, "age_days"] + 365
            logs.append(f"Made date stale for paper_id {corrupted_df.at[idx, 'paper_id']}")
            
        duplicate_row = corrupted_df.iloc[[-1]].copy()
        corrupted_df = pd.concat([corrupted_df, duplicate_row], ignore_index=True)
        logs.append(f"Duplicated paper_id {duplicate_row.iloc[0]['paper_id']}")
        
    corrupted_df["text_for_embedding"] = (
        "Title: " + corrupted_df["title"].fillna("") + "\n" +
        "Authors: " + corrupted_df["authors_joined"].fillna("") + "\n" +
        "Categories: " + corrupted_df["categories_joined"].fillna("") + "\n" +
        "Summary: " + corrupted_df["summary"].fillna("")
    )
    
    if output_log_path:
        with open(output_log_path, "w", encoding="utf-8") as f:
            json.dump(logs, f, ensure_ascii=False, indent=2)
            
    return corrupted_df
