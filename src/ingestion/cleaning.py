from __future__ import annotations

from datetime import datetime
import pandas as pd
from ingestion.crossref import PaperRecord


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
   """TODO(student): clean raw records thanh dataframe san sang de embed.

   Pseudo-code:
   1. Normalize title, summary, authors, categories.
   2. Parse published/updated date.
   3. Tinh age_days.
   4. Tao cot helper:
      - authors_joined
      - categories_joined
      - summary_chars
      - text_for_embedding
   5. Drop duplicates va filter row xau.
   6. Sort dataframe va return.
   """
   if not records:
      return pd.DataFrame()
   
   df = pd.DataFrame([r.__dict__ for r in records])

   df["title"] = df["title"].str.strip()
   df["summary"] = df["summary"].str.strip()

   df["published"] = pd.to_datetime(df["published"], errors="coerce")
   df["updated"] = pd.to_datetime(df["updated"], errors="coerce")

   if run_date.tzinfo is None:
      run_date = run_date.replace(tzinfo=pd.Timestamp.utcnow().tzinfo)
   #tinh tuổi
   df["age_days"] = (run_date - df["published"]).dt.days.fillna(0).clip(lower=0).astype(int)
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
    
    # 6. Sort
   df = df.sort_values(by='published', ascending=False).reset_index(drop=True)
   
   return df
