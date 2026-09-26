from __future__ import annotations

from datetime import datetime, timezone
import pytest

from core.config import load_settings
from ingestion.crossref import load_raw_records
from ingestion.cleaning import build_clean_dataframe
from ingestion.corruption import corrupt_clean_dataframe
from observability.quality import build_freshness_report, run_data_quality_checks


@pytest.fixture
def settings():
    return load_settings()


@pytest.fixture
def clean_df(settings):
    records = load_raw_records(settings.paths.raw_records_json)
    return build_clean_dataframe(records, datetime.now(timezone.utc))


def test_ingestion_and_cleaning(clean_df):
    assert len(clean_df) == 24, "Clean dataframe must contain exactly 24 records"
    expected_cols = {
        "paper_id", "title", "summary", "authors_joined", "categories_joined",
        "published", "age_days", "text_for_embedding"
    }
    assert expected_cols.issubset(clean_df.columns), "Missing required columns in cleaned data"
    # Check 5-part text_for_embedding structure
    sample_text = clean_df.iloc[0]["text_for_embedding"]
    assert "Title:" in sample_text
    assert "Authors:" in sample_text
    assert "Categories:" in sample_text
    assert "Published:" in sample_text
    assert "Summary:" in sample_text


def test_great_expectations_quality_gate(clean_df, settings):
    res = run_data_quality_checks(clean_df, settings, "pytest_clean")
    assert res["success"] is True, "Clean dataset must pass Great Expectations 1.x Quality Gate"


def test_freshness_sla_baseline(clean_df, settings):
    freshness = build_freshness_report(clean_df, settings, settings.paths.quality_dir / "pytest_freshness.json")
    assert freshness["is_fresh"] is True, "Baseline data must satisfy Freshness SLA (stale_ratio <= 0.25)"


def test_corruption_detection(clean_df, settings, tmp_path):
    log_path = tmp_path / "test_corruption_log.json"
    corrupted_df = corrupt_clean_dataframe(clean_df, log_path)
    assert log_path.exists(), "Corruption log must be created"
    
    # GX quality gate should fail on corrupted data
    gx_res = run_data_quality_checks(corrupted_df, settings, "pytest_corrupted")
    assert gx_res["success"] is False, "Corrupted dataset must fail Quality Gate"

    # Freshness check should detect stale data
    freshness = build_freshness_report(corrupted_df, settings, tmp_path / "pytest_corrupted_freshness.json")
    assert freshness["is_fresh"] is False, "Corrupted data with stale dates must trigger Freshness SLA violation"


def test_idempotent_repair(settings):
    # Load from raw source
    records = load_raw_records(settings.paths.raw_records_json)
    repaired_1 = build_clean_dataframe(records, datetime.now(timezone.utc))
    repaired_2 = build_clean_dataframe(records, datetime.now(timezone.utc))
    # Idempotent: multiple runs produce identical record counts and IDs
    assert len(repaired_1) == 24
    assert len(repaired_2) == 24
    assert list(repaired_1["paper_id"]) == list(repaired_2["paper_id"])
