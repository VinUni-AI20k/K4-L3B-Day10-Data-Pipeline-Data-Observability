from __future__ import annotations

import json
from pathlib import Path
from typing import Any
import pandas as pd

from core.utils import first_sentence, normalize_whitespace


def _extract_authors_text(row: pd.Series) -> str:
    if "authors_joined" in row and pd.notna(row["authors_joined"]) and str(row["authors_joined"]).strip():
        return str(row["authors_joined"]).strip()
    authors_val = row.get("authors")
    if isinstance(authors_val, list):
        return ", ".join(str(a).strip() for a in authors_val if str(a).strip())
    if isinstance(authors_val, str) and authors_val.strip():
        return authors_val.strip()
    return "Unknown Authors"


def _extract_categories_text(row: pd.Series) -> str:
    if "categories_joined" in row and pd.notna(row["categories_joined"]) and str(row["categories_joined"]).strip():
        return str(row["categories_joined"]).strip()
    categories_val = row.get("categories")
    if isinstance(categories_val, list):
        return ", ".join(str(c).strip() for c in categories_val if str(c).strip())
    if isinstance(categories_val, str) and categories_val.strip():
        return categories_val.strip()
    primary = row.get("primary_category")
    if pd.notna(primary) and str(primary).strip():
        return str(primary).strip()
    return "General"


def build_test_set(df: pd.DataFrame, output_path: Any = None) -> list[dict[str, Any]]:
    """Build a deterministic benchmark test set of 10 questions across 4 question types:
    - summary: Asks for paper summary (first sentence).
    - authors: Asks for paper authors.
    - date: Asks for publication date.
    - categories: Asks for subject categories.
    """
    if df.empty:
        return []

    test_set: list[dict[str, Any]] = []
    question_types = ["summary", "authors", "date", "categories"]

    num_rows = len(df)
    for i in range(10):
        row_idx = i % num_rows
        row = df.iloc[row_idx]
        q_type = question_types[i % len(question_types)]

        paper_id = str(row.get("paper_id", f"doc_{i+1}")).strip()
        title = normalize_whitespace(str(row.get("title", f"Paper {i+1}"))).strip()
        summary = str(row.get("summary", "")).strip()
        date = str(row.get("published", "")).strip() or "Unknown Date"

        if q_type == "summary":
            first_sent = first_sentence(summary) if summary else title
            question = f"What is the summary of the paper '{title}'?"
            ground_truth = first_sent
        elif q_type == "authors":
            question = f"Who are the authors of the paper '{title}'?"
            ground_truth = _extract_authors_text(row)
        elif q_type == "date":
            question = f"When was the paper '{title}' published?"
            ground_truth = date
        else:  # categories
            question = f"What categories or subjects does the paper '{title}' cover?"
            ground_truth = _extract_categories_text(row)

        item = {
            "id": f"eval_{i+1:03d}",
            "question_type": q_type,
            "question": question,
            "ground_truth": ground_truth,
            "ground_truth_doc_ids": [paper_id],
        }
        test_set.append(item)

    if output_path:
        out_file = Path(output_path)
        out_file.parent.mkdir(parents=True, exist_ok=True)
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(test_set, f, ensure_ascii=False, indent=2)

    return test_set
