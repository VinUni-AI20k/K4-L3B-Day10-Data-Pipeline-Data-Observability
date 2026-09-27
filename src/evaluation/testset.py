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


def validate_test_set(questions: list[dict[str, Any]], df: pd.DataFrame) -> None:
    """Reject a stale or malformed benchmark instead of silently regenerating it."""
    if len(questions) != 10 or len({q.get("id") for q in questions}) != 10:
        raise ValueError("Benchmark must contain ten uniquely identified questions")
    if {q.get("question_type") for q in questions} != {"summary", "authors", "date", "categories"}:
        raise ValueError("Benchmark must cover summary, authors, date and categories")
    by_id = {row["paper_id"]: row for row in df.to_dict(orient="records")}
    for item in questions:
        if not item.get("question") or not item.get("ground_truth") or len(item.get("ground_truth_doc_ids", [])) != 1:
            raise ValueError("Benchmark question/reference must be nonempty and identify one source")
        source = by_id.get(item["ground_truth_doc_ids"][0])
        if source is None:
            raise ValueError(f"Benchmark source is absent: {item['id']}")
        expected = {"summary": first_sentence(source["summary"]), "authors": source["authors_joined"],
                    "date": source["published"], "categories": source["categories_joined"]}[item["question_type"]]
        if item["ground_truth"] != expected:
            raise ValueError(f"Benchmark ground truth disagrees with source: {item['id']}")
