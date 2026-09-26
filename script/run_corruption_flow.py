from __future__ import annotations

from pathlib import Path
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Ensure src/ is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pipelines.corruption_flow import main


if __name__ == "__main__":
    main()

