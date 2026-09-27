"""Shared identity and abstention rules for extractive QA and the tool agent."""
from __future__ import annotations

import re

ABSTENTION = "I don't know from the indexed corpus."


def explicit_paper_reference(question: str) -> str | None:
    """Prefer a DOI (quoted or bare), otherwise an explicitly quoted title."""
    doi = re.search(r"\b10\.[A-Za-z0-9.-]+/[^\s\"'<>]+", question, flags=re.I)
    if doi:
        return doi.group(0).rstrip(".,;?!").lower()
    quoted = re.search(r"'([^']+)'|\"([^\"]+)\"", question)
    return (quoted.group(1) or quoted.group(2)).strip() if quoted else None
