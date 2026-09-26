from __future__ import annotations

from typing import Any

import pandas as pd

from core.utils import first_sentence, write_json


def build_test_set(df: pd.DataFrame, output_path) -> list[dict[str, Any]]:
    """Build and persist a deterministic 10-question ground-truth test set."""
    required_columns = {"paper_id", "title", "summary", "authors_joined", "published", "categories_joined"}
    missing_columns = required_columns - set(df.columns)
    if missing_columns:
        raise ValueError(f"Clean dataframe is missing columns: {sorted(missing_columns)}")
    if len(df) < 10:
        raise ValueError("At least 10 cleaned papers are required to build the test set.")

    question_plan = [
        ("summary", 3),
        ("authors", 3),
        ("date", 2),
        ("categories", 2),
    ]
    test_set: list[dict[str, Any]] = []
    row_index = 0
    for question_type, count in question_plan:
        for _ in range(count):
            row = df.iloc[row_index]
            title = str(row["title"]).strip()
            paper_id = str(row["paper_id"]).strip()
            if question_type == "summary":
                question = f"What is the summary of the paper '{title}'?"
                ground_truth = first_sentence(str(row["summary"]))
            elif question_type == "authors":
                question = f"Who are the authors of the paper '{title}'?"
                ground_truth = str(row["authors_joined"]).strip()
            elif question_type == "date":
                question = f"When was the paper '{title}' published?"
                ground_truth = str(row["published"]).strip()
            else:
                question = f"What are the subject categories of the paper '{title}'?"
                ground_truth = str(row["categories_joined"]).strip() or "Not specified in Crossref metadata."
            test_set.append(
                {
                    "id": f"eval_{len(test_set) + 1:03d}",
                    "question_type": question_type,
                    "question": question,
                    "ground_truth": ground_truth,
                    "ground_truth_doc_ids": [paper_id],
                }
            )
            row_index += 1

    write_json(output_path, test_set)
    return test_set
