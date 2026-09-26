from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
from html import unescape
import json
from pathlib import Path
import re
import time

import requests

from core.config import Settings


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
    """Convert Crossref works into normalized paper records."""

    def plain_text(value: object) -> str:
        if not isinstance(value, str):
            return ""
        text = unescape(value)
        return " ".join(re.sub(r"<[^>]*>", " ", text).split())

    def crossref_date(item: dict, *fields: str) -> str:
        for field in fields:
            value = item.get(field)
            if not isinstance(value, dict):
                continue
            parts = value.get("date-parts")
            if isinstance(parts, list) and parts and isinstance(parts[0], list) and parts[0]:
                try:
                    year = int(parts[0][0])
                    month = int(parts[0][1]) if len(parts[0]) > 1 else 1
                    day = int(parts[0][2]) if len(parts[0]) > 2 else 1
                    return date(year, month, day).isoformat()
                except (TypeError, ValueError):
                    pass
            timestamp = value.get("date-time")
            if isinstance(timestamp, str):
                try:
                    return date.fromisoformat(timestamp[:10]).isoformat()
                except ValueError:
                    pass
        return ""

    message = payload.get("message") if isinstance(payload, dict) else None
    items = message.get("items") if isinstance(message, dict) else None
    if not isinstance(items, list):
        raise ValueError("Crossref payload must contain a list at message.items")

    records = []
    for item in items:
        if not isinstance(item, dict):
            continue
        doi = plain_text(item.get("DOI"))
        titles = item.get("title")
        title = plain_text(titles[0]) if isinstance(titles, list) and titles else plain_text(titles)
        summary = plain_text(item.get("abstract"))
        published = crossref_date(item, "published", "published-online", "published-print", "issued")
        if not all((doi, title, summary, published)):
            continue

        authors = []
        source_authors = item.get("author")
        if not isinstance(source_authors, list):
            source_authors = []
        for author in source_authors:
            if isinstance(author, dict):
                name = plain_text(" ".join(str(author.get(part) or "") for part in ("given", "family")))
                name = name or plain_text(author.get("name"))
                if name:
                    authors.append(name)

        subjects = item.get("subject")
        categories = [plain_text(subject) for subject in subjects] if isinstance(subjects, list) else []
        categories = [category for category in categories if category]
        abs_url = plain_text(item.get("URL")) or f"https://doi.org/{doi}"
        pdf_url = abs_url
        source_links = item.get("link")
        if not isinstance(source_links, list):
            source_links = []
        for link in source_links:
            if isinstance(link, dict) and link.get("content-type") == "application/pdf" and link.get("URL"):
                pdf_url = link["URL"]
                break

        records.append(PaperRecord(
            paper_id=doi,
            title=title,
            summary=summary,
            authors=authors,
            categories=categories,
            primary_category=categories[0] if categories else "",
            published=published,
            updated=crossref_date(item, "deposited", "indexed", "created") or published,
            abs_url=abs_url,
            pdf_url=pdf_url,
            comment=f"Crossref record {doi}",
        ))
    return records


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """Fetch Crossref works, falling back to the preserved response offline."""
    raw_path = settings.paths.raw_api_response
    records_path = settings.paths.raw_records_json
    params = {
        "query": settings.source_query,
        "filter": settings.source_filter,
        "rows": settings.max_results,
    }

    raw_response = None
    payload = None
    for attempt in range(3):
        try:
            response = requests.get(
                "https://api.crossref.org/works",
                params=params,
                headers={"User-Agent": "data-observability-lab/1.0"},
                timeout=15,
            )
            if response.status_code in (429, 503) and attempt < 2:
                time.sleep(attempt + 1)
                continue
            response.raise_for_status()
            candidate = json.loads(response.content)
            if not isinstance(candidate, dict) or not isinstance(candidate.get("message"), dict):
                raise ValueError("Invalid Crossref response")
            if not isinstance(candidate["message"].get("items"), list):
                raise ValueError("Crossref response has no items list")
            payload = candidate
            raw_response = response.content
            break
        except (requests.RequestException, ValueError):
            break
    if raw_response is None:
        if not raw_path.is_file():
            raise RuntimeError(f"Crossref unavailable and no offline snapshot exists at {raw_path}")
        payload = json.loads(raw_path.read_bytes())

    records = parse_crossref_payload(payload)
    if raw_response is not None:
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        raw_path.write_bytes(raw_response)
    records_path.parent.mkdir(parents=True, exist_ok=True)
    records_path.write_text(
        json.dumps([asdict(record) for record in records], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    """Restore paper records from the saved raw-records artifact."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError(f"Expected a list of paper records in {path}")
    return [PaperRecord(**item) for item in payload]
