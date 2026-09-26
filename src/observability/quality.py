from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import great_expectations as gx
import great_expectations.expectations as gxe
import pandas as pd

from core.config import Settings


def evaluate_freshness_sla(df: pd.DataFrame, settings: Settings) -> dict[str, Any]:
    """Đánh giá độ tươi mới (Freshness SLA) của tập dữ liệu dựa trên cột `age_days`.
    
    Quy tắc:
    - Bài báo có `age_days > settings.freshness_threshold_days` (mặc định 180 ngày) được coi là cũ (stale).
    - Nếu tỷ lệ bài cũ >= 25% (hoặc tập dữ liệu rỗng), `is_fresh = False`.
    """
    total_rows = len(df)
    freshness_threshold = getattr(settings, "freshness_threshold_days", 180)

    if total_rows == 0:
        return {
            "total_rows": 0,
            "stale_rows": 0,
            "stale_ratio": 0.0,
            "threshold_days": freshness_threshold,
            "is_fresh": False,
        }

    # Đếm số lượng bài viết bị coi là quá hạn (stale)
    if "age_days" in df.columns:
        stale_rows = int((df["age_days"] > freshness_threshold).sum())
    else:
        stale_rows = 0

    stale_ratio = stale_rows / total_rows

    # Vi phạm SLA nếu 25% bài báo trở lên là cũ
    is_fresh = bool(stale_ratio < 0.25)

    return {
        "total_rows": total_rows,
        "stale_rows": stale_rows,
        "stale_ratio": round(stale_ratio, 4),
        "threshold_days": freshness_threshold,
        "is_fresh": is_fresh,
    }


def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path: Path | str | None = None) -> dict[str, Any]:
    """Tổng hợp freshness report chi tiết và lưu ra file JSON."""
    sla = evaluate_freshness_sla(df, settings)

    latest_published = str(df["published"].max()) if not df.empty and "published" in df.columns else None
    oldest_published = str(df["published"].min()) if not df.empty and "published" in df.columns else None

    report = {
        "latest_published": latest_published,
        "oldest_published": oldest_published,
        "stale_rows": sla["stale_rows"],
        "total_rows": sla["total_rows"],
        "stale_ratio": sla["stale_ratio"],
        "threshold_days": sla["threshold_days"],
        "is_fresh": sla["is_fresh"],
    }

    if report_path is not None:
        target_path = Path(report_path)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        with open(target_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

    return report


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    """Chốt kiểm soát chất lượng dữ liệu sử dụng Great Expectations 1.x Ephemeral Context.

    Kiểm định 4 hàng rào bắt buộc:
    1. Số lượng bản ghi nằm trong khoảng [5, 5000] dòng
    2. Các trường `paper_id`, `title`, `text_for_embedding` không được null
    3. `paper_id` phải là unique (không trùng lặp)
    4. `summary` tối thiểu 30 ký tự

    Kết hợp đánh giá Freshness SLA (`evaluate_freshness_sla`).
    """
    # -------------------------------------------------------------
    # 1. Khởi tạo GX 1.x Ephemeral Context & Data Asset
    # -------------------------------------------------------------
    context = gx.get_context(mode="ephemeral")
    # Đặt tên data source duy nhất theo report_name để tránh trùng lặp
    source_name = f"papers_source_{report_name}"
    data_source = context.data_sources.add_pandas(name=source_name)
    data_asset = data_source.add_dataframe_asset(name="papers_asset")
    batch_def = data_asset.add_batch_definition_whole_dataframe("papers_batch")
    batch = batch_def.get_batch(batch_parameters={"dataframe": df})

    # -------------------------------------------------------------
    # 2. Định nghĩa Expectation Suite với 4 hàng rào kiểm định
    # -------------------------------------------------------------
    suite = gx.ExpectationSuite(name=f"papers_quality_suite_{report_name}")

    # Hàng rào 1: Số lượng bản ghi nằm trong 5 - 5000 dòng
    suite.add_expectation(
        gxe.ExpectTableRowCountToBeBetween(min_value=5, max_value=5000)
    )

    # Hàng rào 2: paper_id, title, text_for_embedding không được null
    suite.add_expectation(
        gxe.ExpectColumnValuesToNotBeNull(column="paper_id")
    )
    suite.add_expectation(
        gxe.ExpectColumnValuesToNotBeNull(column="title")
    )
    suite.add_expectation(
        gxe.ExpectColumnValuesToNotBeNull(column="text_for_embedding")
    )

    # Hàng rào 3: paper_id là unique
    suite.add_expectation(
        gxe.ExpectColumnValuesToBeUnique(column="paper_id")
    )

    # Hàng rào 4: summary có độ dài tối thiểu 30 ký tự
    suite.add_expectation(
        gxe.ExpectColumnValueLengthsToBeBetween(column="summary", min_value=30)
    )

    # -------------------------------------------------------------
    # 3. Tiến hành kiểm định (Validation)
    # -------------------------------------------------------------
    validation_result = batch.validate(suite)
    gx_success = bool(validation_result.success)

    # -------------------------------------------------------------
    # 4. Kiểm định độ tươi mới (Freshness SLA)
    # -------------------------------------------------------------
    freshness = evaluate_freshness_sla(df, settings)

    # -------------------------------------------------------------
    # 5. Tổng hợp kết quả và xuất báo cáo vào data/quality/
    # -------------------------------------------------------------
    # Xác định đường dẫn file báo cáo
    if report_name == "baseline":
        report_file = settings.paths.baseline_quality_report
    elif report_name == "corrupted":
        report_file = settings.paths.corrupted_quality_report
    else:
        report_file = settings.paths.quality_dir / f"{report_name}_quality_report.json"

    result: dict[str, Any] = {
        "success": gx_success,
        "report_name": report_name,
        "gx_success": gx_success,
        "freshness": freshness,
        "statistics": {
            "evaluated_expectations": len(suite.expectations),
            "successful_expectations": sum(1 for r in validation_result.results if r.success),
            "unsuccessful_expectations": sum(1 for r in validation_result.results if not r.success),
        },
        "details": validation_result.to_json_dict(),
    }

    # Ghi file kết quả quality check
    report_file.parent.mkdir(parents=True, exist_ok=True)
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    # Cập nhật thêm freshness_report nếu chưa có hoặc cùng lần chạy
    if hasattr(settings.paths, "freshness_report"):
        build_freshness_report(df, settings, settings.paths.freshness_report)

    return result
