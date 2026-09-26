from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from core.utils import first_sentence, normalize_whitespace, write_json


_QUESTION_TYPES = (
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


def _required_text(row: pd.Series, column: str) -> str:
    value = row[column]
    if pd.isna(value):
        return ""
    return normalize_whitespace(str(value))


def _evenly_spaced_positions(size: int, count: int) -> list[int]:
    """Choose deterministic positions spanning the complete ordered corpus."""
    if count == 1:
        return [0]
    return [round(index * (size - 1) / (count - 1)) for index in range(count)]


def build_test_set(df: pd.DataFrame, output_path: str | Path) -> list[dict[str, Any]]:
    """Build and persist a deterministic ten-question evaluation benchmark."""
    required_columns = {
        "paper_id",
        "title",
        "summary",
        "authors_joined",
        "published",
        "categories_joined",
    }
    missing_columns = sorted(required_columns.difference(df.columns))
    if missing_columns:
        raise ValueError(f"Clean dataframe is missing required columns: {', '.join(missing_columns)}")

    candidates = df.copy()
    for column in required_columns:
        candidates = candidates[candidates[column].notna()]
        candidates = candidates[candidates[column].astype(str).str.strip().ne("")]

    if len(candidates) < len(_QUESTION_TYPES):
        raise ValueError(
            "At least 10 complete documents are required to build the evaluation set; "
            f"found {len(candidates)}."
        )

    # Sorting before sampling makes the generated artifact independent of input row order.
    candidates = candidates.sort_values(
        ["published", "paper_id"], ascending=[False, True], kind="stable"
    ).reset_index(drop=True)
    positions = _evenly_spaced_positions(len(candidates), len(_QUESTION_TYPES))
    selected = candidates.iloc[positions]

    test_set: list[dict[str, Any]] = []
    for number, (question_type, (_, row)) in enumerate(
        zip(_QUESTION_TYPES, selected.iterrows(), strict=True), start=1
    ):
        paper_id = _required_text(row, "paper_id")
        title = _required_text(row, "title")

        if question_type == "summary":
            question = f"What is the main idea of '{title}'?"
            ground_truth = first_sentence(_required_text(row, "summary"))
        elif question_type == "authors":
            question = f"Who authored '{title}'?"
            ground_truth = _required_text(row, "authors_joined")
        elif question_type == "date":
            question = f"When was '{title}' published?"
            ground_truth = _required_text(row, "published")
        else:
            question = f"What categories does '{title}' belong to?"
            ground_truth = _required_text(row, "categories_joined")

        test_set.append(
            {
                "id": f"q{number:03d}",
                "question_type": question_type,
                "question": question,
                "ground_truth": ground_truth,
                "ground_truth_doc_ids": [paper_id],
            }
        )

    write_json(Path(output_path), test_set)
    return test_set
