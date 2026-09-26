from datetime import datetime, timezone
from typing import Any

import great_expectations as gx
import pandas as pd

from core.config import Settings
from core.utils import write_json


def evaluate_freshness_sla(
    df: pd.DataFrame,
    threshold_days: int = 180,
    stale_ratio_limit: float = 0.25,
) -> dict[str, Any]:
    """Đo lường tỉ lệ bài báo cũ (age_days > 180).
    Nếu tỉ lệ bài báo cũ vượt quá 25%, hệ thống lập tức gắn cờ cảnh báo is_fresh = False.
    """
    total_rows = len(df)
    if total_rows == 0:
        return {
            "total_rows": 0,
            "stale_rows": 0,
            "stale_ratio": 0.0,
            "is_fresh": True,
            "threshold_days": threshold_days,
            "stale_ratio_limit": stale_ratio_limit,
        }

    stale_rows = int((df["age_days"] > threshold_days).sum()) if "age_days" in df.columns else 0
    stale_ratio = float(stale_rows / total_rows)
    is_fresh = bool(stale_ratio <= stale_ratio_limit)

    return {
        "total_rows": total_rows,
        "stale_rows": stale_rows,
        "stale_ratio": round(stale_ratio, 4),
        "is_fresh": is_fresh,
        "threshold_days": threshold_days,
        "stale_ratio_limit": stale_ratio_limit,
    }


def run_data_quality_checks(
    df: pd.DataFrame,
    settings: Settings,
    report_name: str = "test",
) -> dict[str, Any]:
    """Thiết lập chốt kiểm soát dữ liệu (Observability Gate) với Great Expectations 1.x.

    4 Hàng Rào Kiểm Định (Expectations) Bắt Buộc:
    1. ExpectTableRowCountToBeBetween: Số lượng bản ghi trong ngưỡng 5 đến 5000 dòng.
    2. ExpectColumnValuesToNotBeNull: Các cột paper_id, title, text_for_embedding không được rỗng.
    3. ExpectColumnValuesToBeUnique: paper_id là duy nhất.
    4. ExpectColumnValueLengthsToBeBetween: Trường summary có độ dài tối thiểu 30 ký tự.
    Kết hợp gọi evaluate_freshness_sla.
    """
    # Ephemeral Context chuẩn GX 1.x
    context = gx.get_context(mode="ephemeral")
    data_source = context.data_sources.add_pandas(name="papers_source")
    data_asset = data_source.add_dataframe_asset(name="papers_asset")
    batch_def = data_asset.add_batch_definition_whole_dataframe("papers_batch")
    batch = batch_def.get_batch(batch_parameters={"dataframe": df})

    suite = gx.ExpectationSuite(name=f"papers_quality_suite_{report_name}")

    # 1. Row count: 5 - 5000
    suite.add_expectation(
        gx.expectations.ExpectTableRowCountToBeBetween(min_value=5, max_value=5000)
    )

    # 2. Not null: paper_id, title, text_for_embedding
    for col in ["paper_id", "title", "text_for_embedding"]:
        if col in df.columns:
            suite.add_expectation(
                gx.expectations.ExpectColumnValuesToNotBeNull(column=col)
            )

    # 3. Unique: paper_id
    if "paper_id" in df.columns:
        suite.add_expectation(
            gx.expectations.ExpectColumnValuesToBeUnique(column="paper_id")
        )

    # 4. Length: summary tối thiểu 30 ký tự
    if "summary" in df.columns:
        suite.add_expectation(
            gx.expectations.ExpectColumnValueLengthsToBeBetween(
                column="summary", min_value=30
            )
        )

    validation_results = batch.validate(suite)
    gx_success = bool(validation_results.success)

    # Freshness check
    freshness = evaluate_freshness_sla(
        df,
        threshold_days=settings.freshness_threshold_days,
        stale_ratio_limit=0.25,
    )

    overall_success = bool(gx_success and freshness["is_fresh"])

    expectation_results = []
    for res in validation_results.results:
        exp_cfg = res.expectation_config
        exp_type = getattr(exp_cfg, "type", getattr(exp_cfg, "expectation_type", str(exp_cfg)))
        expectation_results.append(
            {
                "expectation_type": exp_type,
                "success": bool(res.success),
                "result": res.result,
            }
        )

    output = {
        "report_name": report_name,
        "success": overall_success,
        "gx_success": gx_success,
        "freshness": freshness,
        "expectations_count": len(expectation_results),
        "results": expectation_results,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    out_path = (
        settings.paths.baseline_quality_report
        if report_name == "baseline"
        else settings.paths.quality_dir / f"{report_name}_quality_report.json"
    )
    write_json(out_path, output)

    return output


def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path) -> dict[str, Any]:
    """Tổng hợp freshness report và lưu file JSON."""
    sla = evaluate_freshness_sla(
        df,
        threshold_days=settings.freshness_threshold_days,
        stale_ratio_limit=0.25,
    )

    published_series = df["published"].dropna() if "published" in df.columns else pd.Series(dtype=object)
    latest_published = str(published_series.max()) if not published_series.empty else "N/A"
    oldest_published = str(published_series.min()) if not published_series.empty else "N/A"

    payload = {
        "latest_published": latest_published,
        "oldest_published": oldest_published,
        "stale_rows": sla["stale_rows"],
        "total_rows": sla["total_rows"],
        "stale_ratio": sla["stale_ratio"],
        "threshold_days": sla["threshold_days"],
        "is_fresh": sla["is_fresh"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    write_json(report_path, payload)
    return payload

