from __future__ import annotations

from pathlib import Path
from typing import Any
import great_expectations as gx
import pandas as pd


from core.config import Settings
from core.utils import write_json


def evaluate_freshness_sla(df: pd.DataFrame, settings: Settings) -> dict[str, Any]:
    """Giám sát độ tươi mới (Freshness SLA): Cảnh báo is_fresh = False nếu tỷ lệ bài báo cũ (age_days > 180) > 25%."""
    total_rows = len(df)
    if total_rows == 0:
        return {
            "latest_published": None,
            "oldest_published": None,
            "stale_rows": 0,
            "total_rows": 0,
            "stale_ratio": 0.0,
            "is_fresh": True,
        }

    latest_val = df["published"].max() if "published" in df.columns else None
    oldest_val = df["published"].min() if "published" in df.columns else None
    latest_published = str(latest_val)[:10] if pd.notnull(latest_val) else None
    oldest_published = str(oldest_val)[:10] if pd.notnull(oldest_val) else None

    stale_rows = int((df["age_days"] > settings.freshness_threshold_days).sum()) if "age_days" in df.columns else 0
    stale_ratio = float(stale_rows / total_rows)
    is_fresh = stale_ratio <= 0.25

    return {
        "latest_published": latest_published,
        "oldest_published": oldest_published,
        "stale_rows": stale_rows,
        "total_rows": total_rows,
        "stale_ratio": round(stale_ratio, 4),
        "is_fresh": is_fresh,
    }



def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path: Path | str) -> dict[str, Any]:
    """Tổng hợp và lưu freshness report."""
    payload = evaluate_freshness_sla(df, settings)
    out_path = Path(report_path) if isinstance(report_path, str) else report_path
    write_json(out_path, payload)
    return payload


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, stage: str = "baseline") -> dict[str, Any]:
    """Thiết lập và kiểm định Chốt kiểm soát dữ liệu (Observability Gate) với Great Expectations 1.x."""
    context = gx.get_context(mode="ephemeral")

    source_name = f"papers_source_{stage}"
    asset_name = f"papers_asset_{stage}"
    batch_def_name = f"papers_batch_{stage}"

    data_source = context.data_sources.add_pandas(name=source_name)
    data_asset = data_source.add_dataframe_asset(name=asset_name)
    batch_def = data_asset.add_batch_definition_whole_dataframe(batch_def_name)

    # 4 Hàng Rào Kiểm Định (Expectations) Bắt Buộc:
    expectations = [
        # 1. ExpectTableRowCountToBeBetween: 5 đến 5000 dòng
        gx.expectations.ExpectTableRowCountToBeBetween(min_value=5, max_value=5000),
        # 2. ExpectColumnValuesToNotBeNull: paper_id, title, text_for_embedding không null
        gx.expectations.ExpectColumnValuesToNotBeNull(column="paper_id"),
        gx.expectations.ExpectColumnValuesToNotBeNull(column="title"),
        gx.expectations.ExpectColumnValuesToNotBeNull(column="text_for_embedding"),
        # 3. ExpectColumnValuesToBeUnique: paper_id duy nhất
        gx.expectations.ExpectColumnValuesToBeUnique(column="paper_id"),
        # 4. ExpectColumnValueLengthsToBeBetween: summary có độ dài tối thiểu 30 ký tự
        gx.expectations.ExpectColumnValueLengthsToBeBetween(column="summary", min_value=30),
    ]

    suite_name = f"papers_suite_{stage}"
    suite = context.suites.add(gx.ExpectationSuite(name=suite_name))
    for exp in expectations:
        suite.add_expectation(exp)

    validation_definition = context.validation_definitions.add(
        gx.ValidationDefinition(
            name=f"val_def_{stage}",
            data=batch_def,
            suite=suite,
        )
    )

    result = validation_definition.run(batch_parameters={"dataframe": df})

    gx_success = bool(result.success)
    results_summary = []
    for res in result.results:
        results_summary.append(
            {
                "expectation_type": res.expectation_config.type,
                "kwargs": res.expectation_config.kwargs,
                "success": bool(res.success),
            }
        )

    # Gọi kiểm tra Freshness SLA
    freshness_res = evaluate_freshness_sla(df, settings)
    overall_success = gx_success and freshness_res["is_fresh"]

    output_payload = {
        "stage": stage,
        "success": overall_success,
        "gx_success": gx_success,
        "is_fresh": freshness_res["is_fresh"],
        "evaluated_expectations": len(results_summary),
        "results": results_summary,
        "freshness": freshness_res,
    }

    settings.paths.quality_dir.mkdir(parents=True, exist_ok=True)
    report_file = settings.paths.quality_dir / f"{stage}_quality_report.json"
    write_json(report_file, output_payload)

    return output_payload
