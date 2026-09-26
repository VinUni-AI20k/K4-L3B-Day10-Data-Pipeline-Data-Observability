from __future__ import annotations

from dataclasses import asdict, dataclass
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


def _strip_jats(text: str) -> str:
    if not text:
        return ""
    without_tags = re.sub(r"<[^>]+>", " ", text)
    return normalize_whitespace(without_tags)


def _format_date_parts(date_field: dict | None) -> str:
    if not date_field:
        return ""
    parts = date_field.get("date-parts")
    if not parts or not parts[0]:
        return ""
    values = parts[0]
    year = values[0] if len(values) > 0 else None
    month = values[1] if len(values) > 1 else 1
    day = values[2] if len(values) > 2 else 1
    if year is None:
        return ""
    try:
        return f"{int(year):04d}-{int(month or 1):02d}-{int(day or 1):02d}"
    except (TypeError, ValueError):
        return ""


def parse_crossref_payload(payload: dict) -> list[PaperRecord]:
    """Parse Crossref payload thanh list PaperRecord."""
    items = payload.get("message", {}).get("items", [])
    records: list[PaperRecord] = []
    for item in items:
        doi = item.get("DOI")
        titles = item.get("title") or []
        title = normalize_whitespace(titles[0]) if titles else ""
        if not doi or not title:
            continue

        summary = _strip_jats(item.get("abstract", ""))

        authors = []
        for author in item.get("author", []):
            given = author.get("given", "")
            family = author.get("family", "")
            full_name = normalize_whitespace(f"{given} {family}")
            if full_name:
                authors.append(full_name)

        categories = [normalize_whitespace(subject) for subject in item.get("subject", []) if subject]
        primary_category = categories[0] if categories else ""

        published = _format_date_parts(item.get("published") or item.get("published-print") or item.get("published-online"))
        updated = _format_date_parts(item.get("created")) or published

        url = item.get("URL", "") or f"https://doi.org/{doi}"

        records.append(
            PaperRecord(
                paper_id=doi,
                title=title,
                summary=summary,
                authors=authors,
                categories=categories,
                primary_category=primary_category,
                published=published,
                updated=updated,
                abs_url=url,
                pdf_url=url,
                comment="",
            )
        )
    return records


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """Goi Crossref API (hoac fallback snapshot), luu raw artifacts va parse thanh records."""
    payload: dict | None = None

    if not settings.refresh_source and settings.paths.raw_api_response.exists():
        payload = read_json(settings.paths.raw_api_response)
    else:
        params = {
            "query": settings.source_query,
            "filter": settings.source_filter,
            "rows": settings.max_results,
        }
        max_attempts = 3
        for attempt in range(1, max_attempts + 1):
            try:
                response = requests.get(
                    "https://api.crossref.org/works",
                    params=params,
                    timeout=15,
                )
                if response.status_code in {429, 503}:
                    time.sleep(min(2**attempt, 8))
                    continue
                response.raise_for_status()
                payload = response.json()
                break
            except requests.RequestException:
                time.sleep(min(2**attempt, 8))
                continue

        if payload is None:
            if settings.paths.raw_api_response.exists():
                payload = read_json(settings.paths.raw_api_response)
            else:
                raise RuntimeError("Unable to fetch Crossref data and no offline snapshot is available.")

    write_json(settings.paths.raw_api_response, payload)
    records = parse_crossref_payload(payload)
    write_json(settings.paths.raw_records_json, [asdict(record) for record in records])
    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    """Doc JSON snapshot va map thanh `PaperRecord`."""
    raw_items = read_json(path)
    return [PaperRecord(**item) for item in raw_items]
