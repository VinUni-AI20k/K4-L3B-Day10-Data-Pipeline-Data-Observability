from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from html import unescape
import logging
from pathlib import Path
import re
import time

import requests

from core.config import Settings
from core.utils import read_json, write_json


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
    """Map Crossref API items to raw paper records; skip unusable items."""
    items = payload.get("message", {}).get("items", [])
    if not isinstance(items, list):
        raise ValueError("Crossref payload must contain message.items as a list")

    records: list[PaperRecord] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        doi = _plain_text(item.get("DOI"))
        title = _plain_text(item.get("title"))
        summary = _plain_text(item.get("abstract"))
        published = next(
            (
                parsed
                for key in ("published", "published-online", "published-print", "created")
                if (parsed := _crossref_date(item.get(key)))
            ),
            "",
        )
        if not (doi and title and summary and published):
            continue

        authors = []
        for author in item.get("author") or []:
            if isinstance(author, dict):
                name = _plain_text(author.get("name") or " ".join(
                    str(author.get(part) or "") for part in ("given", "family")
                ))
                if name:
                    authors.append(name)
        categories = [_plain_text(subject) for subject in item.get("subject") or []]
        categories = [category for category in categories if category]
        abs_url = _plain_text(item.get("URL")) or f"https://doi.org/{doi}"
        pdf_url = next(
            (
                _plain_text(link.get("URL"))
                for link in item.get("link") or []
                if isinstance(link, dict) and link.get("content-type") == "application/pdf" and link.get("URL")
            ),
            abs_url,
        )
        updated = next(
            (parsed for key in ("updated", "deposited") if (parsed := _crossref_date(item.get(key)))),
            published,
        )
        records.append(PaperRecord(
            paper_id=doi,
            title=title,
            summary=summary,
            authors=authors,
            categories=categories,
            primary_category=categories[0] if categories else "",
            published=published,
            updated=updated,
            abs_url=abs_url,
            pdf_url=pdf_url,
            comment=f"Crossref record {doi}",
        ))
    return records


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """Use a snapshot by default; persist a successful live refresh of both artifacts."""
    paths = settings.paths
    if not settings.refresh_source:
        if paths.raw_records_json.exists():
            return load_raw_records(paths.raw_records_json)
        if paths.raw_api_response.exists():
            return load_raw_records(paths.raw_api_response)

    params = {"query": settings.source_query, "filter": settings.source_filter, "rows": settings.max_results}
    try:
        for attempt in range(3):
            response = requests.get("https://api.crossref.org/works", params=params, timeout=20)
            if response.status_code in (429, 503) and attempt < 2:
                time.sleep(2 ** attempt)
                continue
            response.raise_for_status()
            payload = response.json()
            records = parse_crossref_payload(payload)
            if not records:
                raise ValueError("Crossref returned no usable records")
            write_json(paths.raw_api_response, payload)
            write_json(paths.raw_records_json, [record.__dict__ for record in records])
            return records
    except (requests.RequestException, ValueError) as exc:
        logging.warning("Crossref request failed; using local snapshot: %s", exc)

    if paths.raw_records_json.exists():
        return load_raw_records(paths.raw_records_json)
    if paths.raw_api_response.exists():
        return load_raw_records(paths.raw_api_response)
    raise RuntimeError("Crossref unavailable and no local raw snapshot exists")


def load_raw_records(path: Path) -> list[PaperRecord]:
    """Read either the parsed-record snapshot or a Crossref response snapshot."""
    payload = read_json(path)
    if isinstance(payload, dict):
        return parse_crossref_payload(payload)
    if not isinstance(payload, list):
        raise ValueError("Raw records snapshot must be a JSON array")
    records = []
    for row in payload:
        if not isinstance(row, dict):
            continue
        records.append(PaperRecord(
            paper_id=str(row.get("paper_id") or ""),
            title=str(row.get("title") or ""),
            summary=str(row.get("summary") or ""),
            authors=list(row.get("authors") or []),
            categories=list(row.get("categories") or []),
            primary_category=str(row.get("primary_category") or ""),
            published=str(row.get("published") or ""),
            updated=str(row.get("updated") or ""),
            abs_url=str(row.get("abs_url") or ""),
            pdf_url=str(row.get("pdf_url") or ""),
            comment=str(row.get("comment") or ""),
        ))
    return records


def _plain_text(value: object) -> str:
    if isinstance(value, list):
        value = value[0] if value else ""
    text = unescape(str(value or ""))
    text = re.sub(r"<[^>]*>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _crossref_date(value: object) -> str:
    if not isinstance(value, dict):
        return ""
    parts = value.get("date-parts")
    if isinstance(parts, list) and parts and isinstance(parts[0], list) and parts[0]:
        try:
            year = int(parts[0][0])
            month = int(parts[0][1]) if len(parts[0]) > 1 else 1
            day = int(parts[0][2]) if len(parts[0]) > 2 else 1
            return date(year, month, day).isoformat()
        except (TypeError, ValueError):
            return ""
    timestamp = value.get("date-time")
    if timestamp:
        try:
            return date.fromisoformat(str(timestamp)[:10]).isoformat()
        except ValueError:
            pass
    return ""
