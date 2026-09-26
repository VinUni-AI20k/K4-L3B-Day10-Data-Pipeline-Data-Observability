from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import pandas as pd
import great_expectations as gx
import great_expectations.expectations as gxe

from core.config import Settings

logger = logging.getLogger(__name__)


def evaluate_freshness(df: pd.DataFrame, settings: Settings) -> dict[str, Any]:
    """Đánh giá Freshness SLA theo tỷ lệ bài báo quá hạn (`age_days > 180`).
    
    Quy tắc:
    Cảnh báo `is_fresh = False` nếu tỷ lệ bài báo có `age_days > freshness_threshold_days` vượt quá 25%.
    """
    total_rows = len(df)
    threshold = settings.freshness_threshold_days

    if total_rows == 0:
        return {
            "total_rows": 0,
            "stale_rows": 0,
            "stale_ratio": 0.0,
            "threshold_days": threshold,
            "is_fresh": False,
            "latest_published": "",
            "oldest_published": "",
            "message": "DataFrame rỗng",
        }

    stale_count = int((df["age_days"] > threshold).sum())
    stale_ratio = float(stale_count / total_rows)
    is_fresh = bool(stale_ratio <= 0.25)

    latest_published = str(df["published"].max()) if "published" in df.columns else ""
    oldest_published = str(df["published"].min()) if "published" in df.columns else ""

    return {
        "total_rows": total_rows,
        "stale_rows": stale_count,
        "stale_ratio": round(stale_ratio, 4),
        "threshold_days": threshold,
        "is_fresh": is_fresh,
        "latest_published": latest_published,
        "oldest_published": oldest_published,
        "message": "Fresh" if is_fresh else f"Cảnh báo: {stale_ratio:.1%} bài báo vượt quá {threshold} ngày",
    }


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    """Chạy bộ Data Quality Gate sử dụng Great Expectations 1.x (ephemeral context).

    Định nghĩa 4 Expectations thiết yếu:
    1. ExpectTableRowCountToBeBetween: Số lượng bản ghi nằm trong khoảng [20, 30].
    2. ExpectColumnValuesToNotBeNull: Cột `paper_id` không được phép null.
    3. ExpectColumnValuesToBeUnique: Cột `paper_id` phải là duy nhất.
    4. ExpectColumnValueLengthsToBeBetween: Độ dài `title` phải >= 8 ký tự.
    """
    settings.paths.quality_dir.mkdir(parents=True, exist_ok=True)

    if df.empty:
        result = {
            "report_name": report_name,
            "success": False,
            "total_rows": 0,
            "expectations_evaluated": 0,
            "expectations_passed": 0,
            "expectations_failed": 0,
            "freshness": evaluate_freshness(df, settings),
            "error": "DataFrame rỗng, không thể chạy Quality Gate",
        }
        return result

    # 1. Khởi tạo Ephemeral Context GX 1.x
    context = gx.get_context(mode="ephemeral")
    source_name = f"papers_source_{report_name}"
    data_source = context.data_sources.add_pandas(name=source_name)
    data_asset = data_source.add_dataframe_asset(name="papers_asset")
    batch_def = data_asset.add_batch_definition_whole_dataframe("papers_batch")
    batch = batch_def.get_batch(batch_parameters={"dataframe": df})

    # 2. Định nghĩa 4 Expectations thiết yếu
    expectations = [
        gxe.ExpectTableRowCountToBeBetween(min_value=20, max_value=30),
        gxe.ExpectColumnValuesToNotBeNull(column="paper_id"),
        gxe.ExpectColumnValuesToBeUnique(column="paper_id"),
        gxe.ExpectColumnValueLengthsToBeBetween(column="title", min_value=8),
    ]

    # 3. Tạo Expectation Suite và nạp expectations
    suite_name = f"papers_quality_suite_{report_name}"
    suite = gx.ExpectationSuite(name=suite_name)
    for exp in expectations:
        suite.add_expectation(exp)

    # 4. Thực thi Validation
    validation_results = batch.validate(suite)

    # 5. Đánh giá Freshness SLA
    freshness_info = evaluate_freshness(df, settings)

    # 6. Tổng hợp chi tiết kết quả
    details = []
    passed_count = 0
    failed_count = 0

    for res in validation_results.results:
        exp_type = res.expectation_config.type
        exp_success = bool(res.success)
        if exp_success:
            passed_count += 1
        else:
            failed_count += 1

        details.append({
            "expectation_type": exp_type,
            "success": exp_success,
            "kwargs": res.expectation_config.kwargs,
            "observed_value": res.result.get("observed_value") if hasattr(res, "result") else None,
        })

    # Tiêu chuẩn: GX thành công VÀ đạt Freshness SLA (hoặc chỉ xét GX success tùy yêu cầu)
    gx_success = bool(validation_results.success)

    report_payload = {
        "report_name": report_name,
        "success": gx_success,
        "total_rows": len(df),
        "expectations_evaluated": len(expectations),
        "expectations_passed": passed_count,
        "expectations_failed": failed_count,
        "freshness": freshness_info,
        "details": details,
    }

    # Ghi artifact ra thư mục quality
    report_file = settings.paths.quality_dir / f"{report_name}_quality_report.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report_payload, f, indent=2, ensure_ascii=False)
    logger.info("Đã lưu Quality Report vào %s (status: %s)", report_file, gx_success)

    return report_payload


def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path: Path) -> dict[str, Any]:
    """Tổng hợp và lưu Freshness Report độc lập ra file JSON."""
    freshness = evaluate_freshness(df, settings)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(freshness, f, indent=2, ensure_ascii=False)
    return freshness
