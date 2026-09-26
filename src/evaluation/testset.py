from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from core.utils import first_sentence, write_json


QUESTION_TYPES = ("summary", "authors", "date", "categories")


def build_test_set(df: pd.DataFrame, output_path: Path) -> list[dict[str, Any]]:
    """Build ten reproducible ground-truth questions from distinct clean papers."""
    required = {"paper_id", "title", "summary", "authors_joined", "categories_joined", "published"}
    missing = required.difference(df.columns)
    if missing:
        raise ValueError(f"Clean dataframe is missing columns: {', '.join(sorted(missing))}")

    papers = df.dropna(subset=list(required)).drop_duplicates(subset="paper_id")
    papers = papers.loc[
        papers[list(required)].apply(lambda column: column.astype(str).str.strip().ne("")).all(axis=1)
    ].reset_index(drop=True)
    if len(papers) < 10:
        raise ValueError("At least 10 distinct papers with complete benchmark fields are required")

    # Spread the questions across the input rather than using only adjacent papers.
    selected = papers.iloc[[i * (len(papers) - 1) // 9 for i in range(10)]]
    test_set: list[dict[str, Any]] = []

    for index, (_, paper) in enumerate(selected.iterrows(), start=1):
        question_type = QUESTION_TYPES[(index - 1) % len(QUESTION_TYPES)]
        title = str(paper["title"]).strip()
        if question_type == "summary":
            question = f"What is the summary of the paper '{title}'?"
            ground_truth = first_sentence(str(paper["summary"]))
        elif question_type == "authors":
            question = f"List the authors of the paper '{title}'."
            ground_truth = str(paper["authors_joined"]).strip()
        elif question_type == "date":
            question = f"When was the paper '{title}' published?"
            ground_truth = str(paper["published"]).strip()[:10]
        else:
            question = f"What categories does the paper '{title}' belong to?"
            ground_truth = str(paper["categories_joined"]).strip()

        test_set.append(
            {
                "id": f"eval_{index:03d}",
                "question_type": question_type,
                "question": question,
                "ground_truth": ground_truth,
                "ground_truth_doc_ids": [str(paper["paper_id"]).strip()],
            }
        )

    write_json(Path(output_path), test_set)
    return test_set
