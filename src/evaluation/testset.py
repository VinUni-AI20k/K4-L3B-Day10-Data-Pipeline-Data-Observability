from __future__ import annotations

from typing import Any

import pandas as pd

from core.utils import first_sentence, write_json


def build_test_set(df: pd.DataFrame, output_path=None) -> list[dict[str, Any]]:
    """Build ten reproducible, source-grounded questions from clean papers."""
    required = ["paper_id", "title", "summary", "authors_joined", "published", "categories_joined"]
    missing = [column for column in required if column not in df]
    if missing:
        raise ValueError(f"Clean dataframe is missing columns: {', '.join(missing)}")

    candidates = df.dropna(subset=required).copy()
    candidates = candidates[
        candidates[required].apply(lambda column: column.astype(str).str.strip().ne("")).all(axis=1)
    ]
    candidates = candidates.drop_duplicates(subset="paper_id").sort_values(
        ["published", "paper_id"], ascending=[False, True]
    ).reset_index(drop=True)
    if len(candidates) < 10:
        raise ValueError("At least ten complete, distinct papers are required for the test set")

    question_types = ["summary", "authors", "date", "categories", "summary",
                      "authors", "date", "categories", "summary", "authors"]
    positions = [index * (len(candidates) - 1) // 9 for index in range(10)]
    questions: list[dict[str, Any]] = []
    for index, (position, question_type) in enumerate(zip(positions, question_types, strict=True), start=1):
        row = candidates.iloc[position]
        title = str(row["title"])
        paper_id = str(row["paper_id"])
        if question_type == "summary":
            question = f"What does the paper '{paper_id}' about {title} describe?"
            ground_truth = first_sentence(str(row["summary"]))
        elif question_type == "authors":
            question = f"Who authored the paper '{paper_id}' about {title}?"
            ground_truth = str(row["authors_joined"])
        elif question_type == "date":
            question = f"When was the paper '{paper_id}' about {title} published?"
            ground_truth = str(row["published"])
        else:
            question = f"What categories describe the paper '{paper_id}' about {title}?"
            ground_truth = str(row["categories_joined"])
        questions.append({
            "id": f"q{index:03d}",
            "question_type": question_type,
            "question": question,
            "ground_truth": ground_truth,
            "ground_truth_doc_ids": [paper_id],
        })

    if output_path is not None:
        write_json(output_path, questions)
    return questions
