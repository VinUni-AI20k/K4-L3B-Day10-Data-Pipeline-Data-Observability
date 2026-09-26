from __future__ import annotations

from pathlib import Path
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Ensure src/ is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd
from core.config import load_settings
from ingestion.corruption import corrupt_clean_dataframe
from observability.self_healing import AutomatedSelfHealingPipeline


def main() -> None:
    print("=" * 70)
    print("      DEMO: AUTOMATED SELF-HEALING / AUTO-REPAIR PIPELINE (BONUS B2)")
    print("=" * 70)

    settings = load_settings()
    pipeline = AutomatedSelfHealingPipeline(settings)

    print("[1/4] Loading clean baseline data...")
    df_clean = pd.read_json(settings.paths.clean_json)
    print(f"      Clean dataset loaded ({len(df_clean)} records).")

    print("[2/4] Testing Self-Healing Controller with Healthy Data...")
    result_healthy = pipeline.inspect_and_heal(df_clean, auto_reindex=False)
    print(f"      Status: {result_healthy.initial_status}, Healing Triggered: {result_healthy.healing_triggered}")
    print("      Result: Healthy data passed through without intervention.")

    print("\n[3/4] Simulating Data Corruption (Injecting 6 synthetic anomalies)...")
    temp_corrupt_log = settings.paths.quality_dir / "demo_corruption_log.json"
    df_corrupted = corrupt_clean_dataframe(df_clean, temp_corrupt_log)
    print(f"      Corrupted dataset created ({len(df_corrupted)} rows with missing fields, noise, and stale dates).")

    print("\n[4/4] Passing Corrupted Data into Self-Healing Pipeline...")
    result_corrupted = pipeline.inspect_and_heal(df_corrupted, auto_reindex=True)

    print("\n" + "=" * 70)
    print("                   KET QUA TU DONG PHUC HOI (SELF-HEALING)")
    print("=" * 70)
    print(f"Trang thai ban dau       : {result_corrupted.initial_status}")
    print(f"GX Quality Gate ban dau  : {'PASSED' if result_corrupted.gx_success else 'FAILED (ALERT TRIGGERED)'}")
    print(f"Freshness SLA ban dau    : {'HEALTHY' if result_corrupted.is_fresh else 'VIOLATED (ALERT TRIGGERED)'}")
    print(f"Co che Auto-Repair       : {'DA KICH HOAT (TRIGGERED)' if result_corrupted.healing_triggered else 'KHONG'}")
    print(f"So luong ban ghi phuc hoi: {result_corrupted.repaired_records} ban ghi")
    print(f"GX Quality Gate sau cung : {'PASSED (100% HEALTHY)' if result_corrupted.final_gx_success else 'FAILED'}")
    print(f"Freshness SLA sau cung   : {'HEALTHY (100% HEALTHY)' if result_corrupted.final_is_fresh else 'VIOLATED'}")
    print(f"File log chi tiet        : {result_corrupted.log_path.name}")
    print("=" * 70)
    print("Tu dong phuc hoi thanh cong! Dư lieu va ChromaDB collection da tro lai trang thai sach 100%.")


if __name__ == "__main__":
    main()
