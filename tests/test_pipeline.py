from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import pytest

from core.config import load_settings, normalized_provider
from ingestion.crossref import load_raw_records, parse_crossref_payload
from ingestion.cleaning import build_clean_dataframe
from ingestion.corruption import corrupt_clean_dataframe
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.self_healing import AutomatedSelfHealingPipeline
from retrieval.embeddings import MiniLMEmbeddings
from retrieval.index import LocalEmbeddingIndex
from retrieval.llm import build_llm
from retrieval.qa import answer_question


@pytest.fixture
def settings():
    return load_settings()


@pytest.fixture
def clean_df(settings):
    records = load_raw_records(settings.paths.raw_records_json)
    return build_clean_dataframe(records, datetime.now(timezone.utc))


def test_ingestion_and_cleaning(clean_df):
    """Test that raw records are correctly parsed and cleaned into standard schema."""
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
    """Test Great Expectations 1.x ephemeral quality gate on baseline clean data."""
    res = run_data_quality_checks(clean_df, settings, "pytest_clean")
    assert res["success"] is True, "Clean dataset must pass Great Expectations 1.x Quality Gate"


def test_freshness_sla_baseline(clean_df, settings):
    """Test that baseline data satisfies Freshness SLA (stale_ratio <= 0.25)."""
    freshness = build_freshness_report(clean_df, settings, settings.paths.quality_dir / "pytest_freshness.json")
    assert freshness["is_fresh"] is True, "Baseline data must satisfy Freshness SLA (stale_ratio <= 0.25)"
    assert freshness["stale_ratio"] <= 0.25


def test_corruption_detection(clean_df, settings, tmp_path):
    """Test that synthetic corruptions trigger Quality Gate failure and Freshness violation."""
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
    """Test that Idempotent Repair produces identical results across multiple executions."""
    records = load_raw_records(settings.paths.raw_records_json)
    repaired_1 = build_clean_dataframe(records, datetime.now(timezone.utc))
    repaired_2 = build_clean_dataframe(records, datetime.now(timezone.utc))
    assert len(repaired_1) == 24
    assert len(repaired_2) == 24
    assert list(repaired_1["paper_id"]) == list(repaired_2["paper_id"])
    assert list(repaired_1["text_for_embedding"]) == list(repaired_2["text_for_embedding"])


def test_automated_self_healing(clean_df, settings, tmp_path):
    """Test Bonus B2: Automated Self-Healing Controller restores corrupted data."""
    pipeline = AutomatedSelfHealingPipeline(settings)
    
    # 1. Healthy data
    healthy_res = pipeline.inspect_and_heal(clean_df, auto_reindex=False)
    assert healthy_res.initial_status == "HEALTHY"
    assert healthy_res.healing_triggered is False

    # 2. Corrupted data
    corrupted_df = corrupt_clean_dataframe(clean_df, tmp_path / "corrupt.json")
    corrupt_res = pipeline.inspect_and_heal(corrupted_df, auto_reindex=False)
    assert corrupt_res.initial_status == "VIOLATION_DETECTED"
    assert corrupt_res.healing_triggered is True
    assert corrupt_res.final_gx_success is True
    assert corrupt_res.final_is_fresh is True
    assert corrupt_res.repaired_records == 24


def test_chroma_vector_indexing_and_search(clean_df, settings):
    """Test building ChromaDB collection and performing similarity search."""
    manifest_path = settings.paths.quality_dir / "pytest_embeddings.json"
    index = LocalEmbeddingIndex.build(clean_df.iloc[:5], settings, manifest_path)
    assert len(index.documents) == 5
    
    query = clean_df.iloc[0]["title"]
    results = index.search(query, top_k=2)
    assert len(results) >= 1
    assert results[0].paper_id == clean_df.iloc[0]["paper_id"]


def test_multi_provider_llm_factory(settings):
    """Test LLM provider normalization and mock factory."""
    assert normalized_provider(settings) in {"gemini", "openai", "anthropic", "openrouter", "ollama", "custom", "mock"}
    
    # Test mock provider
    mock_settings = load_settings()
    object.__setattr__(mock_settings, "llm_provider", "mock")
    llm = build_llm(mock_settings)
    res = llm.invoke("Test question")
    assert "mock response" in res.content.lower()


def test_qa_answer_extraction(clean_df, settings):
    """Test question answering exact lookup and semantic fallback."""
    manifest_path = settings.paths.quality_dir / "pytest_qa_embeddings.json"
    index = LocalEmbeddingIndex.build(clean_df.iloc[:5], settings, manifest_path)
    
    first_title = clean_df.iloc[0]["title"]
    q = f"What is the summary of '{first_title}'?"
    ans = answer_question(q, settings, index)
    assert ans.answer != ""
    assert clean_df.iloc[0]["paper_id"] in ans.retrieved_doc_ids
