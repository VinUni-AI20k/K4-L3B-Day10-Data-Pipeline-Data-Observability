
from __future__ import annotations

from typing import Any
import great_expectations as gx
import pandas as pd
import json
from core.config import Settings


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    """TODO(student): tao bo data quality checks.

    Pseudo-code:
    1. Check row count.
    2. Check `paper_id` not null va unique.
    3. Check `title` not null.
    4. Check do dai `summary`.
    5. Check freshness bang `age_days`.
    6. Ghi ket qua vao `data/quality/`.
    """
    context = gx.get_context(mode="ephemeral")
    data_source = context.data_sources.add_pandas(name="papers_source")
    data_asset = data_source.add_dataframe_asset(name="papers_asset")
    batch_def = data_asset.add_batch_definition_whole_dataframe("papers_batch")
    batch = batch_def.get_batch(batch_parameters={"dataframe": df})
    
    suite = context.suites.add(gx.ExpectationSuite(name="papers_suite"))
    
    # Các quy tắc (Expectations) thiết yếu
    suite.add_expectation(gx.expectations.ExpectTableRowCountToBeBetween(min_value=1, max_value=100000))
    suite.add_expectation(gx.expectations.ExpectColumnValuesToNotBeNull(column="paper_id"))
    suite.add_expectation(gx.expectations.ExpectColumnValuesToBeUnique(column="paper_id"))
    suite.add_expectation(gx.expectations.ExpectColumnValueLengthsToBeBetween(column="summary", min_value=10))
    
    validation_result = batch.validate(suite)
    res = validation_result.to_json_dict()
    
    # Ghi kết quả
    out_path = settings.paths.data_dir / "quality" / f"{report_name}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=2)
        
    return res


def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path) -> dict[str, Any]:
    """TODO(student): tong hop freshness report.

    Pseudo-code:
    1. Tim latest va oldest published date.
    2. Dem so dong stale.
    3. Tao payload:
       - latest_published
       - oldest_published
       - stale_rows
       - total_rows
       - is_fresh
    4. Ghi JSON report.
    """
    raise NotImplementedError("Student task: implement freshness reporting.")
    if df.empty:
        payload = {
            "latest_published": None,
            "oldest_published": None,
            "stale_rows": 0,
            "total_rows": 0,
            "is_fresh": False
        }
    else:
        latest = df['published'].max()
        oldest = df['published'].min()
        stale_rows = len(df[df['age_days'] > 180])
        total_rows = len(df)
        
        # Tiêu chí: Dữ liệu tươi nếu số lượng bài cũ > 180 ngày không vượt quá 25%
        is_fresh = (stale_rows / total_rows) <= 0.25 if total_rows > 0 else False
        
        payload = {
            "latest_published": latest.isoformat() if pd.notnull(latest) else None,
            "oldest_published": oldest.isoformat() if pd.notnull(oldest) else None,
            "stale_rows": stale_rows,
            "total_rows": total_rows,
            "is_fresh": is_fresh
        }
        
    out_path = settings.paths.data_dir / report_path
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        
    return payload
