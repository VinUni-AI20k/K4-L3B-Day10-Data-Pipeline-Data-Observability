from __future__ import annotations

from typing import Any

import pandas as pd

from core.utils import write_json


def build_test_set(df: pd.DataFrame, output_path) -> list[dict[str, Any]]:
    """Build evaluation test set from cleaned dataframe.

    Generates 10 questions covering 4 types:
    - summary   : asks about paper content/topic
    - authors   : asks who authored a paper
    - date      : asks publication date
    - categories: asks about subject categories

    Each item has:
        id, question_type, question, ground_truth, ground_truth_doc_ids
    """
    if len(df) < 5:
        raise ValueError(f"Need at least 5 documents to build a test set, got {len(df)}.")

    # Pick representative papers spread across the corpus
    total = len(df)
    step = max(1, total // 10)
    selected = df.iloc[::step].head(10).reset_index(drop=True)

    test_items: list[dict[str, Any]] = []

    question_specs = [
        # (question_type, question_template, ground_truth_field)
        ("summary",    "What is the main topic of the paper titled '{title}'?",          "summary"),
        ("authors",    "Who authored the paper titled '{title}'?",                        "authors_joined"),
        ("date",       "When was the paper '{title}' published?",                         "published"),
        ("categories", "What categories does the paper '{title}' belong to?",             "categories_joined"),
        ("summary",    "Summarize the contribution of '{title}'.",                        "summary"),
        ("authors",    "List the authors of '{title}'.",                                  "authors_joined"),
        ("date",       "What is the publication date of '{title}'?",                      "published"),
        ("categories", "What subject areas does '{title}' cover?",                        "categories_joined"),
        ("summary",    "Describe the key findings presented in '{title}'.",               "summary"),
        ("authors",    "Who are the researchers behind '{title}'?",                       "authors_joined"),
    ]

    for idx, (q_type, q_template, gt_field) in enumerate(question_specs):
        row = selected.iloc[idx % len(selected)]
        title = str(row["title"])
        ground_truth = str(row[gt_field]) if gt_field in row.index else ""
        paper_id = str(row["paper_id"])

        test_items.append({
            "id": f"q{idx + 1:03d}",
            "question_type": q_type,
            "question": q_template.format(title=title),
            "ground_truth": ground_truth,
            "ground_truth_doc_ids": [paper_id],
        })

    write_json(output_path, test_items)
    return test_items
