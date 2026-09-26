from __future__ import annotations

from typing import Any
import json
import os
import pandas as pd


def build_test_set(df: pd.DataFrame, output_path) -> list[dict[str, Any]]:
   """TODO(student): tao bo evaluation set tu cleaned dataframe.

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
   test_set = []
    
   if len(df) == 0:
        return test_set
        
    # Lấy sample một số bài (vd: 5 bài) để tạo 10 câu hỏi (mỗi bài 2 câu)
   sample_df = df.head(5) if len(df) >= 5 else df
   
   for i, row in sample_df.iterrows():
      doc_id = row['paper_id']
      
      # Câu hỏi về Summary
      test_set.append({
         "id": f"q_sum_{doc_id}",
         "question_type": "summary",
         "question": f"What is the summary of the paper titled '{row['title']}'?",
         "ground_truth": row['summary'],
         "ground_truth_doc_ids": [doc_id]
      })
      
      # Câu hỏi về Authors
      test_set.append({
         "id": f"q_auth_{doc_id}",
         "question_type": "authors",
         "question": f"Who are the authors of the paper titled '{row['title']}'?",
         "ground_truth": row['authors_joined'],
         "ground_truth_doc_ids": [doc_id]
      })
      
      # Ngừng nếu đủ 10 câu
      if len(test_set) >= 10:
         break
         
   # Chốt 10 câu
   test_set = test_set[:10]
   
   # Save to file
   os.makedirs(os.path.dirname(output_path), exist_ok=True)
   with open(output_path, 'w', encoding='utf-8') as f:
      json.dump(test_set, f, ensure_ascii=False, indent=2)
      
   return test_set

