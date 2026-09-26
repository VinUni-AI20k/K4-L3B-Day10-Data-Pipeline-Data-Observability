from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import great_expectations as gx
import pandas as pd

from core.config import Settings

logger = logging.getLogger(__name__)


def evaluate_freshness_sla(
    df: pd.DataFrame,
    threshold_days: int = 180,
    stale_pct_limit: float = 0.25,
) -> dict[str, Any]:
    """Canh bao neu > 25% bai bao cu qua threshold_days ngay.

    Returns:
        dict voi keys: stale_count, total_rows, stale_pct, is_fresh, warning
    """
    total = len(df)
    if total == 0:
        return {
            "stale_count": 0,
            "total_rows": 0,
            "stale_pct": 0.0,
            "is_fresh": True,
            "warning": None,
        }

    if "age_days" in df.columns:
        stale_count = int((df["age_days"] > threshold_days).sum())
    elif "published" in df.columns:
        today = datetime.now(UTC).date()

        def _age(pub_str: str) -> int:
            try:
                d = datetime.fromisoformat(str(pub_str)[:10]).date()
                return (today - d).days
            except Exception:
                return 0

        stale_count = int(df["published"].apply(_age).gt(threshold_days).sum())
    else:
        stale_count = 0

    stale_pct = stale_count / total
    is_fresh = stale_pct <= stale_pct_limit
    warning = None
    if not is_fresh:
        warning = (
            f"FRESHNESS SLA WARNING: {stale_count}/{total} bai bao "
            f"({stale_pct:.1%}) cu hon {threshold_days} ngay -- vuot nguong {stale_pct_limit:.0%}."
        )
        logger.warning(warning)
    else:
        logger.info(
            "Freshness SLA OK: %d/%d bai bao cu hon %d ngay (%.1f%%).",
            stale_count,
            total,
            threshold_days,
            stale_pct * 100,
        )

    return {
        "stale_count": stale_count,
        "total_rows": total,
        "stale_pct": round(stale_pct, 4),
        "is_fresh": is_fresh,
        "warning": warning,
    }


def run_data_quality_checks(
    df: pd.DataFrame, settings: Settings, report_name: str
) -> dict[str, Any]:
    """Chay Great Expectations 1.x Ephemeral Context voi 4 expectations bat buoc.

    Expectations:
      1. ExpectTableRowCountToBeBetween (5-5000 dong)
      2. ExpectColumnValuesToNotBeNull (paper_id, title, text_for_embedding)
      3. ExpectColumnValuesToBeUnique (paper_id)
      4. ExpectColumnValueLengthsToBeBetween (summary >= 30 ky tu)

    Tich hop evaluate_freshness_sla() (canh bao neu > 25% bai bao cu qua 180 ngay).
    Ghi ket qua JSON vao data/quality/.
    """
    # 1. Thiet lap GX 1.x Ephemeral Context
    context = gx.get_context(mode="ephemeral")
    data_source = context.data_sources.add_pandas(name="papers_source")
    data_asset = data_source.add_dataframe_asset(name="papers_asset")
    batch_def = data_asset.add_batch_definition_whole_dataframe("papers_batch")

    # 2. Tao Expectation Suite
    suite_name = f"{report_name}_suite"
    suite = context.suites.add(gx.ExpectationSuite(name=suite_name))

    # Expectation 1: Row count between 5 va 5000
    suite.add_expectation(
        gx.expectations.ExpectTableRowCountToBeBetween(min_value=5, max_value=5000)
    )

    # Expectation 2: Cac cot khong duoc null
    for col in ["paper_id", "title", "text_for_embedding"]:
        if col in df.columns:
            suite.add_expectation(
                gx.expectations.ExpectColumnValuesToNotBeNull(column=col)
            )

    # Expectation 3: paper_id phai unique
    if "paper_id" in df.columns:
        suite.add_expectation(
            gx.expectations.ExpectColumnValuesToBeUnique(column="paper_id")
        )

    # Expectation 4: summary >= 30 ky tu
    if "summary" in df.columns:
        suite.add_expectation(
            gx.expectations.ExpectColumnValueLengthsToBeBetween(
                column="summary",
                min_value=30,
            )
        )

    # 3. Tao Validation Definition va chay
    validation_def = context.validation_definitions.add(
        gx.ValidationDefinition(
            name=f"{report_name}_validation",
            data=batch_def,
            suite=suite,
        )
    )
    result = validation_def.run(batch_parameters={"dataframe": df})

    # 4. Tich hop Freshness SLA
    freshness = evaluate_freshness_sla(
        df,
        threshold_days=settings.freshness_threshold_days,
        stale_pct_limit=0.25,
    )

    # 5. Tong hop ket qua
    gx_success = bool(result.success)

    results_detail = []
    for er in result.results:
        results_detail.append(
            {
                "expectation_type": er.expectation_config.type,
                "success": bool(er.success),
                "kwargs": {
                    k: v
                    for k, v in er.expectation_config.kwargs.items()
                    if k != "batch_id"
                },
            }
        )

    payload: dict[str, Any] = {
        "report_name": report_name,
        "run_at": datetime.now(UTC).isoformat(),
        "success": gx_success,
        "row_count": len(df),
        "gx_results": results_detail,
        "freshness": freshness,
    }

    if freshness["warning"]:
        logger.warning(freshness["warning"])

    # 6. Ghi ket qua vao data/quality/
    quality_dir: Path = settings.paths.quality_dir
    quality_dir.mkdir(parents=True, exist_ok=True)

    report_path = quality_dir / f"{report_name}_quality_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    logger.info(
        "Quality check '%s': success=%s, rows=%d, report=%s",
        report_name,
        gx_success,
        len(df),
        report_path,
    )
    return payload


def build_freshness_report(
    df: pd.DataFrame, settings: Settings, report_path
) -> dict[str, Any]:
    """Tong hop freshness report.

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
    total = len(df)
    threshold_days = settings.freshness_threshold_days

    latest_published: str | None = None
    oldest_published: str | None = None

    if "published" in df.columns and total > 0:
        pub_series = df["published"].dropna().astype(str)
        valid_dates = pub_series[pub_series.str.len() >= 10]
        if not valid_dates.empty:
            latest_published = valid_dates.max()[:10]
            oldest_published = valid_dates.min()[:10]

    freshness = evaluate_freshness_sla(df, threshold_days=threshold_days, stale_pct_limit=0.25)
    stale_rows = freshness["stale_count"]

    payload: dict[str, Any] = {
        "run_at": datetime.now(UTC).isoformat(),
        "latest_published": latest_published,
        "oldest_published": oldest_published,
        "stale_rows": stale_rows,
        "total_rows": total,
        "stale_pct": freshness["stale_pct"],
        "threshold_days": threshold_days,
        "is_fresh": freshness["is_fresh"],
        "warning": freshness["warning"],
    }

    report_path = Path(report_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    logger.info(
        "Freshness report: is_fresh=%s, stale=%d/%d, latest=%s",
        payload["is_fresh"],
        stale_rows,
        total,
        latest_published,
    )
    return payload
