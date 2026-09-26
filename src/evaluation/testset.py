from __future__ import annotations

from pathlib import Path
from typing import Any
import pandas as pd

from core.utils import first_sentence, write_json


def build_test_set(df: pd.DataFrame, output_path: Path | str) -> list[dict[str, Any]]:
    """Build standardized 10-question evaluation benchmark test set across 4 question types:
    summary (3), authors (3), date (2), categories (2).
    """
    if len(df) < 10:
        raise ValueError(f"Need at least 10 documents to build the evaluation set, got {len(df)}")

    test_cases: list[dict[str, Any]] = []

    # Distribution: 3 summary, 3 authors, 2 date, 2 categories = 10 questions
    specs = [
        ("summary", 0),
        ("summary", 1),
        ("summary", 2),
        ("authors", 3),
        ("authors", 4),
        ("authors", 5),
        ("date", 6),
        ("date", 7),
        ("categories", 8),
        ("categories", 9),
    ]

    for idx, (q_type, row_idx) in enumerate(specs, start=1):
        row = df.iloc[row_idx]
        title = row["title"]
        paper_id = row["paper_id"]

        if q_type == "summary":
            question = f"What is the summary of '{title}'?"
            ground_truth = first_sentence(str(row["summary"]))
        elif q_type == "authors":
            question = f"Who authored '{title}'?"
            ground_truth = str(row["authors_joined"])
        elif q_type == "date":
            question = f"When was '{title}' published?"
            ground_truth = str(row["published"])
        elif q_type == "categories":
            question = f"What categories describe '{title}'?"
            ground_truth = str(row["categories_joined"])
        else:
            question = f"What is the summary of '{title}'?"
            ground_truth = first_sentence(str(row["summary"]))

        test_cases.append(
            {
                "id": f"test_{idx:02d}",
                "question_type": q_type,
                "question": question,
                "ground_truth": ground_truth,
                "ground_truth_doc_ids": [paper_id],
            }
        )

    out_p = Path(output_path)
    write_json(out_p, test_cases)
    return test_cases
