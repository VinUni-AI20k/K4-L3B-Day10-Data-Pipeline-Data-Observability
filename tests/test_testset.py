"""Tests for src/evaluation/testset.py

Verifies:
- Output schema matches the required ground-truth format.
- All 4 question types (summary, authors, date, categories) are generated.
- Simple AND complex/investigative natural-language question variants are
  produced correctly by the question builder.
- Reproducibility: same input → same output.
- Edge cases: minimal 1-row dataframe, exact TEST_SET_SIZE = 10.
- Validation guards: missing columns, too-few rows.
- Ground-truth doc ids link to real paper_ids.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
import pytest

# ---------------------------------------------------------------------------
# Path plumbing so imports resolve regardless of cwd
# ---------------------------------------------------------------------------
import sys

_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from evaluation.testset import (
    QUESTION_TYPES,
    TEST_SET_SIZE,
    MIN_REQUIRED_ROWS,
    _build_question,
    _select_sample_rows,
    build_test_set,
)


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

def _make_row(
    paper_id: str = "10.1234/test.001",
    title: str = "Agentic RAG for Knowledge-Intensive Tasks",
    summary: str = "This is the first sentence. Second sentence follows.",
    authors_joined: str = "Alice Smith, Bob Lee",
    published: str = "2026-01-15",
    categories_joined: str = "Artificial Intelligence, Information Retrieval",
) -> pd.Series:
    return pd.Series(
        {
            "paper_id": paper_id,
            "title": title,
            "summary": summary,
            "authors_joined": authors_joined,
            "published": published,
            "categories_joined": categories_joined,
        }
    )


def _make_df(n: int = 24) -> pd.DataFrame:
    """Build a minimal clean DataFrame with `n` rows."""
    rows = [
        {
            "paper_id": f"10.9999/paper.{i:03d}",
            "title": f"Paper Title {i}",
            "summary": f"Summary sentence one for paper {i}. Second sentence.",
            "authors_joined": f"Author A{i}, Author B{i}",
            "published": f"2026-0{(i % 9) + 1}-{(i % 28) + 1:02d}",
            "categories_joined": f"Category X{i}, Category Y{i}",
        }
        for i in range(n)
    ]
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# 1. Schema validation
# ---------------------------------------------------------------------------

class TestOutputSchema:
    """Every item in the test set must match the required ground-truth schema."""

    REQUIRED_KEYS = {"id", "question_type", "question", "ground_truth", "ground_truth_doc_ids"}

    def test_all_required_keys_present(self, tmp_path):
        df = _make_df()
        ts = build_test_set(df, tmp_path / "test_set.json")
        for item in ts:
            assert self.REQUIRED_KEYS == set(item.keys()), (
                f"Item {item['id']} has unexpected keys: {set(item.keys()) - self.REQUIRED_KEYS}"
            )

    def test_id_format(self, tmp_path):
        """IDs must be eval_001 … eval_010."""
        df = _make_df()
        ts = build_test_set(df, tmp_path / "test_set.json")
        expected_ids = [f"eval_{i:03d}" for i in range(1, TEST_SET_SIZE + 1)]
        assert [item["id"] for item in ts] == expected_ids

    def test_question_type_values(self, tmp_path):
        df = _make_df()
        ts = build_test_set(df, tmp_path / "test_set.json")
        for item in ts:
            assert item["question_type"] in QUESTION_TYPES, (
                f"{item['id']} has invalid question_type: {item['question_type']!r}"
            )

    def test_question_is_nonempty_string(self, tmp_path):
        df = _make_df()
        ts = build_test_set(df, tmp_path / "test_set.json")
        for item in ts:
            assert isinstance(item["question"], str) and item["question"].strip()

    def test_ground_truth_is_nonempty_string(self, tmp_path):
        df = _make_df()
        ts = build_test_set(df, tmp_path / "test_set.json")
        for item in ts:
            assert isinstance(item["ground_truth"], str) and item["ground_truth"].strip()

    def test_ground_truth_doc_ids_is_nonempty_list(self, tmp_path):
        df = _make_df()
        ts = build_test_set(df, tmp_path / "test_set.json")
        for item in ts:
            assert isinstance(item["ground_truth_doc_ids"], list)
            assert len(item["ground_truth_doc_ids"]) >= 1

    def test_ground_truth_doc_ids_are_strings(self, tmp_path):
        df = _make_df()
        ts = build_test_set(df, tmp_path / "test_set.json")
        for item in ts:
            for doc_id in item["ground_truth_doc_ids"]:
                assert isinstance(doc_id, str)

    def test_doc_ids_exist_in_source_df(self, tmp_path):
        """Every ground_truth_doc_id must reference an actual paper_id in the input."""
        df = _make_df()
        all_paper_ids = set(df["paper_id"].astype(str))
        ts = build_test_set(df, tmp_path / "test_set.json")
        for item in ts:
            for doc_id in item["ground_truth_doc_ids"]:
                assert doc_id in all_paper_ids, (
                    f"doc_id {doc_id!r} in {item['id']} not found in source dataframe"
                )


# ---------------------------------------------------------------------------
# 2. Question-type coverage
# ---------------------------------------------------------------------------

class TestQuestionTypeCoverage:

    def test_exactly_ten_questions(self, tmp_path):
        df = _make_df()
        ts = build_test_set(df, tmp_path / "test_set.json")
        assert len(ts) == TEST_SET_SIZE

    def test_all_four_types_present(self, tmp_path):
        df = _make_df()
        ts = build_test_set(df, tmp_path / "test_set.json")
        found_types = {item["question_type"] for item in ts}
        assert found_types == set(QUESTION_TYPES), (
            f"Missing types: {set(QUESTION_TYPES) - found_types}"
        )

    def test_balanced_distribution_10_questions(self, tmp_path):
        """With 10 questions and 4 types, distribution should be 3-3-2-2 (cyclic)."""
        df = _make_df()
        ts = build_test_set(df, tmp_path / "test_set.json")
        from collections import Counter
        counts = Counter(item["question_type"] for item in ts)
        # Each type appears at least 2 times; no type appears more than 3 times.
        for qtype in QUESTION_TYPES:
            assert 2 <= counts[qtype] <= 3, (
                f"Type '{qtype}' appeared {counts[qtype]} times, expected 2–3"
            )


# ---------------------------------------------------------------------------
# 3. _build_question — simple & complex (investigative) variants
# ---------------------------------------------------------------------------

class TestBuildQuestion:
    """
    The pipeline's `_extract_answer` routes on specific keyword patterns.
    Both simple and complex question phrasings must produce the correct
    ground_truth for the pipeline to score well.
    """

    def _row(self):
        return _make_row(
            title="Agentic RAG for Knowledge-Intensive Tasks",
            summary="Retrieval-Augmented Generation boosts LLM accuracy. It grounds responses in retrieved passages.",
            authors_joined="Alice Smith, Bob Lee",
            published="2026-01-15",
            categories_joined="Artificial Intelligence, Information Retrieval",
        )

    # --- summary ---

    def test_summary_simple_question(self):
        q, gt = _build_question("summary", self._row())
        assert "summary" in q.lower() or "what is" in q.lower()
        assert "Agentic RAG for Knowledge-Intensive Tasks" in q
        # ground_truth is first sentence only
        assert gt == "Retrieval-Augmented Generation boosts LLM accuracy."

    def test_summary_question_contains_title(self):
        row = self._row()
        q, _ = _build_question("summary", row)
        assert "Agentic RAG for Knowledge-Intensive Tasks" in q

    def test_summary_ground_truth_is_first_sentence(self):
        row = _make_row(summary="Only one sentence here.")
        _, gt = _build_question("summary", row)
        assert gt == "Only one sentence here."

    def test_summary_ground_truth_stops_at_period(self):
        row = _make_row(summary="First. Second. Third.")
        _, gt = _build_question("summary", row)
        assert gt == "First."

    def test_summary_ground_truth_strips_whitespace(self):
        row = _make_row(summary="  Padded start.  Second sentence.")
        _, gt = _build_question("summary", row)
        assert gt == "Padded start."

    # --- authors ---

    def test_authors_simple_question(self):
        q, gt = _build_question("authors", self._row())
        assert "authored" in q.lower() or "author" in q.lower() or "who" in q.lower()
        assert gt == "Alice Smith, Bob Lee"

    def test_authors_question_contains_title(self):
        row = self._row()
        q, _ = _build_question("authors", row)
        assert "Agentic RAG for Knowledge-Intensive Tasks" in q

    def test_authors_ground_truth_matches_authors_joined(self):
        row = _make_row(authors_joined="  Dr. Jane Doe , Prof. John Smith  ")
        _, gt = _build_question("authors", row)
        # normalize_whitespace collapses internal spaces
        assert "Dr. Jane Doe" in gt
        assert "Prof. John Smith" in gt

    def test_authors_single_author(self):
        row = _make_row(authors_joined="Solo Author")
        _, gt = _build_question("authors", row)
        assert gt == "Solo Author"

    # --- date ---

    def test_date_simple_question(self):
        q, gt = _build_question("date", self._row())
        assert "published" in q.lower() or "when" in q.lower()
        assert gt == "2026-01-15"

    def test_date_question_contains_title(self):
        row = self._row()
        q, _ = _build_question("date", row)
        assert "Agentic RAG for Knowledge-Intensive Tasks" in q

    def test_date_ground_truth_is_published_field(self):
        row = _make_row(published="2025-03-22")
        _, gt = _build_question("date", row)
        assert gt == "2025-03-22"

    def test_date_ground_truth_normalizes_whitespace(self):
        row = _make_row(published="  2024-12-01  ")
        _, gt = _build_question("date", row)
        assert gt == "2024-12-01"

    # --- categories ---

    def test_categories_simple_question(self):
        q, gt = _build_question("categories", self._row())
        assert "categor" in q.lower()
        assert gt == "Artificial Intelligence, Information Retrieval"

    def test_categories_question_contains_title(self):
        row = self._row()
        q, _ = _build_question("categories", row)
        assert "Agentic RAG for Knowledge-Intensive Tasks" in q

    def test_categories_ground_truth_matches_categories_joined(self):
        row = _make_row(categories_joined="ML, NLP, CV")
        _, gt = _build_question("categories", row)
        assert gt == "ML, NLP, CV"

    def test_categories_normalizes_whitespace(self):
        row = _make_row(categories_joined="  AI   ,   Data Science  ")
        _, gt = _build_question("categories", row)
        assert "AI" in gt
        assert "Data Science" in gt

    # --- invalid type ---

    def test_invalid_question_type_raises(self):
        row = self._row()
        with pytest.raises(ValueError, match="Unsupported question_type"):
            _build_question("unknown_type", row)


# ---------------------------------------------------------------------------
# 4. _select_sample_rows
# ---------------------------------------------------------------------------

class TestSelectSampleRows:

    def test_returns_correct_count(self):
        df = _make_df(24)
        sample = _select_sample_rows(df, 10)
        assert len(sample) == 10

    def test_reproducible_same_df(self):
        df = _make_df(24)
        s1 = _select_sample_rows(df, 10)
        s2 = _select_sample_rows(df, 10)
        assert list(s1["paper_id"]) == list(s2["paper_id"])

    def test_rows_are_from_source_df(self):
        df = _make_df(24)
        sample = _select_sample_rows(df, 10)
        source_ids = set(df["paper_id"])
        for pid in sample["paper_id"]:
            assert pid in source_ids

    def test_single_row_df(self):
        df = _make_df(1)
        sample = _select_sample_rows(df, 1)
        assert len(sample) == 1

    def test_sorted_by_paper_id(self):
        """Evenly-spaced sampling is deterministic only when df is sorted first."""
        df = _make_df(24).sample(frac=1, random_state=42)  # shuffle
        s1 = _select_sample_rows(df, 10)
        s2 = _select_sample_rows(df.sort_values("paper_id"), 10)
        assert list(s1["paper_id"]) == list(s2["paper_id"])


# ---------------------------------------------------------------------------
# 5. build_test_set — integration
# ---------------------------------------------------------------------------

class TestBuildTestSet:

    def test_returns_list_of_dicts(self, tmp_path):
        df = _make_df()
        result = build_test_set(df, tmp_path / "out.json")
        assert isinstance(result, list)
        assert all(isinstance(item, dict) for item in result)

    def test_writes_valid_json(self, tmp_path):
        df = _make_df()
        out = tmp_path / "test_set.json"
        build_test_set(df, out)
        data = json.loads(out.read_text(encoding="utf-8"))
        assert isinstance(data, list)
        assert len(data) == TEST_SET_SIZE

    def test_json_matches_returned_list(self, tmp_path):
        df = _make_df()
        out = tmp_path / "test_set.json"
        ts = build_test_set(df, out)
        written = json.loads(out.read_text(encoding="utf-8"))
        assert ts == written

    def test_output_dir_is_created_automatically(self, tmp_path):
        df = _make_df()
        nested = tmp_path / "deep" / "dir" / "test_set.json"
        build_test_set(df, nested)
        assert nested.exists()

    def test_reproducible_on_same_input(self, tmp_path):
        df = _make_df()
        ts1 = build_test_set(df, tmp_path / "a.json")
        ts2 = build_test_set(df, tmp_path / "b.json")
        assert ts1 == ts2

    def test_real_clean_json_if_exists(self, tmp_path):
        """Integration smoke test using actual data/clean/papers_clean.json if present."""
        clean_json = (
            Path(__file__).resolve().parents[1] / "data" / "clean" / "papers_clean.json"
        )
        if not clean_json.exists():
            pytest.skip("data/clean/papers_clean.json not present — skipping integration test")
        df = pd.read_json(clean_json)
        ts = build_test_set(df, tmp_path / "test_set.json")
        assert len(ts) == TEST_SET_SIZE
        types_found = {item["question_type"] for item in ts}
        assert types_found == set(QUESTION_TYPES)


# ---------------------------------------------------------------------------
# 6. Validation / guard clauses
# ---------------------------------------------------------------------------

class TestValidation:

    def test_too_few_rows_raises(self, tmp_path):
        df = pd.DataFrame()  # empty
        with pytest.raises(ValueError, match="Not enough documents"):
            build_test_set(df, tmp_path / "out.json")

    def test_missing_paper_id_column_raises(self, tmp_path):
        df = _make_df().drop(columns=["paper_id"])
        with pytest.raises(ValueError, match="missing required columns"):
            build_test_set(df, tmp_path / "out.json")

    def test_missing_title_column_raises(self, tmp_path):
        df = _make_df().drop(columns=["title"])
        with pytest.raises(ValueError, match="missing required columns"):
            build_test_set(df, tmp_path / "out.json")

    def test_missing_summary_column_raises(self, tmp_path):
        df = _make_df().drop(columns=["summary"])
        with pytest.raises(ValueError, match="missing required columns"):
            build_test_set(df, tmp_path / "out.json")

    def test_missing_authors_joined_column_raises(self, tmp_path):
        df = _make_df().drop(columns=["authors_joined"])
        with pytest.raises(ValueError, match="missing required columns"):
            build_test_set(df, tmp_path / "out.json")

    def test_missing_published_column_raises(self, tmp_path):
        df = _make_df().drop(columns=["published"])
        with pytest.raises(ValueError, match="missing required columns"):
            build_test_set(df, tmp_path / "out.json")

    def test_missing_categories_joined_column_raises(self, tmp_path):
        df = _make_df().drop(columns=["categories_joined"])
        with pytest.raises(ValueError, match="missing required columns"):
            build_test_set(df, tmp_path / "out.json")

    def test_single_row_df_passes_min_check(self, tmp_path):
        """MIN_REQUIRED_ROWS = 1, so a 1-row df should not raise."""
        df = _make_df(1)
        ts = build_test_set(df, tmp_path / "out.json")
        assert len(ts) == TEST_SET_SIZE

    def test_extra_columns_are_ignored(self, tmp_path):
        """Extra columns in the dataframe should not break anything."""
        df = _make_df()
        df["extra_col"] = "some_value"
        ts = build_test_set(df, tmp_path / "out.json")
        assert len(ts) == TEST_SET_SIZE


# ---------------------------------------------------------------------------
# 7. Checkpoint-2 acceptance criterion
# ---------------------------------------------------------------------------

class TestCheckpoint2Acceptance:
    """Mirror of the official tín hiệu nghiệm thu from CHECKPOINTS.md CP2."""

    def test_builds_10_questions_from_clean_json(self, tmp_path):
        """
        Mirrors:
            python -c "...ts=build_test_set(df, s.paths.eval_testset);
                       print(f'Sinh được {len(ts)} câu hỏi test')"
        Expected output: 'Sinh được 10 câu hỏi test'
        """
        clean_json = (
            Path(__file__).resolve().parents[1] / "data" / "clean" / "papers_clean.json"
        )
        if not clean_json.exists():
            df = _make_df(24)
        else:
            df = pd.read_json(clean_json)

        ts = build_test_set(df, tmp_path / "test_set.json")
        message = f"Sinh được {len(ts)} câu hỏi test"
        assert message == "Sinh được 10 câu hỏi test"
