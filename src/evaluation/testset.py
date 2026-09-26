from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from core.utils import compact_join, first_sentence, write_json


def _to_text(val: Any) -> str:
    if isinstance(val, (list, tuple)):
        return compact_join(str(x) for x in val)
    return str(val).strip() if val is not None else ""


def build_test_set(df: pd.DataFrame, output_path: Path | str) -> list[dict[str, Any]]:
    """Tạo bộ benchmark evaluation set (10 câu hỏi) từ cleaned dataframe.

    Bao phủ 4 nhóm nghiệp vụ thiết yếu:
    - summary: Kiểm tra khả năng tóm tắt ý chính bài báo.
    - authors: Kiểm tra trích xuất chính xác danh sách tác giả.
    - date: Kiểm tra truy vấn thời gian xuất bản.
    - categories: Kiểm tra phân loại chủ đề chuyên ngành.

    Mỗi mẫu kiểm thử bao gồm:
    - id: Mã định danh câu hỏi (q_01 -> q_10)
    - question_type: Nhóm nghiệp vụ (summary, authors, date, categories)
    - question: Câu hỏi có trích dẫn tên bài báo trong nháy đơn
    - ground_truth: Câu trả lời chuẩn
    - ground_truth_doc_ids: Danh sách paper_id chuẩn làm ground truth retrieval
    """
    if df.empty:
        raise ValueError("DataFrame cannot be empty to build evaluation test set.")

    total_available = len(df)
    test_set: list[dict[str, Any]] = []

    # 10 câu hỏi bao phủ 4 nhóm: 3 summary, 3 authors, 2 date, 2 categories
    question_specs: list[tuple[str, str, Any]] = [
        ("summary", "What is the summary of '{title}'?", lambda r: first_sentence(_to_text(r["summary"]))),
        (
            "authors",
            "Who authored '{title}'?",
            lambda r: _to_text(r.get("authors_joined") if "authors_joined" in r else r.get("authors")),
        ),
        ("date", "When was '{title}' published?", lambda r: _to_text(r["published"])),
        (
            "categories",
            "What categories are associated with '{title}'?",
            lambda r: _to_text(r.get("categories_joined") if "categories_joined" in r else r.get("categories")),
        ),
        ("summary", "What is the summary of '{title}'?", lambda r: first_sentence(_to_text(r["summary"]))),
        (
            "authors",
            "Who authored '{title}'?",
            lambda r: _to_text(r.get("authors_joined") if "authors_joined" in r else r.get("authors")),
        ),
        ("date", "When was '{title}' published?", lambda r: _to_text(r["published"])),
        (
            "categories",
            "What categories are associated with '{title}'?",
            lambda r: _to_text(r.get("categories_joined") if "categories_joined" in r else r.get("categories")),
        ),
        ("summary", "What is the summary of '{title}'?", lambda r: first_sentence(_to_text(r["summary"]))),
        (
            "authors",
            "Who authored '{title}'?",
            lambda r: _to_text(r.get("authors_joined") if "authors_joined" in r else r.get("authors")),
        ),
    ]

    for idx, (q_type, template, gt_fn) in enumerate(question_specs):
        row_idx = idx if idx < total_available else (idx % total_available)
        row = df.iloc[row_idx]
        title = _to_text(row["title"])
        question = template.format(title=title)
        ground_truth = gt_fn(row)

        test_set.append(
            {
                "id": f"q_{idx + 1:02d}",
                "question_type": q_type,
                "question": question,
                "ground_truth": ground_truth,
                "ground_truth_doc_ids": [str(row["paper_id"])],
            }
        )

    out_p = Path(output_path)
    write_json(out_p, test_set)
    return test_set
