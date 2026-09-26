from __future__ import annotations

from pathlib import Path
from typing import Any

import great_expectations as gx
import great_expectations.expectations as gxe
import pandas as pd

from core.config import Settings
from core.utils import write_json


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    """Chạy bộ Data Quality Gate với Great Expectations 1.x (Ephemeral Context) và Freshness SLA.

    Quy trình:
    1. Cấu hình Ephemeral context, Pandas data source & dataframe asset.
    2. Định nghĩa 4 Expectations thiết yếu:
       - ExpectTableRowCountToBeBetween: 20 <= số dòng <= 30
       - ExpectColumnValuesToNotBeNull: paper_id, title, summary, text_for_embedding
       - ExpectColumnValuesToBeUnique: paper_id
       - ExpectColumnValueLengthsToBeBetween: title >= 8 ký tự, summary >= 20 ký tự
    3. Đánh giá Freshness SLA bằng age_days (cảnh báo nếu >25% bài quá 180 ngày).
    4. Ghi kết quả kiểm tra vào data/quality/.
    """
    context = gx.get_context(mode="ephemeral")
    data_source = context.data_sources.add_pandas(name=f"papers_source_{report_name}")
    data_asset = data_source.add_dataframe_asset(name=f"papers_asset_{report_name}")
    batch_def = data_asset.add_batch_definition_whole_dataframe(f"papers_batch_{report_name}")
    batch = batch_def.get_batch(batch_parameters={"dataframe": df})

    suite = gx.ExpectationSuite(name=f"papers_{report_name}_suite")

    # 1. ExpectTableRowCountToBeBetween
    suite.add_expectation(gxe.ExpectTableRowCountToBeBetween(min_value=20, max_value=30))

    # 2. ExpectColumnValuesToNotBeNull
    for col in ["paper_id", "title", "summary", "text_for_embedding"]:
        if col in df.columns:
            suite.add_expectation(gxe.ExpectColumnValuesToNotBeNull(column=col))

    # 3. ExpectColumnValuesToBeUnique
    if "paper_id" in df.columns:
        suite.add_expectation(gxe.ExpectColumnValuesToBeUnique(column="paper_id"))

    # 4. ExpectColumnValueLengthsToBeBetween
    if "title" in df.columns:
        suite.add_expectation(gxe.ExpectColumnValueLengthsToBeBetween(column="title", min_value=8))
    if "summary" in df.columns:
        suite.add_expectation(gxe.ExpectColumnValueLengthsToBeBetween(column="summary", min_value=20))

    validation_result = batch.validate(suite)

    # Đánh giá Freshness SLA
    freshness_path = (
        settings.paths.freshness_report
        if report_name == "baseline"
        else settings.paths.quality_dir / f"{report_name}_freshness_report.json"
    )
    freshness_payload = build_freshness_report(df, settings, freshness_path)
    is_fresh = freshness_payload["is_fresh"]

    overall_success = bool(validation_result.success and is_fresh)

    # Xác định đường dẫn file báo cáo
    if report_name == "baseline":
        report_output_path = settings.paths.baseline_quality_report
    elif report_name == "corrupted":
        report_output_path = settings.paths.corrupted_quality_report
    elif report_name.endswith(".json"):
        report_output_path = Path(report_name)
    else:
        report_output_path = settings.paths.quality_dir / f"{report_name}_quality_report.json"

    val_dict = validation_result.to_json_dict()

    report_payload = {
        "report_name": str(report_name),
        "success": overall_success,
        "gx_success": bool(validation_result.success),
        "is_fresh": bool(is_fresh),
        "statistics": val_dict.get("statistics", {}),
        "freshness": freshness_payload,
        "evaluated_expectations_count": len(validation_result.results),
        "successful_expectations_count": sum(1 for r in validation_result.results if r.success),
        "unsuccessful_expectations_count": sum(1 for r in validation_result.results if not r.success),
        "details": val_dict,
    }

    write_json(report_output_path, report_payload)
    return report_payload


def build_freshness_report(
    df: pd.DataFrame, settings: Settings, report_path: Path | str | None = None
) -> dict[str, Any]:
    """Tổng hợp báo cáo Freshness SLA theo age_days.

    Quy tắc SLA:
    - Ngưỡng quá hạn: settings.freshness_threshold_days (180 ngày).
    - Cảnh báo vi phạm (is_fresh = False) nếu tỷ lệ bài báo có age_days > 180 vượt quá 25%.
    """
    total_rows = len(df)
    threshold = settings.freshness_threshold_days

    published_series = (
        df["published"].dropna() if "published" in df.columns and not df.empty else pd.Series(dtype=object)
    )
    latest_published = str(published_series.max()) if not published_series.empty else "N/A"
    oldest_published = str(published_series.min()) if not published_series.empty else "N/A"

    stale_rows = int((df["age_days"] > threshold).sum()) if "age_days" in df.columns and not df.empty else 0
    stale_ratio = float(stale_rows / total_rows) if total_rows > 0 else 0.0
    stale_pct = round(stale_ratio * 100, 2)
    is_fresh = stale_ratio <= 0.25

    payload = {
        "latest_published": latest_published,
        "oldest_published": oldest_published,
        "stale_rows": stale_rows,
        "total_rows": total_rows,
        "stale_ratio": stale_ratio,
        "stale_percentage": stale_pct,
        "threshold_days": threshold,
        "max_stale_ratio_allowed": 0.25,
        "is_fresh": is_fresh,
    }

    if report_path is not None:
        write_json(Path(report_path), payload)

    return payload
