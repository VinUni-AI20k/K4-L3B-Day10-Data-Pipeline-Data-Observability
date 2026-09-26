from __future__ import annotations

import json
from typing import Any

import pandas as pd


def build_test_set(df: pd.DataFrame, output_path) -> list[dict[str, Any]]:
    if len(df) < 1:
        return []

    sample_df = df.head(10) if len(df) >= 10 else df
    
    test_set = []
    question_types = ["summary", "authors", "date", "categories"]
    
    for idx, row in enumerate(sample_df.to_dict(orient="records")):
        q_type = question_types[idx % len(question_types)]
        paper_id = row["paper_id"]
        
        if q_type == "summary":
            q = f"What is the main topic or summary of the paper titled '{row['title']}'?"
            gt = row["summary"]
        elif q_type == "authors":
            q = f"Who are the authors of the paper '{row['title']}'?"
            gt = row["authors_joined"]
        elif q_type == "date":
            q = f"When was the paper '{row['title']}' published?"
            gt = str(row["published"])
        elif q_type == "categories":
            q = f"What categories does the paper '{row['title']}' belong to?"
            gt = row["categories_joined"]
            
        test_set.append({
            "id": f"q_{idx}",
            "question_type": q_type,
            "question": q,
            "ground_truth": gt,
            "ground_truth_doc_ids": [paper_id]
        })
        
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(test_set, f, ensure_ascii=False, indent=2)
        
    return test_set
