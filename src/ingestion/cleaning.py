from __future__ import annotations

from datetime import datetime
import pandas as pd
from ingestion.crossref import PaperRecord


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    """Clean raw records into embedding-ready dataframe."""
    if not records:
        return pd.DataFrame()
    
    df = pd.DataFrame([r.__dict__ for r in records])

    df["title"] = df["title"].astype(str).str.strip()
    df["summary"] = df["summary"].astype(str).str.strip()

    published_dt = pd.to_datetime(df["published"], errors="coerce", utc=True)
    run_date_utc = pd.to_datetime(run_date, utc=True)

    df["age_days"] = (run_date_utc - published_dt).dt.days.fillna(0).clip(lower=0).astype(int)
    df["published"] = published_dt.dt.strftime("%Y-%m-%d").fillna("")
    df["updated"] = pd.to_datetime(df["updated"], errors="coerce", utc=True).dt.strftime("%Y-%m-%d").fillna("")

    df["authors_joined"] = df["authors"].apply(lambda x: ','.join(x) if isinstance(x, list) else str(x))
    df["categories_joined"] = df["categories"].apply(lambda x: ','.join(x) if isinstance(x, list) else str(x))
    df["summary_chars"] = df["summary"].str.len()
    df['text_for_embedding'] = (
        "Title: " + df['title'] + "\n" +
        "Authors: " + df['authors_joined'] + "\n" +
        "Categories: " + df['categories_joined'] + "\n" +
        "Summary: " + df['summary']
    )
    df = df.drop_duplicates(subset=['paper_id'])
    df = df.dropna(subset=['paper_id', 'title', 'summary'])
    df = df[df['paper_id'].astype(str).str.len() > 0]
    df = df[df['title'].astype(str).str.len() > 0]
     
    # Sort
    df = df.sort_values(by='published', ascending=False).reset_index(drop=True)
    
    return df