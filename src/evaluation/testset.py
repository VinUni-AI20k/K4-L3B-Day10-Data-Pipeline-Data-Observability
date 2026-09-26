from __future__ import annotations

from typing import Any

import pandas as pd

from core.utils import first_sentence, write_json


PREFERRED_PAPER_IDS = [
    "10.1145/3637528.3671801",
    "10.1145/3637528.3671802",
    "10.1145/3637528.3671803",
    "10.1145/3637528.3671804",
    "10.1145/3637528.3671805",
    "10.1145/3637528.3671806",
    "10.1145/3637528.3671807",
    "10.1145/3637528.3671808",
    "10.1145/3637528.3671809",
    "10.1145/3637528.3671810",
]

QUESTION_TYPES = [
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
]


def _select_papers(df: pd.DataFrame, count: int) -> list[pd.Series]:
    by_id = {str(row["paper_id"]): row for _, row in df.iterrows()}
    selected: list[pd.Series] = []
    seen: set[str] = set()
    for paper_id in PREFERRED_PAPER_IDS:
        row = by_id.get(paper_id)
        if row is None:
            continue
        selected.append(row)
        seen.add(paper_id)
        if len(selected) >= count:
            return selected
    for _, row in df.iterrows():
        paper_id = str(row["paper_id"])
        if paper_id in seen:
            continue
        selected.append(row)
        seen.add(paper_id)
        if len(selected) >= count:
            break
    return selected


def _question_for(question_type: str, row: pd.Series) -> dict[str, str]:
    title = str(row["title"])
    if question_type == "summary":
        return {
            "question": f"Summarize the paper '{title}'.",
            "ground_truth": first_sentence(str(row["summary"])),
        }
    if question_type == "authors":
        return {
            "question": f"Who authored '{title}'?",
            "ground_truth": str(row["authors_joined"]),
        }
    if question_type == "date":
        return {
            "question": f"When was '{title}' published?",
            "ground_truth": str(row["published"]),
        }
    if question_type == "categories":
        return {
            "question": f"What categories does the paper '{title}' belong to?",
            "ground_truth": str(row["categories_joined"]),
        }
    raise ValueError(f"Unsupported question type: {question_type}")


def build_test_set(df: pd.DataFrame, output_path) -> list[dict[str, Any]]:
    """Build a 10-question benchmark covering summary, authors, date, and categories."""
    if len(df) < 4:
        raise ValueError("Need at least 4 cleaned documents to build the evaluation set.")

    papers = _select_papers(df, count=10)
    if len(papers) < 4:
        raise ValueError("Could not select enough representative papers for the evaluation set.")

    items: list[dict[str, Any]] = []
    for index in range(10):
        row = papers[index % len(papers)]
        question_type = QUESTION_TYPES[index]
        payload = _question_for(question_type, row)
        items.append(
            {
                "id": f"q{index + 1:02d}-{question_type}",
                "question_type": question_type,
                "question": payload["question"],
                "ground_truth": payload["ground_truth"],
                "ground_truth_doc_ids": [str(row["paper_id"])],
            }
        )

    write_json(output_path, items)
    return items
