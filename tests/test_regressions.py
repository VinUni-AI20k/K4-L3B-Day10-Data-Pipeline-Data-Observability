"""Regression tests for data protection, run reuse, grounding and repair gates.

Run: .venv/Scripts/python.exe -B -m unittest discover -s tests -v
Real GX and LangChain are used; model/network/index failure cases use explicit doubles.
"""
from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
for key in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[key] = "1"
os.environ.update(LLM_PROVIDER="mock", RUN_RAGAS="0", HF_HUB_OFFLINE="1",
                  GX_ANALYTICS_ENABLED="false", ANONYMIZED_TELEMETRY="False")

from core.config import load_settings, with_output_dir
from core.utils import read_json, write_json
from evaluation.metrics import evaluate_pipeline
from evaluation.testset import build_test_set
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import load_raw_records, parse_crossref_payload
from observability.quality import build_freshness_report, run_data_quality_checks
from pipelines.corruption_flow import run_corruption_pipeline
from pipelines.phase1 import run_phase1_pipeline
from pipelines.runs import RunStore, digest, inventory
from retrieval.agent import build_agent, run_agent_question
from retrieval.identity import ABSTENTION
from retrieval.index import LocalEmbeddingIndex, SearchResult
from retrieval.qa import answer_question


class MemoryEmbeddings:
    def __init__(self, *args):
        pass

    def embed_documents(self, texts):
        return [[1.0, 0.0] for _ in texts]


class MemoryCollection:
    def __init__(self):
        self.ids = []

    def add(self, **kwargs):
        self.ids = kwargs["ids"]

    def count(self):
        return len(self.ids)

    def query(self, **kwargs):
        return {"ids": [self.ids[:1]]}


class MemoryClient:
    def __init__(self):
        self.collections = {"old-good": MemoryCollection()}
        self.closed = False

    def create_collection(self, name, **kwargs):
        self.collections[name] = MemoryCollection()
        return self.collections[name]

    def get_collection(self, name):
        return self.collections[name]

    def delete_collection(self, name):
        del self.collections[name]

    def close(self):
        self.closed = True


class ManifestIndex:
    def __init__(self, df):
        self.documents = LocalEmbeddingIndex._build_documents(df)
        self.search_calls = 0

    def lookup(self, value):
        return next((d for d in self.documents if value.lower() in
                     (d["paper_id"].lower(), d["title"].lower())), None)

    def search(self, query, top_k=None):
        self.search_calls += 1
        return [SearchResult(d["paper_id"], d["title"], .5, d["content"], d["metadata"])
                for d in self.documents[:top_k or 4]]


class RegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = replace(load_settings(), llm_provider="mock", model_name="mock",
                           refresh_source=False, refresh_test_set=False)
        cls.raw = load_raw_records(cls.base.paths.raw_records_json)
        cls.date = datetime(2026, 9, 27, tzinfo=UTC)
        cls.df = build_clean_dataframe(cls.raw, cls.date)
        cls.temp_parent = ROOT / "acceptance_runs" / "regression_tests"
        cls.temp_parent.mkdir(parents=True, exist_ok=True)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=self.temp_parent)
        self.directory = Path(self.temp.name)
        self.settings = with_output_dir(self.base, self.directory / "output")

    def tearDown(self):
        self.temp.cleanup()

    def test_quality_failure_never_builds_index_or_publishes_clean(self):
        import pipelines.phase1 as phase1
        with patch.object(phase1, "load_raw_records", return_value=self.raw[:-1]), \
                patch.object(phase1.LocalEmbeddingIndex, "build") as build:
            with self.assertRaisesRegex(RuntimeError, "before indexing"):
                run_phase1_pipeline(self.settings, run_at=self.date)
        build.assert_not_called()
        self.assertFalse(self.settings.paths.clean_json.exists())
        self.assertTrue(self.settings.paths.baseline_quality_report.exists())

    def test_invalid_frozen_benchmark_never_builds_index(self):
        questions = build_test_set(self.df)
        questions[0]["ground_truth"] = "tampered answer"
        with patch("pipelines.phase1.LocalEmbeddingIndex.build") as build:
            with self.assertRaisesRegex(ValueError, "ground truth"):
                run_phase1_pipeline(self.settings, run_at=self.date, test_set=questions)
        build.assert_not_called()

    def test_index_encoding_failure_preserves_previous_manifest(self):
        write_json(self.settings.paths.embeddings_json, {"collection_name": "old-good"})
        before = digest(self.settings.paths.embeddings_json)
        with patch("retrieval.index.MiniLMEmbeddings") as model, \
                patch("retrieval.index.chromadb.PersistentClient") as client:
            model.return_value.embed_documents.side_effect = RuntimeError("encode failed")
            with self.assertRaisesRegex(RuntimeError, "encode failed"):
                LocalEmbeddingIndex.build(self.df, self.settings)
        client.assert_not_called()
        self.assertEqual(before, digest(self.settings.paths.embeddings_json))

    def test_index_add_failure_keeps_old_collection(self):
        client = MemoryClient()
        write_json(self.settings.paths.embeddings_json, {"collection_name": "old-good"})
        before = digest(self.settings.paths.embeddings_json)
        with patch("retrieval.index.MiniLMEmbeddings", MemoryEmbeddings), \
                patch("retrieval.index.chromadb.PersistentClient", return_value=client), \
                patch.object(MemoryCollection, "add", side_effect=RuntimeError("add failed")):
            with self.assertRaisesRegex(RuntimeError, "add failed"):
                LocalEmbeddingIndex.build(self.df, self.settings)
        self.assertEqual(set(client.collections), {"old-good"})
        self.assertEqual(before, digest(self.settings.paths.embeddings_json))
        self.assertTrue(client.closed)

    def test_index_publication_failure_keeps_old_manifest_and_collection(self):
        client = MemoryClient()
        write_json(self.settings.paths.embeddings_json, {"collection_name": "old-good"})
        before = digest(self.settings.paths.embeddings_json)
        with patch("retrieval.index.MiniLMEmbeddings", MemoryEmbeddings), \
                patch("retrieval.index.chromadb.PersistentClient", return_value=client), \
                patch("retrieval.index.write_json", side_effect=OSError("disk full")):
            with self.assertRaisesRegex(OSError, "disk full"):
                LocalEmbeddingIndex.build(self.df, self.settings)
        self.assertEqual(set(client.collections), {"old-good"})
        self.assertEqual(before, digest(self.settings.paths.embeddings_json))

    def test_index_success_publishes_new_collection_without_deleting_old(self):
        client = MemoryClient()
        with patch("retrieval.index.MiniLMEmbeddings", MemoryEmbeddings), \
                patch("retrieval.index.chromadb.PersistentClient", return_value=client):
            index = LocalEmbeddingIndex.build(self.df, self.settings)
        manifest = read_json(self.settings.paths.embeddings_json)
        self.assertIn("old-good", client.collections)
        self.assertNotEqual(index.collection_name, "old-good")
        self.assertEqual(manifest["collection_name"], index.collection_name)
        self.assertFalse(Path(manifest["persist_path"]).is_absolute())
        index.close()

    def test_relative_manifest_load_resolves_from_its_new_location(self):
        target = self.directory / "moved" / "embeddings" / "index.json"
        write_json(target, {"schema_version": 2, "embedding_model": self.settings.embedding_model,
                            "persist_path": "../chroma", "collection_name": "new", "documents": []})
        with patch.object(LocalEmbeddingIndex, "__init__", return_value=None) as constructor:
            LocalEmbeddingIndex.load(self.settings, target)
        self.assertEqual(constructor.call_args.kwargs["persist_path"], (target.parent / "../chroma").resolve())

    def test_atomic_write_failure_keeps_old_file(self):
        target = self.directory / "manifest.json"
        write_json(target, {"good": True})
        before = digest(target)
        with patch("core.utils.os.replace", side_effect=OSError("replace failed")):
            with self.assertRaises(OSError):
                write_json(target, {"good": False})
        self.assertEqual(before, digest(target))
        self.assertEqual(list(self.directory.glob("*.tmp")), [])

    def test_completed_run_reuses_without_writing(self):
        root = self.directory / "run"
        operation = Mock(return_value={"ok": True})
        with RunStore(self.base, root).locked() as run:
            run.execute("baseline", operation)
        before = inventory(root)
        with RunStore(self.base, root).locked() as run:
            self.assertEqual(run.execute("baseline", operation), {"ok": True})
        self.assertEqual(operation.call_count, 1)
        self.assertEqual(before, inventory(root))

    def test_failed_run_retries_in_new_attempt_and_retains_diagnostic(self):
        root = self.directory / "run"
        def fail(settings):
            write_json(settings.paths.baseline_quality_report, {"failure": True})
            raise RuntimeError("deliberate failure")
        with RunStore(self.base, root).locked() as run:
            with self.assertRaisesRegex(RuntimeError, "deliberate"):
                run.execute("baseline", fail)
        with RunStore(self.base, root).locked() as run:
            run.execute("baseline", lambda settings: {"ok": True})
            attempts = run.manifest["stages"]["baseline"]["attempts"]
        self.assertEqual([a["status"] for a in attempts], ["failed", "complete"])
        self.assertTrue((root / "baseline/attempt-001/quality/baseline_quality_report.json").is_file())

    def test_completed_artifact_tampering_is_rejected(self):
        root = self.directory / "run"
        with RunStore(self.base, root).locked() as run:
            run.execute("baseline", lambda settings: {"ok": True})
        write_json(root / "baseline/attempt-001/stage_result.json", {"tampered": True})
        with self.assertRaisesRegex(ValueError, "Artifact missing or changed"):
            with RunStore(self.base, root).locked():
                pass

    def test_changed_configuration_is_not_silently_reused(self):
        root = self.directory / "run"
        with RunStore(self.base, root).locked():
            pass
        with self.assertRaisesRegex(ValueError, "choose a new"):
            with RunStore(replace(self.base, top_k=2), root).locked():
                pass

    def test_changed_source_is_not_silently_reused(self):
        root = self.directory / "run"
        with RunStore(self.base, root).locked():
            pass
        with patch("pipelines.runs.source_inventory", return_value={"source": "changed"}):
            with self.assertRaisesRegex(ValueError, "choose a new"):
                with RunStore(self.base, root).locked():
                    pass

    def test_run_lock_blocks_concurrent_writer(self):
        root = self.directory / "run"
        with RunStore(self.base, root).locked():
            with self.assertRaisesRegex(RuntimeError, "locked"):
                with RunStore(self.base, root).locked():
                    pass

    def test_source_raw_is_preserved_and_run_copies_match(self):
        original = inventory(self.base.paths.raw_records_json.parent)
        with RunStore(self.base, self.directory / "run").locked() as run:
            self.assertEqual(digest(self.base.paths.raw_records_json), digest(run.root / "raw/crossref_records.json"))
        self.assertEqual(original, inventory(self.base.paths.raw_records_json.parent))

    def test_response_only_bootstrap_does_not_write_original_raw(self):
        settings = replace(self.base, paths=replace(self.base.paths,
            raw_records_json=self.directory / "does-not-exist.json"))
        with RunStore(settings, self.directory / "run").locked() as run:
            self.assertEqual(len(load_raw_records(run.root / "raw/crossref_records.json")), 24)
        self.assertFalse(settings.paths.raw_records_json.exists())

    def test_existing_data_directory_cannot_be_used_as_run_output(self):
        with self.assertRaises(ValueError):
            RunStore(self.base, self.base.paths.clean_json.parent.parent)

    def test_missing_identity_abstains_without_semantic_substitution(self):
        index = ManifestIndex(self.df)
        for question in ("Who authored '10.9999/missing'?", "When was 10.9999/missing published?",
                         'What does "Missing title" describe?'):
            result = answer_question(question, self.settings, index)
            self.assertTrue(result.abstained)
            self.assertEqual(result.answer_doc_ids, [])
            self.assertEqual(result.answer, ABSTENTION)
        self.assertEqual(index.search_calls, 0)

    def test_missing_summary_abstains_but_keeps_retrieval_evidence(self):
        frame = self.df.copy()
        frame.loc[0, "summary"] = ""
        index = ManifestIndex(frame)
        result = answer_question(f"What does '{frame.iloc[0]['paper_id']}' describe?", self.settings, index)
        self.assertTrue(result.abstained)
        self.assertEqual(result.answer_doc_ids, [])
        self.assertIn(frame.iloc[0]["paper_id"], result.retrieved_doc_ids)

    def test_mock_tool_agent_handles_known_and_unknown_papers(self):
        index = ManifestIndex(self.df)
        agent = build_agent(self.settings, index)
        for question in build_test_set(self.df):
            self.assertEqual(run_agent_question(agent, question["question"]), question["ground_truth"])
        self.assertEqual(run_agent_question(agent, "Who authored '10.9999/missing'?"), ABSTENTION)

    def test_equal_answer_with_wrong_source_has_zero_grounded_score(self):
        from retrieval.qa import AnswerResult
        question = build_test_set(self.df)[0]
        write_json(self.settings.paths.eval_testset, [question])
        result = AnswerResult(question["question"], question["ground_truth"], ["wrong-doi"], ["context"],
                              ["title"], ["wrong-doi"], False)
        with patch("evaluation.metrics.answer_question", return_value=result):
            measured = evaluate_pipeline(self.settings, None, self.settings.paths.eval_testset,
                                         self.settings.paths.baseline_metrics, self.settings.paths.baseline_answers)
        self.assertEqual(measured.summary["mean_token_f1"], 1)
        self.assertEqual(measured.summary["mean_grounded_token_f1"], 0)
        self.assertEqual(measured.summary["heuristic_judge_count"], 1)

    def test_freshness_boundaries_and_invalid_ages(self):
        for stale_count, expected in ((6, True), (7, False)):
            frame = self.df.copy()
            frame["age_days"] = 180
            frame.loc[:stale_count - 1, "age_days"] = 181
            self.assertEqual(build_freshness_report(frame, self.settings)["is_fresh"], expected)
        for value in (-1, float("inf"), float("-inf"), float("nan"), 1.5):
            frame = self.df.copy()
            frame["age_days"] = value
            self.assertFalse(build_freshness_report(frame, self.settings)["is_fresh"])

    def test_null_crossref_message_is_validation_error(self):
        with self.assertRaisesRegex(ValueError, "message object"):
            parse_crossref_payload({"message": None})

    def test_repaired_quality_failure_prevents_repaired_index(self):
        baseline = with_output_dir(self.base, self.directory / "baseline")
        rows = self.df.to_dict(orient="records")
        questions = build_test_set(self.df)
        write_json(baseline.paths.clean_json, rows)
        write_json(baseline.paths.eval_testset, questions)
        write_json(baseline.paths.baseline_answers, questions)
        write_json(baseline.paths.baseline_metrics, {"samples": 10})
        write_json(baseline.paths.baseline_quality_report, {"success": True})
        write_json(baseline.paths.freshness_report, {"is_fresh": True})
        index = Mock()
        with patch("pipelines.corruption_flow.run_data_quality_checks", return_value={"success": False}), \
                patch("pipelines.corruption_flow.build_freshness_report", return_value={"is_fresh": True}), \
                patch("pipelines.corruption_flow.LocalEmbeddingIndex.build", return_value=index) as build, \
                patch("pipelines.corruption_flow.evaluate_pipeline"), \
                patch("pipelines.corruption_flow.evaluate_abstention_challenges"):
            with self.assertRaisesRegex(RuntimeError, "Repaired quality gate failed"):
                run_corruption_pipeline(self.settings, baseline)
        self.assertEqual(build.call_count, 1)  # Corrupted only; repaired was never published.
        index.close.assert_called_once()


if __name__ == "__main__":
    unittest.main()
