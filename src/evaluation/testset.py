from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from core.utils import first_sentence, normalize_whitespace, write_json


QUESTION_TYPES = (
    "summary",
    "authors",
    "date",
    "categories",
    "summary",
    "authors",
    "date",
    "categories",
    "summary",
    "authors",
)


def _joined_value(row: pd.Series, joined_column: str, list_column: str) -> str:
    joined = row.get(joined_column, "")
    if isinstance(joined, str) and joined.strip():
        return normalize_whitespace(joined)

    values = row.get(list_column, [])
    if not isinstance(values, (list, tuple)):
        return ""
    return ", ".join(
        normalized
        for value in values
        if (normalized := normalize_whitespace(str(value)))
    )


def _normalized_published(value: Any) -> str:
    if isinstance(value, pd.Timestamp):
        return value.date().isoformat()
    return normalize_whitespace(str(value)) if value is not None else ""


def build_test_set(df: pd.DataFrame, output_path) -> list[dict[str, Any]]:
    """Build a deterministic 10-question benchmark from cleaned papers."""
    required_columns = {"paper_id", "title", "summary", "published"}
    missing_columns = sorted(required_columns - set(df.columns))
    if missing_columns:
        raise ValueError(f"Clean dataframe is missing required columns: {missing_columns}")

    candidates: list[dict[str, str]] = []
    deduplicated = df.drop_duplicates(subset=["paper_id"], keep="first")
    for _, row in deduplicated.iterrows():
        candidate = {
            "paper_id": normalize_whitespace(str(row.get("paper_id", ""))),
            "title": normalize_whitespace(str(row.get("title", ""))),
            "summary": normalize_whitespace(str(row.get("summary", ""))),
            "authors": _joined_value(row, "authors_joined", "authors"),
            "categories": _joined_value(row, "categories_joined", "categories"),
            "published": _normalized_published(row.get("published")),
        }
        if all(candidate.values()):
            candidates.append(candidate)

    if len(candidates) < len(QUESTION_TYPES):
        raise ValueError(
            "At least 10 complete, unique papers are required to build the benchmark; "
            f"found {len(candidates)}."
        )

    # Spread the selected papers across the full cleaned corpus rather than
    # taking only the first ten rows. This remains deterministic for a fixed input.
    last_index = len(candidates) - 1
    selected = [
        candidates[(position * last_index) // (len(QUESTION_TYPES) - 1)]
        for position in range(len(QUESTION_TYPES))
    ]

    test_set: list[dict[str, Any]] = []
    for index, (question_type, paper) in enumerate(zip(QUESTION_TYPES, selected, strict=True), start=1):
        title = paper["title"]
        if question_type == "summary":
            question = f"What is the summary of the paper '{title}'?"
            ground_truth = first_sentence(paper["summary"])
        elif question_type == "authors":
            question = f"Who authored the paper '{title}'?"
            ground_truth = paper["authors"]
        elif question_type == "date":
            question = f"When was the paper '{title}' published?"
            ground_truth = paper["published"]
        else:
            question = f"What categories does the paper '{title}' cover?"
            ground_truth = paper["categories"]

        test_set.append(
            {
                "id": f"eval_{index:03d}",
                "question_type": question_type,
                "question": question,
                "ground_truth": ground_truth,
                "ground_truth_doc_ids": [paper["paper_id"]],
            }
        )

    write_json(Path(output_path), test_set)
    return test_set
