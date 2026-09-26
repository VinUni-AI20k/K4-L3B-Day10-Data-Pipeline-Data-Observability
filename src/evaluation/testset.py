from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd


def build_test_set(df: pd.DataFrame, output_path: Path | str | None = None) -> list[dict[str, Any]]:
    """Tạo bộ benchmark evaluation test set (10 câu hỏi) từ cleaned dataframe.

    Phủ đủ 4 nhóm nghiệp vụ:
    - summary: Câu hỏi về nội dung, đóng góp hoặc phương pháp của bài báo.
    - authors: Câu hỏi về tác giả viết bài báo.
    - date: Câu hỏi về thời gian xuất bản bài báo.
    - categories: Câu hỏi về chủ đề / chuyên ngành nghiên cứu của bài báo.
    """
    if len(df) < 5:
        raise ValueError(f"DataFrame cần tối thiểu 5 tài liệu để sinh test set, nhận được {len(df)}")

    # Lấy các bài báo đại diện từ dataframe sạch
    records = df.to_dict(orient="records")
    test_set: list[dict[str, Any]] = []

    # Nhóm 1: Summary questions (3 câu)
    for i, idx in enumerate([0, 1, 2]):
        row = records[idx]
        test_set.append(
            {
                "id": f"q_summary_{i+1:02d}",
                "question_type": "summary",
                "question": f"Tóm tắt nội dung chính và đóng góp của nghiên cứu '{row['title']}' là gì?",
                "ground_truth": row["summary"],
                "ground_truth_doc_ids": [row["paper_id"]],
            }
        )

    # Nhóm 2: Authors questions (3 câu)
    for i, idx in enumerate([3, 4, 5]):
        row = records[idx]
        test_set.append(
            {
                "id": f"q_authors_{i+1:02d}",
                "question_type": "authors",
                "question": f"Những tác giả nào đã thực hiện bài báo khoa học '{row['title']}'?",
                "ground_truth": row["authors_joined"],
                "ground_truth_doc_ids": [row["paper_id"]],
            }
        )

    # Nhóm 3: Date questions (2 câu)
    for i, idx in enumerate([6, 7]):
        row = records[idx]
        test_set.append(
            {
                "id": f"q_date_{i+1:02d}",
                "question_type": "date",
                "question": f"Bài báo nghiên cứu '{row['title']}' được công bố vào ngày tháng năm nào?",
                "ground_truth": str(row["published"]),
                "ground_truth_doc_ids": [row["paper_id"]],
            }
        )

    # Nhóm 4: Categories questions (2 câu)
    for i, idx in enumerate([8, 9]):
        row = records[idx]
        test_set.append(
            {
                "id": f"q_categories_{i+1:02d}",
                "question_type": "categories",
                "question": f"Lĩnh vực hoặc phân loại nghiên cứu chính của bài báo '{row['title']}' là gì?",
                "ground_truth": row["categories_joined"] or row.get("primary_category", ""),
                "ground_truth_doc_ids": [row["paper_id"]],
            }
        )

    if output_path is not None:
        target_path = Path(output_path)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        with open(target_path, "w", encoding="utf-8") as f:
            json.dump(test_set, f, indent=2, ensure_ascii=False)

    return test_set
