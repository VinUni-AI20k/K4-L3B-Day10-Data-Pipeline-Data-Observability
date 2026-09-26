from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from core.utils import first_sentence, write_json


QUESTION_TYPES = ("summary", "authors", "date", "categories")


def build_test_set(df: pd.DataFrame, output_path) -> list[dict[str, Any]]:
    """Build ten reproducible questions from ten distinct clean papers.

    Select evenly across publication dates, including newest and oldest papers.
    Ground truths follow the extractive QA contract: first summary sentence,
    joined authors/categories, and the original publication date string.
    Build once on the baseline; reuse the JSON for corruption and repair.
    """
    required = ("paper_id", "title", "summary", "authors_joined", "categories_joined", "published")
    missing = sorted(set(required) - set(df.columns))
    if missing:
        raise ValueError(f"Benchmark missing required columns: {', '.join(missing)}")
    if len(df) < 10:
        raise ValueError("Benchmark requires at least 10 clean papers.")
    for column in required:
        if not df[column].map(lambda value: isinstance(value, str) and bool(value.strip())).all():
            raise ValueError(f"Benchmark column {column!r} must contain non-empty strings.")
    if df["paper_id"].duplicated().any():
        raise ValueError("Benchmark paper_id values must be unique.")

    papers = df.copy(deep=True)
    papers["_published_at"] = pd.to_datetime(papers["published"], format="ISO8601", utc=True, errors="coerce")
    if papers["_published_at"].isna().any():
        raise ValueError("Benchmark published values must be valid dates.")
    papers = papers.sort_values(["_published_at", "paper_id"], ascending=[False, True]).reset_index(drop=True)
    questions = []
    for number in range(10):
        row = papers.iloc[number * (len(papers) - 1) // 9]
        question_type = QUESTION_TYPES[number % len(QUESTION_TYPES)]
        # qa.py recognizes single-quoted titles/IDs. Apostrophes in a title
        # would break its parser, so use the stable document ID in that case.
        subject = row["title"] if "'" not in row["title"] else row["paper_id"]
        templates = {
            "summary": (f"What is the main finding of '{subject}'?", first_sentence(row["summary"])),
            "authors": (f"Who authored '{subject}'?", row["authors_joined"]),
            "date": (f"When was '{subject}' published?", row["published"]),
            "categories": (f"What categories does '{subject}' belong to?", row["categories_joined"]),
        }
        question, ground_truth = templates[question_type]
        questions.append({
            "id": f"q{number + 1:02d}",
            "question_type": question_type,
            "question": question,
            "ground_truth": ground_truth,
            "ground_truth_doc_ids": [row["paper_id"]],
        })
    write_json(Path(output_path), questions)
    return questions
