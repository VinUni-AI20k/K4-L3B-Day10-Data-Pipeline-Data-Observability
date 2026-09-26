from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import pandas as pd


# Phan bo 10 cau hoi cho 4 loai: summary=3, authors=3, date=2, categories=2
_QUESTION_DISTRIBUTION: dict[str, int] = {
    "summary": 3,
    "authors": 3,
    "date": 2,
    "categories": 2,
}


def _pick_rows(df: pd.DataFrame, n: int) -> pd.DataFrame:
    """Chon n hang phan bo deu, uu tien cac hang co summary dai."""
    if "summary_chars" in df.columns:
        df_sorted = df.sort_values("summary_chars", ascending=False)
    else:
        df_sorted = df.copy()
    # Lay cac chi so phan bo deu tren toan bo dataframe
    total = len(df_sorted)
    step = max(1, total // n)
    indices = [min(i * step, total - 1) for i in range(n)]
    return df_sorted.iloc[indices].reset_index(drop=True)


def _make_summary_question(row: pd.Series, idx: int) -> dict[str, Any]:
    title = str(row.get("title", "")).strip()
    summary = str(row.get("summary", "")).strip()
    # Ground truth: cau dau tien cua summary
    first_sentence = summary.split(".")[0].strip() + "." if "." in summary else summary[:200]
    return {
        "id": f"eval_{idx:03d}",
        "question_type": "summary",
        "question": f"What is the summary of the paper '{title}'?",
        "ground_truth": first_sentence,
        "ground_truth_doc_ids": [str(row.get("paper_id", ""))],
    }


def _make_authors_question(row: pd.Series, idx: int) -> dict[str, Any]:
    title = str(row.get("title", "")).strip()
    authors = row.get("authors", [])
    if isinstance(authors, list):
        authors_str = ", ".join(authors) if authors else "Unknown"
    else:
        authors_str = str(row.get("authors_joined", "")).strip() or "Unknown"
    return {
        "id": f"eval_{idx:03d}",
        "question_type": "authors",
        "question": f"Who are the authors of the paper '{title}'?",
        "ground_truth": authors_str,
        "ground_truth_doc_ids": [str(row.get("paper_id", ""))],
    }


def _make_date_question(row: pd.Series, idx: int) -> dict[str, Any]:
    title = str(row.get("title", "")).strip()
    published = str(row.get("published", "")).strip()
    ground_truth = published[:10] if published else "Unknown"
    return {
        "id": f"eval_{idx:03d}",
        "question_type": "date",
        "question": f"When was the paper '{title}' published?",
        "ground_truth": ground_truth,
        "ground_truth_doc_ids": [str(row.get("paper_id", ""))],
    }


def _make_categories_question(row: pd.Series, idx: int) -> dict[str, Any]:
    title = str(row.get("title", "")).strip()
    categories = row.get("categories", [])
    if isinstance(categories, list):
        categories_str = ", ".join(categories) if categories else str(row.get("primary_category", "Unknown"))
    else:
        categories_str = str(row.get("categories_joined", "")).strip() or "Unknown"
    return {
        "id": f"eval_{idx:03d}",
        "question_type": "categories",
        "question": f"What are the research categories of the paper '{title}'?",
        "ground_truth": categories_str,
        "ground_truth_doc_ids": [str(row.get("paper_id", ""))],
    }


_BUILDERS = {
    "summary": _make_summary_question,
    "authors": _make_authors_question,
    "date": _make_date_question,
    "categories": _make_categories_question,
}


def build_test_set(df: pd.DataFrame, output_path) -> list[dict[str, Any]]:
    """Tao bo evaluation set tu cleaned dataframe.

    1. Kiem tra so luong document toi thieu (can >= 4 rows).
    2. Chon cac paper dai dien, phan bo deu.
    3. Tao 10 cau hoi ground-truth thuoc 4 loai:
       - summary  (3 cau)
       - authors  (3 cau)
       - date     (2 cau)
       - categories (2 cau)
    4. Moi phan tu co: id, question_type, question, ground_truth, ground_truth_doc_ids.
    5. Ghi file JSON vao output_path.
    """
    if df.empty or len(df) < 4:
        raise ValueError(f"DataFrame can co it nhat 4 rows, hien tai chi co {len(df)}.")

    test_set: list[dict[str, Any]] = []
    counter = 1

    for q_type, n_questions in _QUESTION_DISTRIBUTION.items():
        builder = _BUILDERS[q_type]
        sampled = _pick_rows(df, n_questions)
        for _, row in sampled.iterrows():
            item = builder(row, counter)
            test_set.append(item)
            counter += 1

    # Ghi file JSON ra output_path
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(test_set, f, ensure_ascii=False, indent=2)

    return test_set

