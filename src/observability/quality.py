from __future__ import annotations

from datetime import datetime, timezone
import json
import logging
from pathlib import Path
from typing import Any

import great_expectations as gx
import great_expectations.expectations as gxe
import pandas as pd

from core.config import Settings

logger = logging.getLogger(__name__)


def evaluate_freshness_sla(df: pd.DataFrame, settings: Settings) -> dict[str, Any]:
    """Danh gia do tuoi moi theo Freshness SLA (age_days > threshold).

    Canh bao is_fresh = False neu ty le bai bao co age_days > 180 vuot qua 25%.
    """
    threshold_days = getattr(settings, "freshness_threshold_days", 180)
    total_rows = len(df)
    if total_rows == 0:
        return {
            "total_rows": 0,
            "stale_rows": 0,
            "stale_ratio": 0.0,
            "threshold_days": threshold_days,
            "is_fresh": True,
            "latest_published": "",
            "oldest_published": "",
        }

    if "age_days" in df.columns:
        stale_mask = df["age_days"] > threshold_days
    else:
        today = datetime.now(timezone.utc).date()
        stale_mask = pd.to_datetime(df["published"], errors="coerce").dt.date.apply(
            lambda d: (today - d).days > threshold_days if pd.notna(d) else True
        )

    stale_rows = int(stale_mask.sum())
    stale_ratio = float(stale_rows / total_rows)
    is_fresh = bool(stale_ratio <= 0.25)

    latest_published = (
        str(df["published"].dropna().max())
        if "published" in df.columns and not df["published"].dropna().empty
        else ""
    )
    oldest_published = (
        str(df["published"].dropna().min())
        if "published" in df.columns and not df["published"].dropna().empty
        else ""
    )

    return {
        "total_rows": total_rows,
        "stale_rows": stale_rows,
        "stale_ratio": round(stale_ratio, 4),
        "threshold_days": threshold_days,
        "is_fresh": is_fresh,
        "latest_published": latest_published,
        "oldest_published": oldest_published,
    }


def build_freshness_report(
    df: pd.DataFrame, settings: Settings, report_path: Path | None = None
) -> dict[str, Any]:
    """Tong hop freshness report va ghi file JSON."""
    report = evaluate_freshness_sla(df, settings)
    target_path = report_path or settings.paths.freshness_report
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return report


def run_data_quality_checks(
    df: pd.DataFrame, settings: Settings, report_name: str = "baseline"
) -> dict[str, Any]:
    """Tao va chay bo data quality checks voi GX 1.x ephemeral context va Freshness SLA.

    1. Khoi tao Ephemeral Context tren GX 1.x.
    2. Dinh nghia 4 Hang Rao Kiem Dinh (Expectations) bat buoc:
       - ExpectTableRowCountToBeBetween: 5 den 5000 dong.
       - ExpectColumnValuesToNotBeNull: paper_id, title, text_for_embedding khong duoc null.
       - ExpectColumnValuesToBeUnique: paper_id la duy nhat.
       - ExpectColumnValueLengthsToBeBetween: summary co do dai toi thieu 30 ky tu.
    3. Danh gia Freshness SLA bang evaluate_freshness_sla().
    4. Ghi ket qua vao data/quality/ va tra ve ket qua.
    """
    context = gx.get_context(mode="ephemeral")
    data_source = context.data_sources.add_pandas(name="papers_source")
    data_asset = data_source.add_dataframe_asset(name="papers_asset")
    batch_def = data_asset.add_batch_definition_whole_dataframe("papers_batch")
    batch = batch_def.get_batch(batch_parameters={"dataframe": df})

    expectations = [
        gxe.ExpectTableRowCountToBeBetween(min_value=5, max_value=5000),
        gxe.ExpectColumnValuesToNotBeNull(column="paper_id"),
        gxe.ExpectColumnValuesToNotBeNull(column="title"),
        gxe.ExpectColumnValuesToNotBeNull(column="text_for_embedding"),
        gxe.ExpectColumnValuesToBeUnique(column="paper_id"),
        gxe.ExpectColumnValueLengthsToBeBetween(column="summary", min_value=30),
    ]

    expectation_results = []
    all_gx_success = True

    for exp in expectations:
        res = batch.validate(exp)
        success = bool(res.success)
        all_gx_success = all_gx_success and success
        expectation_results.append(
            {
                "expectation": exp.__class__.__name__,
                "success": success,
                "result": res.result if hasattr(res, "result") else {},
            }
        )

    freshness = evaluate_freshness_sla(df, settings)
    overall_success = bool(all_gx_success and freshness["is_fresh"])

    report_payload = {
        "report_name": report_name,
        "success": overall_success,
        "gx_success": all_gx_success,
        "row_count": len(df),
        "freshness": freshness,
        "expectations": expectation_results,
    }

    if report_name == "baseline":
        output_path = settings.paths.baseline_quality_report
    elif report_name == "corrupted":
        output_path = settings.paths.corrupted_quality_report
    else:
        output_path = settings.paths.quality_dir / f"{report_name}_quality_report.json"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report_payload, indent=2, default=str, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    return report_payload
