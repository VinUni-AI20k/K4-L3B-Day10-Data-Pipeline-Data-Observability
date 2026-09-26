from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from core.utils import first_sentence, write_json


def build_test_set(df: pd.DataFrame, output_path: Path | str | None = None) -> list[dict[str, Any]]:
    """Tao bo evaluation set tu cleaned dataframe.

    Pseudo-code:
    1. Kiem tra so luong document toi thieu.
    2. Chon mot so paper dai dien.
    3. Tao nhieu loai cau hoi:
       - summary
       - authors
       - date
       - categories
    4. Moi row can co:
       - id
       - question_type
       - question
       - ground_truth
       - ground_truth_doc_ids
    5. Ghi file JSON vao output_path.
    """
    if len(df) < 4:
        raise ValueError("DataFrame phai co it nhat 4 ban ghi de tao bo test set da dang.")

    specs = [
        ("summary", "What is the summary of the paper '{title}'?", lambda r: first_sentence(str(r["summary"]))),
        ("authors", "Who authored the paper '{title}'?", lambda r: str(r["authors_joined"])),
        ("date", "When was the paper '{title}' published?", lambda r: str(r["published"])),
        ("categories", "What categories belong to the paper '{title}'?", lambda r: str(r["categories_joined"])),
        ("summary", "What is the summary of the paper '{title}'?", lambda r: first_sentence(str(r["summary"]))),
        ("authors", "Who authored the paper '{title}'?", lambda r: str(r["authors_joined"])),
        ("date", "When was the paper '{title}' published?", lambda r: str(r["published"])),
        ("categories", "What categories belong to the paper '{title}'?", lambda r: str(r["categories_joined"])),
        ("summary", "What is the summary of the paper '{title}'?", lambda r: first_sentence(str(r["summary"]))),
        ("authors", "Who authored the paper '{title}'?", lambda r: str(r["authors_joined"])),
    ]

    test_set: list[dict[str, Any]] = []
    total_rows = len(df)

    for i, (q_type, tmpl, gt_fn) in enumerate(specs):
        row = df.iloc[i % total_rows]
        title = str(row["title"]).strip()
        test_set.append(
            {
                "id": f"eval_{i+1:03d}",
                "question_type": q_type,
                "question": tmpl.format(title=title),
                "ground_truth": gt_fn(row),
                "ground_truth_doc_ids": [str(row["paper_id"])],
            }
        )

    if output_path is not None:
        out_p = Path(output_path)
        write_json(out_p, test_set)

    return test_set
