from __future__ import annotations

from datetime import datetime

import pandas as pd

from ingestion.crossref import PaperRecord


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    data = []
    for r in records:
        data.append({
            "paper_id": r.paper_id,
            "title": r.title.strip() if r.title else "",
            "summary": r.summary.strip() if r.summary else "",
            "authors": r.authors,
            "categories": r.categories,
            "published": r.published,
            "updated": r.updated,
            "abs_url": r.abs_url,
            "pdf_url": r.pdf_url,
            "comment": r.comment
        })
    df = pd.DataFrame(data)
    if df.empty:
        return df

    df["published_date"] = pd.to_datetime(df["published"], format="mixed", errors="coerce").dt.tz_localize(None)
    run_date_naive = run_date.replace(tzinfo=None) if run_date.tzinfo else run_date
    df["age_days"] = (run_date_naive - df["published_date"]).dt.days

    df["authors_joined"] = df["authors"].apply(lambda x: ", ".join(x) if isinstance(x, list) else "")
    df["categories_joined"] = df["categories"].apply(lambda x: ", ".join(x) if isinstance(x, list) else "")
    df["summary_chars"] = df["summary"].str.len()
    
    df["text_for_embedding"] = (
        "Title: " + df["title"] + "\n" +
        "Authors: " + df["authors_joined"] + "\n" +
        "Categories: " + df["categories_joined"] + "\n" +
        "Summary: " + df["summary"]
    )

    df = df.drop_duplicates(subset=["paper_id"], keep="first")
    df = df[df["paper_id"].notna() & (df["paper_id"] != "")]
    df = df[df["title"].notna() & (df["title"] != "")]
    
    df = df.sort_values(by="published_date", ascending=False)
    
    return df
