from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
from html import unescape
from pathlib import Path
import re
import time
from typing import Any

import requests

from core.config import Settings
from core.utils import ensure_parent, normalize_whitespace, read_json, write_json


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


def _text(value: Any) -> str:
    if isinstance(value, list):
        value = " ".join(str(part) for part in value if part)
    if value is None:
        return ""
    without_tags = re.sub(r"<[^>]+>", " ", str(value))
    return normalize_whitespace(unescape(without_tags))


def _date_from_crossref(value: Any) -> str:
    if not isinstance(value, dict):
        return ""

    date_time = value.get("date-time")
    if isinstance(date_time, str) and date_time:
        return date_time[:10]

    date_parts = value.get("date-parts")
    if not isinstance(date_parts, list) or not date_parts or not date_parts[0]:
        return ""
    parts = date_parts[0]
    try:
        year = int(parts[0])
        month = int(parts[1]) if len(parts) > 1 else 1
        day = int(parts[2]) if len(parts) > 2 else 1
        return date(year, month, day).isoformat()
    except (TypeError, ValueError):
        return ""


def _first_date(item: dict[str, Any], keys: tuple[str, ...]) -> str:
    for key in keys:
        parsed = _date_from_crossref(item.get(key))
        if parsed:
            return parsed
    return ""


def parse_crossref_payload(payload: dict) -> list[PaperRecord]:
    """Parse a Crossref work-list payload into normalized paper records."""
    message = payload.get("message", {}) if isinstance(payload, dict) else {}
    items = message.get("items", []) if isinstance(message, dict) else []
    if not isinstance(items, list):
        raise ValueError("Invalid Crossref payload: message.items must be a list.")

    records: list[PaperRecord] = []
    seen_ids: set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            continue

        paper_id = _text(item.get("DOI")).lower()
        title = _text(item.get("title"))
        summary = _text(item.get("abstract"))
        published = _first_date(
            item,
            ("published", "published-print", "published-online", "issued", "created"),
        )
        if not paper_id or not title or not summary or not published or paper_id in seen_ids:
            continue

        authors: list[str] = []
        for author in item.get("author", []) or []:
            if not isinstance(author, dict):
                continue
            name = _text(
                " ".join(
                    part
                    for part in (_text(author.get("given")), _text(author.get("family")))
                    if part
                )
                or author.get("name")
            )
            if name and name not in authors:
                authors.append(name)

        categories: list[str] = []
        for subject in item.get("subject", []) or []:
            normalized = _text(subject)
            if normalized and normalized not in categories:
                categories.append(normalized)

        abs_url = _text(item.get("URL")) or f"https://doi.org/{paper_id}"
        pdf_url = ""
        for link in item.get("link", []) or []:
            if not isinstance(link, dict):
                continue
            content_type = str(link.get("content-type", "")).lower()
            candidate = _text(link.get("URL"))
            if candidate and ("pdf" in content_type or candidate.lower().endswith(".pdf")):
                pdf_url = candidate
                break

        updated = _first_date(item, ("indexed", "deposited", "created")) or published
        comment = _text(item.get("note")) or f"Crossref record {paper_id}"
        records.append(
            PaperRecord(
                paper_id=paper_id,
                title=title,
                summary=summary,
                authors=authors,
                categories=categories,
                primary_category=categories[0] if categories else "Uncategorized",
                published=published,
                updated=updated,
                abs_url=abs_url,
                pdf_url=pdf_url or abs_url,
                comment=comment,
            )
        )
        seen_ids.add(paper_id)

    return records


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """Load the bundled snapshot or refresh it from Crossref with fallback."""
    snapshot_path = settings.paths.raw_api_response
    payload: dict[str, Any] | None = None
    last_error: Exception | None = None

    if not settings.refresh_source and snapshot_path.exists():
        payload = read_json(snapshot_path)
    else:
        params = {
            "query": settings.source_query,
            "filter": settings.source_filter,
            "rows": settings.max_results,
        }
        headers = {
            "Accept": "application/json",
            "User-Agent": "day10-data-observability-lab/0.1",
        }
        retry_statuses = {429, 500, 502, 503, 504}

        for attempt in range(3):
            try:
                response = requests.get(
                    "https://api.crossref.org/works",
                    params=params,
                    headers=headers,
                    timeout=(10, 30),
                )
                if response.status_code in retry_statuses:
                    retry_after = response.headers.get("Retry-After", "")
                    delay = float(retry_after) if retry_after.isdigit() else 2**attempt
                    if attempt < 2:
                        time.sleep(min(delay, 10.0))
                        continue
                response.raise_for_status()
                candidate = response.json()
                if not isinstance(candidate, dict):
                    raise ValueError("Crossref returned a non-object JSON payload.")
                if not parse_crossref_payload(candidate):
                    raise ValueError("Crossref returned no usable paper records.")
                payload = candidate
                ensure_parent(snapshot_path)
                snapshot_path.write_bytes(response.content)
                break
            except (requests.RequestException, ValueError) as exc:
                last_error = exc
                if attempt < 2:
                    time.sleep(2**attempt)

        if payload is None and snapshot_path.exists():
            payload = read_json(snapshot_path)

    if payload is None:
        raise RuntimeError("Crossref fetch failed and no offline snapshot is available.") from last_error

    records = parse_crossref_payload(payload)
    if not records:
        raise ValueError("Crossref payload did not contain any usable paper records.")
    write_json(settings.paths.raw_records_json, [asdict(record) for record in records])
    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    """Load a preserved record snapshot and validate its basic schema."""
    payload = read_json(path)
    if not isinstance(payload, list):
        raise ValueError(f"Invalid raw record snapshot at {path}: expected a list.")

    records: list[PaperRecord] = []
    for index, item in enumerate(payload):
        if not isinstance(item, dict):
            raise ValueError(f"Invalid raw record at index {index}: expected an object.")
        try:
            record = PaperRecord(
                paper_id=str(item["paper_id"]),
                title=str(item["title"]),
                summary=str(item["summary"]),
                authors=[str(value) for value in item.get("authors", [])],
                categories=[str(value) for value in item.get("categories", [])],
                primary_category=str(item.get("primary_category", "Uncategorized")),
                published=str(item["published"]),
                updated=str(item.get("updated", item["published"])),
                abs_url=str(item.get("abs_url", "")),
                pdf_url=str(item.get("pdf_url", "")),
                comment=str(item.get("comment", "")),
            )
        except KeyError as exc:
            raise ValueError(f"Raw record at index {index} is missing {exc.args[0]!r}.") from exc
        records.append(record)
    return records
