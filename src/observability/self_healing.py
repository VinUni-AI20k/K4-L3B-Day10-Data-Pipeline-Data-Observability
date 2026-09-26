from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import pandas as pd

from core.config import Settings, load_settings
from core.utils import now_utc, write_csv, write_json
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from retrieval.index import LocalEmbeddingIndex


@dataclass
class SelfHealingResult:
    initial_status: str
    gx_success: bool
    is_fresh: bool
    healing_triggered: bool
    repaired_records: int
    final_gx_success: bool
    final_is_fresh: bool
    log_path: Path
    details: dict[str, Any]


class AutomatedSelfHealingPipeline:
    """Automated Self-Healing / Auto-Repair Controller (Bonus B2):
    Monitors data streams, detects Great Expectations 1.x violations or Freshness SLA breaches,
    and automatically executes Idempotent Repair from immutable raw snapshots.
    """

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or load_settings()

    def inspect_and_heal(
        self,
        df_or_path: pd.DataFrame | Path | str,
        auto_reindex: bool = True,
    ) -> SelfHealingResult:
        if isinstance(df_or_path, (str, Path)):
            p = Path(df_or_path)
            if p.suffix == ".csv":
                df = pd.read_csv(p)
            else:
                df = pd.read_json(p)
        else:
            df = df_or_path.copy()

        # Step 1: Run Quality Gate and Freshness Checks
        gx_res = run_data_quality_checks(df, self.settings, "self_healing_precheck")
        freshness_res = build_freshness_report(
            df, self.settings, self.settings.paths.quality_dir / "self_healing_precheck_freshness.json"
        )

        gx_success = gx_res.get("success", False)
        is_fresh = freshness_res.get("is_fresh", False)

        healing_log: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "input_rows": len(df),
            "precheck": {
                "gx_success": gx_success,
                "is_fresh": is_fresh,
                "stale_ratio": freshness_res.get("stale_ratio", 0.0),
            },
        }

        # Step 2: Decision Gate
        if gx_success and is_fresh:
            healing_log["action"] = "NO_ACTION_REQUIRED"
            healing_log["status"] = "HEALTHY"
            log_path = self.settings.paths.results_dir if hasattr(self.settings.paths, "results_dir") else self.settings.paths.quality_dir / "self_healing_log.json"
            write_json(log_path, healing_log)
            return SelfHealingResult(
                initial_status="HEALTHY",
                gx_success=True,
                is_fresh=True,
                healing_triggered=False,
                repaired_records=len(df),
                final_gx_success=True,
                final_is_fresh=True,
                log_path=log_path,
                details=healing_log,
            )

        # Step 3: Trigger Automated Self-Healing
        healing_log["action"] = "AUTO_REPAIR_TRIGGERED"
        violations = []
        if not gx_success:
            violations.append("Great Expectations 1.x Quality Gate violation detected")
        if not is_fresh:
            violations.append(f"Freshness SLA violation: stale_ratio={freshness_res.get('stale_ratio', 0.0)*100:.1f}% > 25%")
        healing_log["violations"] = violations

        # Execute Idempotent Repair from raw snapshot
        raw_path = self.settings.paths.raw_records_json
        if not raw_path.exists():
            raise FileNotFoundError(f"Cannot auto-repair: immutable raw snapshot missing at {raw_path}")

        raw_records = load_raw_records(raw_path)
        df_repaired = build_clean_dataframe(raw_records, now_utc())

        # Persist repaired clean artifacts
        self.settings.paths.repaired_clean_json.parent.mkdir(parents=True, exist_ok=True)
        df_repaired.to_json(self.settings.paths.repaired_clean_json, orient="records", indent=2)
        write_csv(df_repaired, self.settings.paths.repaired_clean_csv)

        # Optionally re-index ChromaDB collection
        if auto_reindex:
            LocalEmbeddingIndex.build(
                df_repaired, self.settings, self.settings.paths.repaired_embeddings_json
            )

        # Re-validate repaired data
        post_gx = run_data_quality_checks(df_repaired, self.settings, "self_healing_postcheck")
        post_freshness = build_freshness_report(
            df_repaired, self.settings, self.settings.paths.quality_dir / "self_healing_postcheck_freshness.json"
        )

        final_gx_success = post_gx.get("success", False)
        final_is_fresh = post_freshness.get("is_fresh", False)

        healing_log["postcheck"] = {
            "repaired_rows": len(df_repaired),
            "gx_success": final_gx_success,
            "is_fresh": final_is_fresh,
            "recovery_status": "FULLY_RESTORED" if (final_gx_success and final_is_fresh) else "PARTIAL",
        }

        log_path = self.settings.paths.quality_dir / "self_healing_log.json"
        write_json(log_path, healing_log)

        return SelfHealingResult(
            initial_status="VIOLATION_DETECTED",
            gx_success=gx_success,
            is_fresh=is_fresh,
            healing_triggered=True,
            repaired_records=len(df_repaired),
            final_gx_success=final_gx_success,
            final_is_fresh=final_is_fresh,
            log_path=log_path,
            details=healing_log,
        )
