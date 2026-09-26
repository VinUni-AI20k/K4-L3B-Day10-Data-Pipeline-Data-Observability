from __future__ import annotations

from typing import Any

import pandas as pd

from core.utils import first_sentence, write_json

QUESTION_TYPES = ["summary", "authors", "date", "categories"]
TARGET_QUESTION_COUNT = 10


def build_test_set(df: pd.DataFrame, output_path) -> list[dict[str, Any]]:
    """Tao bo evaluation set tu cleaned dataframe."""
    if len(df) < 5:
        raise ValueError("Cleaned dataset must contain at least 5 documents to build a test set.")

    sample_size = min(TARGET_QUESTION_COUNT, len(df))
    sample_df = df.head(sample_size).reset_index(drop=True)

    test_set: list[dict[str, Any]] = []
    for index, row in sample_df.iterrows():
        question_type = QUESTION_TYPES[index % len(QUESTION_TYPES)]
        title = row["title"]

        if question_type == "summary":
            question = f"What is the summary of the paper '{title}'?"
            ground_truth = first_sentence(row["summary"])
        elif question_type == "authors":
            question = f"Who are the authors of the paper '{title}'?"
            ground_truth = row["authors_joined"]
        elif question_type == "date":
            question = f"When was the paper '{title}' published?"
            ground_truth = row["published"]
        else:
            question = f"What categories does the paper '{title}' belong to?"
            ground_truth = row["categories_joined"]

        test_set.append(
            {
                "id": f"eval_{index + 1:03d}",
                "question_type": question_type,
                "question": question,
                "ground_truth": ground_truth,
                "ground_truth_doc_ids": [row["paper_id"]],
            }
        )

    write_json(output_path, test_set)
    return test_set
