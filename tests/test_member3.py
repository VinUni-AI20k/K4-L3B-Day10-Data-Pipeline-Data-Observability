"""Tests for Member 3 deliverables: orchestration, reporting, and idempotent repair."""
from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from core.utils import read_json
from observability.reporting import generate_corruption_report, generate_phase1_report


class Member3Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.temp_dir = Path(self.temp.name)

    def test_generate_phase1_report(self):
        report_path = self.temp_dir / "reports" / "phase1_report.md"
        source_summary = {
            "api": "Crossref REST API",
            "query": "agentic retrieval",
            "filter": "from-pub-date:2026-01-01",
            "count": 24,
            "timestamp": "2026-09-26T00:00:00Z",
        }
        metrics = {
            "samples": 10,
            "retrieval_hit_rate": 1.0,
            "mean_token_f1": 0.985,
            "judge_accuracy": 1.0,
            "mean_judge_score": 5.0,
        }
        quality = {
            "success": True,
            "gx_success": True,
            "checks": [
                {"expectation_type": "ExpectTableRowCountToBeBetween", "success": True, "kwargs": {}},
                {"expectation_type": "ExpectColumnValuesToNotBeNull", "success": True, "kwargs": {"column": "paper_id"}},
            ],
        }
        freshness = {
            "is_fresh": True,
            "stale_ratio": 0.0417,
            "latest_published": "2026-09-20",
            "oldest_published": "2026-04-10",
            "stale_rows": 1,
            "total_rows": 24,
            "freshness_threshold_days": 180,
        }

        generate_phase1_report(report_path, source_summary, metrics, quality, freshness)
        self.assertTrue(report_path.is_file())
        content = report_path.read_text(encoding="utf-8")
        self.assertIn("# Báo Cáo Pha 1 — Baseline Data Pipeline & Observability", content)
        self.assertIn("100.00%", content)
        self.assertIn("Crossref REST API", content)
        self.assertIn("ExpectTableRowCountToBeBetween", content)
        self.assertIn("FRESH", content)

    def test_generate_corruption_report_three_states(self):
        report_path = self.temp_dir / "reports" / "corruption_report.md"
        baseline_metrics = {
            "retrieval_hit_rate": 1.0,
            "mean_token_f1": 1.0,
            "judge_accuracy": 1.0,
            "mean_judge_score": 5.0,
        }
        corrupted_metrics = {
            "retrieval_hit_rate": 0.8,
            "mean_token_f1": 0.6,
            "judge_accuracy": 0.6,
            "mean_judge_score": 3.4,
        }
        repaired_metrics = {
            "retrieval_hit_rate": 1.0,
            "mean_token_f1": 1.0,
            "judge_accuracy": 1.0,
            "mean_judge_score": 5.0,
        }
        corrupted_quality = {"gx_success": False, "success": False}
        repaired_quality = {"gx_success": True, "success": True}
        corrupted_freshness = {"is_fresh": False, "stale_ratio": 0.4762}
        repaired_freshness = {"is_fresh": True, "stale_ratio": 0.0417}

        generate_corruption_report(
            report_path=report_path,
            baseline_metrics=baseline_metrics,
            corrupted_metrics=corrupted_metrics,
            repaired_metrics=repaired_metrics,
            corrupted_quality=corrupted_quality,
            repaired_quality=repaired_quality,
            corrupted_freshness=corrupted_freshness,
            repaired_freshness=repaired_freshness,
        )

        self.assertTrue(report_path.is_file())
        content = report_path.read_text(encoding="utf-8")
        self.assertIn("Báo Cáo Đối Chiếu 3 Trạng Thái: Baseline vs Corrupted vs Repaired", content)
        self.assertIn("Retrieval Hit Rate", content)
        self.assertIn("Silent Failure", content)
        self.assertIn("Idempotent", content)
        self.assertIn("100.00%", content)
        self.assertIn("80.00%", content)

    def test_idempotent_repair_consistency(self):
        """Chứng minh tính idempotent: nạp cùng snapshot raw luôn cho ra cùng DataFrame sạch."""
        from datetime import UTC, datetime
        from ingestion.cleaning import build_clean_dataframe
        from ingestion.crossref import load_raw_records
        from core.config import load_settings

        settings = load_settings()
        records = load_raw_records(settings.paths.raw_records_json)
        fixed_date = datetime(2026, 9, 26, 0, 0, 0, tzinfo=UTC)

        df1 = build_clean_dataframe(records, run_date=fixed_date)
        df2 = build_clean_dataframe(records, run_date=fixed_date)

        pd.testing.assert_frame_equal(df1, df2)
        self.assertEqual(len(df1), 24)
        self.assertTrue(df1["paper_id"].is_unique)


if __name__ == "__main__":
    unittest.main()
