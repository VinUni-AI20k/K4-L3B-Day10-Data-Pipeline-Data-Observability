"""Contract and failure-injection tests; no API keys or model downloads."""
from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest

import pandas as pd
from pandas.testing import assert_frame_equal

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from evaluation.testset import build_test_set
from ingestion.corruption import NOISE, corrupt_clean_dataframe


def clean_fixture(count=24):
    return pd.DataFrame([
        {
            "paper_id": f"10.1000/{i:03d}",
            "title": f"Research paper number {i:03d}",
            "summary": f"Finding number {i}. Supporting details about this research.",
            "authors_joined": f"Author {i}, Coauthor {i}",
            "categories_joined": "Artificial Intelligence, Data Systems",
            "published": (pd.Timestamp("2026-09-26") - pd.Timedelta(days=i)).date().isoformat(),
            "age_days": i,
            "text_for_embedding": "Original embedding text",
            "summary_chars": 999,
            "authors": [f"Author {i}", f"Coauthor {i}"],
        }
        for i in range(count)
    ])


class Member2Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "nested" / "artifact.json"
        self.df = clean_fixture()

    def test_benchmark_schema_and_ground_truth(self):
        result = build_test_set(self.df, str(self.path))
        self.assertEqual(result, json.loads(self.path.read_text()))
        self.assertEqual(len(result), 10)
        self.assertEqual(len({item["id"] for item in result}), 10)
        self.assertEqual(len({item["ground_truth_doc_ids"][0] for item in result}), 10)
        self.assertEqual({kind: sum(item["question_type"] == kind for item in result) for kind in ("summary", "authors", "date", "categories")}, {"summary": 3, "authors": 3, "date": 2, "categories": 2})
        records = self.df.set_index("paper_id")
        for item in result:
            row = records.loc[item["ground_truth_doc_ids"][0]]
            expected = {"summary": row["summary"].split(". ")[0] + ".", "authors": row["authors_joined"], "date": row["published"], "categories": row["categories_joined"]}
            self.assertEqual(item["ground_truth"], expected[item["question_type"]])
        self.assertEqual(result[0]["ground_truth_doc_ids"], ["10.1000/000"])
        self.assertEqual(result[-1]["ground_truth_doc_ids"], ["10.1000/023"])

    def test_benchmark_is_independent_of_row_order(self):
        expected = build_test_set(self.df, self.path)
        self.assertEqual(expected, build_test_set(self.df.sample(frac=1, random_state=42), self.path))

    def test_benchmark_does_not_mutate_input(self):
        original = self.df.copy(deep=True)
        build_test_set(self.df, self.path)
        assert_frame_equal(self.df, original)

    def test_apostrophe_in_title_uses_document_id(self):
        self.df.at[0, "title"] = "An author's research paper"
        result = build_test_set(self.df, self.path)
        self.assertIn("'10.1000/000'", result[0]["question"])

    def test_invalid_benchmark_inputs_do_not_write_artifact(self):
        cases = [self.df.iloc[:9], self.df.iloc[:0], self.df.drop(columns="summary"), pd.concat([self.df, self.df.iloc[:1]])]
        for column, value in [("summary", " "), ("authors_joined", None), ("published", "invalid"), ("categories_joined", ["AI"])]:
            invalid = self.df.copy(deep=True)
            invalid[column] = invalid[column].astype(object)
            invalid.at[0, column] = value
            cases.append(invalid)
        for invalid in cases:
            with self.subTest(shape=invalid.shape), self.assertRaises(ValueError):
                build_test_set(invalid, self.path)
            self.assertFalse(self.path.exists())

    def test_benchmark_import_does_not_load_rag_stack(self):
        self.assertNotIn("evaluation.metrics", sys.modules)
        self.assertNotIn("sentence_transformers", sys.modules)

    def test_all_six_corruptions_and_audit_log(self):
        corrupted = corrupt_clean_dataframe(self.df, self.path)
        log = json.loads(self.path.read_text())
        self.assertEqual([item["scenario"] for item in log["scenarios"]], ["drop_latest_records", "blank_summary", "inject_noise", "truncate_title", "stale_date", "duplicate_rows"])
        self.assertEqual([item["affected_count"] for item in log["scenarios"]], [5, 4, 4, 4, 8, 2])
        self.assertEqual((log["input_rows"], log["output_rows"]), (24, 21))
        self.assertEqual(set(self.df.paper_id) - set(corrupted.paper_id), set(self.df.head(5).paper_id))
        self.assertEqual(corrupted.summary.eq("").sum(), 4)
        self.assertEqual(corrupted.summary.str.startswith(NOISE).sum(), 4)
        self.assertEqual(corrupted.title.str.len().lt(8).sum(), 4)
        self.assertEqual(corrupted.age_days.gt(180).sum(), 8)
        self.assertEqual(corrupted.paper_id.duplicated().sum(), 2)
        indexed = corrupted.drop_duplicates("paper_id").set_index("paper_id")
        for event in log["scenarios"]:
            self.assertEqual(len(event["changes"]), event["affected_count"])
            self.assertEqual(event["affected_paper_ids"], [change["paper_id"] for change in event["changes"]])
            for change in event["changes"]:
                if event["scenario"] not in {"drop_latest_records", "duplicate_rows"}:
                    for field, value in change["after"].items():
                        self.assertEqual(indexed.at[change["paper_id"], field], value)
                self.assertNotEqual(change["before"], change["after"])

    def test_stale_age_and_embedding_fields_are_consistent(self):
        corrupted = corrupt_clean_dataframe(self.df, self.path)
        for row in corrupted.to_dict("records"):
            self.assertEqual(row["summary_chars"], len(row["summary"]))
            self.assertEqual(row["age_days"], (pd.Timestamp("2026-09-26") - pd.Timestamp(row["published"])).days)
            for label, field in [("Title", "title"), ("Authors", "authors_joined"), ("Published", "published"), ("Categories", "categories_joined"), ("Summary", "summary")]:
                self.assertIn(f"{label}: {row[field]}", row["text_for_embedding"])
        for paper_id in corrupted.loc[corrupted.paper_id.duplicated(), "paper_id"]:
            pair = corrupted[corrupted.paper_id == paper_id].reset_index(drop=True)
            self.assertEqual(pair.iloc[0].to_dict(), pair.iloc[1].to_dict())

    def test_audit_log_replays_all_six_operations(self):
        corrupted = corrupt_clean_dataframe(self.df, self.path)
        replay = self.df.copy(deep=True)
        log = json.loads(self.path.read_text())
        for event in log["scenarios"]:
            self.assertEqual(len(replay), event["rows_before"])
            for change in event["changes"]:
                mask = replay.paper_id.eq(change["paper_id"])
                if event["scenario"] == "drop_latest_records":
                    self.assertEqual(replay.loc[mask, "published"].iloc[0], change["before"]["published"])
                    replay = replay.loc[~mask].copy()
                elif event["scenario"] == "duplicate_rows":
                    self.assertEqual(int(mask.sum()), change["before"]["occurrences"])
                    replay = pd.concat([replay, replay.loc[mask]], ignore_index=True)
                else:
                    for column, before in change["before"].items():
                        self.assertEqual(replay.loc[mask, column].iloc[0], before)
                        replay.loc[mask, column] = change["after"][column]
            self.assertEqual(len(replay), event["rows_after"])
        columns = [column for column in replay.columns if column not in {"summary_chars", "text_for_embedding"}]
        assert_frame_equal(replay[columns].reset_index(drop=True), corrupted[columns])

    def test_corruption_deterministic_even_with_duplicate_index_labels(self):
        expected = corrupt_clean_dataframe(self.df, self.path)
        expected_log = self.path.read_bytes()
        shuffled = self.df.sample(frac=1, random_state=17)
        shuffled.index = [0] * len(shuffled)
        actual = corrupt_clean_dataframe(shuffled, self.path)
        assert_frame_equal(actual, expected)
        self.assertEqual(expected_log, self.path.read_bytes())

    def test_corruption_does_not_modify_input_or_benchmark(self):
        original = self.df.copy(deep=True)
        benchmark_path = self.path.with_name("benchmark.json")
        build_test_set(self.df, benchmark_path)
        benchmark_bytes = benchmark_path.read_bytes()
        corrupt_clean_dataframe(self.df, self.path)
        assert_frame_equal(self.df, original)
        self.assertEqual(benchmark_bytes, benchmark_path.read_bytes())

    def test_rounding_and_small_corpora(self):
        for size in (10, 11, 12, 20, 24, 25):
            with self.subTest(size=size):
                result = corrupt_clean_dataframe(clean_fixture(size), self.path)
                log = json.loads(self.path.read_text())
                self.assertEqual(len(log["scenarios"]), 6)
                self.assertTrue(all(event["affected_count"] > 0 for event in log["scenarios"]))
                self.assertEqual(len(result), log["output_rows"])

    def test_date_ties_have_stable_selection(self):
        self.df["published"] = "2026-09-26"
        self.df["age_days"] = 0
        expected = corrupt_clean_dataframe(self.df, self.path)
        actual = corrupt_clean_dataframe(self.df.iloc[::-1], self.path)
        assert_frame_equal(actual, expected)

    def test_timestamp_strings_are_supported(self):
        self.df["published"] = self.df["published"] + "T12:00:00+07:00"
        result = corrupt_clean_dataframe(self.df, self.path)
        log = json.loads(self.path.read_text())
        for change in log["scenarios"][4]["changes"]:
            self.assertEqual((pd.Timestamp(change["before"]["published"]) - pd.Timestamp(change["after"]["published"])).days, 730)
        self.assertEqual(len(result), 21)

    def test_invalid_corruption_inputs_do_not_write_artifact(self):
        cases = [self.df.iloc[:9], self.df.iloc[:0], self.df.drop(columns="age_days"), pd.concat([self.df, self.df.iloc[:1]])]
        for column, value in [("summary", None), ("title", "tiny"), ("published", "invalid"), ("age_days", -1), ("age_days", "bad"), ("age_days", float("inf")), ("age_days", 0.5)]:
            invalid = self.df.copy(deep=True)
            invalid[column] = invalid[column].astype(object)
            invalid.at[0, column] = value
            cases.append(invalid)
        for invalid in cases:
            with self.subTest(shape=invalid.shape), self.assertRaises(ValueError):
                corrupt_clean_dataframe(invalid, self.path)
            self.assertFalse(self.path.exists())


if __name__ == "__main__":
    unittest.main()
