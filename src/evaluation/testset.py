from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from core.utils import first_sentence, write_json


def build_test_set(df: pd.DataFrame, output_path: Path | str) -> list[dict[str, Any]]:
    """Tao bo evaluation set gom 10 cau hoi tu cleaned dataframe phu 4 nhom nghiep vu."""
    if len(df) < 10:
        raise ValueError(f"Dataframe phai co it nhat 10 ban ghi, hien tai co {len(df)}")

    # Chon 10 paper khac nhau de tao 10 cau hoi
    sample_df = df.head(10).reset_index(drop=True)

    # 4 nhom: summary (3), authors (3), date (2), categories (2)
    types_distribution = [
        "summary", "authors", "date", "categories",
        "summary", "authors", "date", "categories",
        "summary", "authors"
    ]

    test_set: list[dict[str, Any]] = []
    for idx, row in sample_df.iterrows():
        q_type = types_distribution[idx]
        title = row["title"]
        paper_id = row["paper_id"]

        if q_type == "summary":
            question = f"What is the summary of the paper '{title}'?"
            ground_truth = first_sentence(row["summary"])
        elif q_type == "authors":
            question = f"Who authored the paper '{title}'?"
            ground_truth = row["authors_joined"]
        elif q_type == "date":
            question = f"When was the paper '{title}' published?"
            ground_truth = str(row["published"])
        elif q_type == "categories":
            question = f"What categories does the paper '{title}' belong to?"
            ground_truth = row["categories_joined"]
        else:
            question = f"What is the summary of the paper '{title}'?"
            ground_truth = first_sentence(row["summary"])

        test_set.append(
            {
                "id": f"q_{idx + 1:02d}",
                "question_type": q_type,
                "question": question,
                "ground_truth": ground_truth,
                "ground_truth_doc_ids": [paper_id],
            }
        )

    out_p = Path(output_path)
    write_json(out_p, test_set)
    return test_set

