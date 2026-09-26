from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from core.utils import first_sentence, normalize_whitespace, write_json


def build_test_set(df: pd.DataFrame, output_path: Path) -> list[dict[str, Any]]:
    """Build ten reproducible, source-grounded evaluation questions."""
    required = ("paper_id", "title", "summary", "authors_joined", "published", "categories_joined")
    missing = sorted(set(required) - set(df.columns))
    if missing:
        raise ValueError(f"Clean dataframe is missing columns: {', '.join(missing)}")

    papers = []
    seen_ids = set()
    for row in df.to_dict(orient="records"):
        paper = {
            column: normalize_whitespace(row[column]) if isinstance(row[column], str) else ""
            for column in required
        }
        paper_id = paper["paper_id"]
        if (
            not all(paper[column] for column in ("paper_id", "title", "summary", "authors_joined", "published"))
            or paper_id in seen_ids
        ):
            continue
        seen_ids.add(paper_id)
        papers.append(paper)
    if len(papers) < 5:
        raise ValueError("At least five complete, distinct papers are needed for the test set")

    question_types = ["summary", "authors", "date", "categories"] * 2 + ["summary", "authors"]
    used_papers: set[str] = set()
    used_pairs: set[tuple[str, str]] = set()
    test_set = []
    for question_type in question_types:
        candidates = [paper for paper in papers if (question_type, paper["paper_id"]) not in used_pairs]
        if question_type == "categories":
            categorized = [paper for paper in candidates if paper["categories_joined"]]
            if categorized:
                candidates = categorized
        if not candidates:
            raise ValueError(f"Not enough distinct papers for {question_type} questions")
        paper = next((candidate for candidate in candidates if candidate["paper_id"] not in used_papers), candidates[0])
        used_papers.add(paper["paper_id"])
        used_pairs.add((question_type, paper["paper_id"]))

        title = paper["title"]
        if question_type == "summary":
            question = f"What is the summary of the paper '{title}'?"
            ground_truth = first_sentence(paper["summary"])
        elif question_type == "authors":
            question = f"Who authored the paper '{title}'?"
            ground_truth = paper["authors_joined"]
        elif question_type == "date":
            question = f"When was the paper '{title}' published?"
            ground_truth = paper["published"]
        else:
            question = f"What categories are listed for the paper '{title}'?"
            ground_truth = paper["categories_joined"] or "No categories are listed in the Crossref metadata."

        test_set.append({
            "id": f"eval_{len(test_set) + 1:03d}",
            "question_type": question_type,
            "question": question,
            "ground_truth": ground_truth,
            "ground_truth_doc_ids": [paper["paper_id"]],
        })

    write_json(output_path, test_set)
    return test_set
