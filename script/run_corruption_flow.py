from __future__ import annotations

import sys

from pipelines.corruption_flow import main


def _configure_utf8_output() -> None:
    """Keep Vietnamese progress messages printable on Windows terminals."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")


if __name__ == "__main__":
    _configure_utf8_output()
    main()
