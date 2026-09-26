from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
import re
import time

import requests

from core.config import Settings
from core.utils import normalize_whitespace, read_json, write_json


@dataclass(frozen=True)
class PaperRecord:
    paper_id: str
    title: str
    summary: str
    authors: list[str]
    categories: list[str]
    primary_category: str
    published: str
    updated: str
    abs_url: str
    pdf_url: str
    comment: str


_TAG_RE = re.compile(r"<[^>]+>")


def _strip_jats_tags(value: str) -> str:
    return normalize_whitespace(_TAG_RE.sub(" ", value or ""))


def _format_date_parts(date_parts: list[int]) -> str:
    if not date_parts:
        return ""
    year, month, day = (list(date_parts) + [1, 1])[:3]
    return date(year, month, day).isoformat()


def parse_crossref_payload(payload: dict) -> list[PaperRecord]:
    """Parse a Crossref `/works` payload into `PaperRecord`s, skipping invalid items."""
    items = payload.get("message", {}).get("items", [])
    records: list[PaperRecord] = []

    for item in items:
        try:
            doi = (item.get("DOI") or "").strip()
            titles = item.get("title") or []
            title = normalize_whitespace(titles[0]) if titles else ""
            date_parts = ((item.get("published") or {}).get("date-parts") or [[]])[0]
            published = _format_date_parts(date_parts)

            if not doi or not title or not published:
                continue

            summary = _strip_jats_tags(item.get("abstract", ""))

            authors = [
                normalize_whitespace(f"{author.get('given', '')} {author.get('family', '')}")
                for author in item.get("author", [])
                if author.get("given") or author.get("family")
            ]

            categories = [normalize_whitespace(subject) for subject in item.get("subject", [])]
            primary_category = categories[0] if categories else ""

            url = item.get("URL", "")

            records.append(
                PaperRecord(
                    paper_id=doi,
                    title=title,
                    summary=summary,
                    authors=authors,
                    categories=categories,
                    primary_category=primary_category,
                    published=published,
                    updated=published,
                    abs_url=url,
                    pdf_url=url,
                    comment=f"Crossref record {doi}",
                )
            )
        except (KeyError, IndexError, ValueError, TypeError):
            continue

    return records


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """Fetch from Crossref with retry on 429/503, falling back to the local raw snapshot on failure."""
    params = {
        "query.bibliographic": settings.source_query,
        "filter": settings.source_filter,
        "rows": settings.max_results,
    }

    payload: dict | None = None
    last_error: Exception | None = None
    max_attempts = 3

    for attempt in range(max_attempts):
        try:
            response = requests.get("https://api.crossref.org/works", params=params, timeout=15)
            if response.status_code in (429, 503):
                time.sleep(2**attempt)
                continue
            response.raise_for_status()
            payload = response.json()
            break
        except requests.RequestException as exc:
            last_error = exc
            time.sleep(2**attempt)

    if payload is None:
        if settings.paths.raw_api_response.exists():
            payload = read_json(settings.paths.raw_api_response)
        else:
            raise RuntimeError(
                f"Khong the goi Crossref API va khong co local snapshot de fallback: {last_error}"
            )
    else:
        write_json(settings.paths.raw_api_response, payload)

    records = parse_crossref_payload(payload)
    write_json(settings.paths.raw_records_json, [asdict(record) for record in records])
    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    """Read a `raw_records_json` snapshot and map it back to `PaperRecord`s."""
    data = read_json(path)
    return [PaperRecord(**item) for item in data]
