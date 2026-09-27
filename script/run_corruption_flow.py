from __future__ import annotations

from pathlib import Path
import os
import sys

for name in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(name, "1")
for name in ("HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE", "HF_HUB_DISABLE_TELEMETRY"):
    os.environ.setdefault(name, "1")
os.environ.setdefault("RUN_RAGAS", "0")
os.environ.setdefault("GX_ANALYTICS_ENABLED", "false")
os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pipelines.corruption_flow import main


if __name__ == "__main__":
    main()
