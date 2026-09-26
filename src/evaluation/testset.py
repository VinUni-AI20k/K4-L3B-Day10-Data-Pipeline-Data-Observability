from __future__ import annotations

import json
from pathlib import Path
from typing import Any
import pandas as pd


def build_test_set(df: pd.DataFrame, output_path: Any) -> list[dict[str, Any]]:
    """Build a deterministic benchmark test set of 10 questions across 4 question types."""
    if df.empty:
        return []

    test_set: list[dict[str, Any]] = []
    question_types = ["summary", "authors", "date", "categories"]

    num_rows = len(df)
    # Generate exactly 10 questions distributed evenly across available papers
    for i in range(10):
        row_idx = i % num_rows
        row = df.iloc[row_idx]
        q_type = question_types[i % len(question_types)]

        paper_id = str(row["paper_id"])
        title = str(row["title"])
        summary = str(row["summary"])
        authors = str(row["authors_joined"]) if "authors_joined" in row else str(row.get("authors", ""))
        date = str(row["published"])
        categories = str(row["categories_joined"]) if "categories_joined" in row else str(row.get("categories", ""))

        if q_type == "summary":
            # Taking the first sentence or snippet of summary as ground_truth
            first_sentence = summary.split(". ")[0].strip() if summary else title
            question = f"What is the summary of the paper '{title}'?"
            ground_truth = first_sentence
        elif q_type == "authors":
            question = f"Who are the authors of the paper '{title}'?"
            ground_truth = authors or "Unknown Authors"
        elif q_type == "date":
            question = f"When was the paper '{title}' published?"
            ground_truth = date
        else:  # categories
            question = f"What categories or subjects does the paper '{title}' cover?"
            ground_truth = categories or "General AI"

        item = {
            "id": f"eval_{i+1:03d}",
            "question_type": q_type,
            "question": question,
            "ground_truth": ground_truth,
            "ground_truth_doc_ids": [paper_id],
        }
        test_set.append(item)

    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(test_set, f, ensure_ascii=False, indent=2)

    return test_set
