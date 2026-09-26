from __future__ import annotations

from typing import Any
import json
import os
import re
import pandas as pd


def _get_first_sentence(text: str) -> str:
    """Trích xuất câu đầu tiên kết thúc bằng dấu chấm, hỏi chấm hoặc chấm than."""
    text = (text or "").strip()
    if not text:
        return ""
    # Tìm câu đầu tiên kết thúc bởi ., ?, hoặc !
    match = re.search(r"^(.*?[.!?])(?:\s|$)", text, flags=re.DOTALL)
    if match:
        return match.group(1).strip()
    return text.split("\n")[0].strip()


def _format_date(val: Any) -> str:
    """Chuẩn hóa ngày xuất bản về định dạng YYYY-MM-DD."""
    if pd.isna(val):
        return ""
    if hasattr(val, "strftime"):
        return val.strftime("%Y-%m-%d")
    val_str = str(val).strip()
    return val_str[:10]


def build_test_set(df: pd.DataFrame, output_path: str) -> list[dict[str, Any]]:
    """Tạo bộ evaluation benchmark gồm đúng 10 câu hỏi phân bổ đều 4 dạng bài toán:
    summary, authors, date, categories.
    """
    test_set: list[dict[str, Any]] = []

    if df.empty:
        return test_set

    # 4 dạng bài toán xoay vòng đều qua các mẫu:
    # Thứ tự phân bổ 10 câu: 3 summary, 3 authors, 2 date, 2 categories
    question_types = [
        "summary",     # eval_001
        "authors",     # eval_002
        "date",        # eval_003
        "categories",  # eval_004
        "summary",     # eval_005
        "authors",     # eval_006
        "date",        # eval_007
        "categories",  # eval_008
        "summary",     # eval_009
        "authors",     # eval_010
    ]

    total_rows = len(df)

    for i, q_type in enumerate(question_types):
        eval_id = f"eval_{i+1:03d}"
        # Lấy dòng tương ứng từ DataFrame (vòng lặp an toàn nếu số dòng < 10)
        row = df.iloc[i % total_rows]
        
        doc_id = str(row["paper_id"])
        title = str(row["title"]).strip()

        if q_type == "summary":
            question = f"What is the summary of the paper '{title}'?"
            ground_truth = _get_first_sentence(row.get("summary", ""))

        elif q_type == "authors":
            question = f"Who are the authors of the paper '{title}'?"
            ground_truth = str(row.get("authors_joined", "")).strip()

        elif q_type == "date":
            question = f"When was the paper '{title}' published?"
            ground_truth = _format_date(row.get("published", ""))

        elif q_type == "categories":
            question = f"What are the categories of the paper '{title}'?"
            ground_truth = str(row.get("categories_joined", "")).strip()

        test_set.append({
            "id": eval_id,
            "question_type": q_type,
            "question": question,
            "ground_truth": ground_truth,
            "ground_truth_doc_ids": [doc_id],
        })

    # Đảm bảo lưu đúng đường dẫn
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(test_set, f, ensure_ascii=False, indent=2)

    return test_set