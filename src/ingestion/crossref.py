from __future__ import annotations

from dataclasses import asdict
from dataclasses import dataclass
import html
import json
from pathlib import Path
import re
import time

import requests

from core.config import Settings
from core.utils import ensure_parent, write_json


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


def parse_crossref_payload(payload: dict) -> list[PaperRecord]:
    """Parse Crossref ``works`` payload into normalized paper records."""
    items = payload.get("message", {}).get("items", [])
    records: list[PaperRecord] = []

    for item in items:
        published_data = item.get("published") or {}
        updated_data = item.get("updated") or {}
        created_data = item.get("created") or {}
        paper_id = _clean_text(item.get("DOI"))
        title = _clean_text(_first(item.get("title")))
        summary = _clean_text(item.get("abstract"))
        if not paper_id or not title:
            continue

        authors = [
            _clean_text(" ".join(part for part in (author.get("given"), author.get("family")) if part))
            for author in (item.get("author") or [])
            if isinstance(author, dict)
        ]
        authors = [author for author in authors if author]
        categories = [_clean_text(value) for value in (item.get("subject") or [])]
        categories = [category for category in categories if category]
        published = _date_from_parts(published_data.get("date-parts"))
        updated = _date_from_parts(updated_data.get("date-parts")) or _date_from_datetime(
            created_data.get("date-time")
        ) or published
        url = _clean_text(item.get("URL")) or f"https://doi.org/{paper_id}"
        pdf_url = next(
            (_clean_text(link.get("URL")) for link in (item.get("link") or []) if link.get("content-type") == "application/pdf"),
            url,
        )

        records.append(
            PaperRecord(
                paper_id=paper_id,
                title=title,
                summary=summary,
                authors=authors,
                categories=categories,
                primary_category=categories[0] if categories else "",
                published=published,
                updated=updated,
                abs_url=url,
                pdf_url=pdf_url,
                comment=_clean_text(item.get("comment")) or f"Crossref record {paper_id}",
            )
        )
    return records


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """Fetch Crossref metadata and preserve both raw and normalized artifacts."""
    payload: dict | None = None
    raw_response: bytes | None = None
    endpoint = "https://api.crossref.org/works"
    params = {
        "query": settings.source_query,
        "filter": settings.source_filter,
        "rows": settings.max_results,
    }

    for attempt in range(3):
        try:
            response = requests.get(endpoint, params=params, timeout=20)
            if response.status_code in {429, 502, 503, 504}:
                raise requests.HTTPError(f"Crossref temporary error: {response.status_code}")
            response.raise_for_status()
            payload = response.json()
            raw_response = response.content
            break
        except (requests.RequestException, ValueError):
            if attempt == 2:
                break
            time.sleep(2**attempt)

    if payload is None:
        payload = json.loads(settings.paths.raw_api_response.read_text(encoding="utf-8"))
    elif raw_response is not None:
        ensure_parent(settings.paths.raw_api_response)
        settings.paths.raw_api_response.write_bytes(raw_response)
    records = parse_crossref_payload(payload)
    if not records:
        raise ValueError("Crossref payload did not contain valid paper records.")
    write_json(settings.paths.raw_records_json, [asdict(record) for record in records])
    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    """Load normalized ``PaperRecord`` objects from the raw records artifact."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    return [PaperRecord(**item) for item in payload]


def _first(value) -> str:
    if isinstance(value, list):
        return value[0] if value else ""
    return value or ""


def _clean_text(value) -> str:
    text = html.unescape(str(value or ""))
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _date_from_parts(parts) -> str:
    if not parts or not parts[0]:
        return ""
    values = parts[0]
    if len(values) == 1:
        return f"{values[0]:04d}"
    if len(values) == 2:
        return f"{values[0]:04d}-{values[1]:02d}"
    return f"{values[0]:04d}-{values[1]:02d}-{values[2]:02d}"


def _date_from_datetime(value) -> str:
    return str(value or "")[:10]
