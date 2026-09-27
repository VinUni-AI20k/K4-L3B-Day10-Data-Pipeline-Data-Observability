"""Checks for honest CP6 scoring, trace redaction, and sealed-evidence replay."""
from __future__ import annotations

from contextlib import redirect_stdout
import argparse
import io
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "script"))
from run_live_demo import (ABSTENTION, build_cases, checked_name, render_report,
                           replay, safe_error, sanitize_trace, score_case, sha)


class LiveDemoTests(unittest.TestCase):
    def setUp(self):
        self.baseline = [{"paper_id": "10.1/drop", "published": "2026-07-22"},
                         {"paper_id": "10.1/stale", "published": "2026-05-12"},
                         {"paper_id": "10.1/stable", "published": "2026-05-01"}]
        self.corrupted = [{"paper_id": "10.1/stale", "published": "2025-05-12"},
                          {"paper_id": "10.1/stable", "published": "2026-05-01"}]
        self.log = {"events": [{"type": "drop_latest", "paper_ids": ["10.1/drop"]},
                               {"type": "stale_date", "paper_ids": ["10.1/stale"]}]}
        self.cases = build_cases(self.baseline, self.corrupted, self.log)

    def trace(self, doi):
        return [{"type": "ai", "tool_calls": [{"name": "lookup_paper", "args": {"paper_id_or_title": doi}}]},
                {"type": "tool", "name": "lookup_paper", "content": "Published: 2025-05-12"}]

    def test_corrupted_date_is_context_grounded_but_wrong_against_raw(self):
        case = next(c for c in self.cases if c["id"] == "stale_date")
        scores = score_case(case, "corrupted", "2025-05-12", self.trace(case["paper_id"]))
        self.assertTrue(scores["passed"])
        self.assertFalse(scores["correct_against_raw"])
        self.assertEqual(case["expected_by_state"]["repaired"], case["ground_truth"])

    def test_dropped_and_absent_are_distinct_from_restored_record(self):
        dropped, absent = self.cases[0], self.cases[-1]
        self.assertEqual(dropped["expected_by_state"]["corrupted"], ABSTENTION)
        self.assertNotEqual(dropped["ground_truth"], ABSTENTION)
        self.assertTrue(all(v == ABSTENTION for v in absent["expected_by_state"].values()))

    def test_answer_without_exact_completed_tool_does_not_pass(self):
        case = self.cases[0]
        for trace in ([], self.trace("10.1/wrong"), self.trace(case["paper_id"])[:1]):
            self.assertFalse(score_case(case, "baseline", case["ground_truth"], trace)["passed"])

    def test_real_model_garbage_prefix_is_not_silently_removed(self):
        case = next(c for c in self.cases if c["id"] == "stable_control")
        answer = "2ellsells user\n" + case["ground_truth"]
        checks = score_case(case, "baseline", answer, self.trace(case["paper_id"]))
        self.assertFalse(checks["passed"])
        self.assertFalse(checks["correct_against_raw"])

    def test_trace_excludes_headers_and_hidden_reasoning(self):
        message = SimpleNamespace(type="ai", content=[{"type": "reasoning", "text": "private-thought"},
                                                      {"type": "text", "text": "2026-07-22"}],
                                  tool_calls=[], usage_metadata={"total_tokens": 5},
                                  response_metadata={"model_name": "test", "headers": {"Authorization": "secret"}},
                                  additional_kwargs={"reasoning_content": "private-thought"})
        encoded = json.dumps(sanitize_trace([message]))
        self.assertNotIn("secret", encoded)
        self.assertNotIn("private-thought", encoded)
        self.assertIn("2026-07-22", encoded)

    def test_error_diagnostics_redact_key_and_account(self):
        error = SimpleNamespace(status_code=429, body={"error": {"message": "Provider error",
            "metadata": {"raw": "rate limited example-secret user_privateAccount",
                         "limit_source": "upstream_provider_shared_pool"}},
            "user_id": "user_privateAccount", "headers": {"Authorization": "example-secret"}})
        output = json.dumps(safe_error(error, "example-secret"))
        self.assertNotIn("example-secret", output)
        self.assertNotIn("user_privateAccount", output)
        self.assertIn("upstream_provider_shared_pool", output)

    def test_callable_sdk_error_code_is_json_serializable(self):
        error = SimpleNamespace(code=lambda: 429)
        output = safe_error(error)
        self.assertIsNone(output["http_status"])
        json.dumps(output)

    def test_replay_rejects_tampered_evidence(self):
        parent = ROOT / "acceptance_runs/live_demo_tests"
        parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=parent) as temp:
            directory = Path(temp)
            report = directory / "online_report.md"
            report.write_text("verified", encoding="utf-8")
            (directory / "demo_manifest.json").write_text(json.dumps({"status": "complete", "artifacts": {report.name: sha(report)}}))
            with redirect_stdout(io.StringIO()):
                self.assertEqual(replay(directory), 0)
            report.write_text("changed", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "changed"):
                replay(directory)

    def test_offline_report_never_claims_online_complete(self):
        report = render_report({"status": "offline_rehearsal_only", "model": "test",
                                "pipeline_run_id": "test", "answers": []})
        self.assertIn("offline_rehearsal_only", report)
        self.assertNotIn("**complete**", report)

    def test_demo_id_cannot_escape_output_directory(self):
        for name in ("../raw", "C:/outside", "..", "test/demo"):
            with self.assertRaises(argparse.ArgumentTypeError):
                checked_name(name)


if __name__ == "__main__":
    unittest.main()
