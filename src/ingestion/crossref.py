from __future__ import annotations

from dataclasses import asdict, dataclass, fields
from datetime import date
from html import unescape
import json
from pathlib import Path
import re
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from core.config import Settings
from core.utils import normalize_whitespace, read_json, write_json


CROSSREF_WORKS_URL = "https://api.crossref.org/works"
_HTML_TAG_RE = re.compile(r"<[^>]+>")


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
    """Parse a Crossref ``/works`` payload into validated paper records."""
    message = payload.get("message", {}) if isinstance(payload, dict) else {}
    items = message.get("items", []) if isinstance(message, dict) else []
    if not isinstance(items, list):
        return []

    records: list[PaperRecord] = []
    seen_ids: set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            continue

        paper_id = _clean_text(item.get("DOI"))
        title = _first_text(item.get("title"))
        summary = _clean_text(item.get("abstract"), strip_markup=True)
        if not paper_id or not title or not summary or paper_id in seen_ids:
            continue

        authors = _parse_authors(item.get("author"))
        categories = _clean_string_list(item.get("subject"))
        published = _extract_date(item, "published", "published-print", "published-online", "created")
        updated = _extract_date(item, "indexed", "deposited", "created") or published
        abs_url = _clean_text(item.get("URL")) or f"https://doi.org/{paper_id}"
        pdf_url = _find_pdf_url(item) or abs_url

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
                abs_url=abs_url,
                pdf_url=pdf_url,
                comment=f"Crossref record {paper_id}",
            )
        )
        seen_ids.add(paper_id)
    return records


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """Fetch Crossref records and fall back to the bundled response snapshot."""
    params = {
        "query": settings.source_query,
        "filter": settings.source_filter,
        "rows": settings.max_results,
        "select": "DOI,title,abstract,author,subject,published,published-print,"
        "published-online,created,indexed,deposited,URL,link",
    }
    payload: dict[str, Any]
    try:
        retry = Retry(
            total=4,
            backoff_factor=1.0,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=frozenset({"GET"}),
            respect_retry_after_header=True,
        )
        session = requests.Session()
        session.headers.update(
            {
                "Accept": "application/json",
                "User-Agent": "day10-data-observability-lab/0.1 (mailto:student@example.com)",
            }
        )
        session.mount("https://", HTTPAdapter(max_retries=retry))
        response = session.get(CROSSREF_WORKS_URL, params=params, timeout=(5, 30))
        response.raise_for_status()
        payload = response.json()
        if not parse_crossref_payload(payload):
            raise ValueError("Crossref returned no valid records.")
        write_json(settings.paths.raw_api_response, payload)
    except (requests.RequestException, ValueError, json.JSONDecodeError):
        if not settings.paths.raw_api_response.exists():
            raise RuntimeError("Crossref request failed and no local snapshot is available.")
        payload = read_json(settings.paths.raw_api_response)

    records = parse_crossref_payload(payload)[: settings.max_results]
    if not records:
        raise ValueError("No valid Crossref records were found in the API response or snapshot.")
    write_json(settings.paths.raw_records_json, [asdict(record) for record in records])
    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    """Load normalized records, or derive them from a nearby API snapshot."""
    if path.exists():
        payload = read_json(path)
        if isinstance(payload, dict) and "message" in payload:
            return parse_crossref_payload(payload)
        if not isinstance(payload, list):
            raise ValueError(f"Expected a JSON list in {path}.")

        field_names = {field.name for field in fields(PaperRecord)}
        records: list[PaperRecord] = []
        for index, item in enumerate(payload):
            if not isinstance(item, dict):
                continue
            missing = field_names - item.keys()
            if missing:
                raise ValueError(f"Record {index} in {path} is missing: {sorted(missing)}")
            values = {name: item[name] for name in field_names}
            values["authors"] = _clean_string_list(values["authors"])
            values["categories"] = _clean_string_list(values["categories"])
            records.append(PaperRecord(**values))
        return records

    response_path = path.with_name("crossref_response.json")
    if response_path.exists():
        return parse_crossref_payload(read_json(response_path))
    raise FileNotFoundError(f"Neither {path} nor fallback snapshot {response_path} exists.")


def _clean_text(value: Any, *, strip_markup: bool = False) -> str:
    if value is None:
        return ""
    text = str(value)
    if strip_markup:
        text = _HTML_TAG_RE.sub(" ", text)
    return normalize_whitespace(unescape(text))


def _first_text(value: Any) -> str:
    if isinstance(value, list):
        return next((_clean_text(item) for item in value if _clean_text(item)), "")
    return _clean_text(value)


def _clean_string_list(value: Any) -> list[str]:
    if not isinstance(value, (list, tuple)):
        return []
    return [text for item in value if (text := _clean_text(item))]


def _parse_authors(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    authors: list[str] = []
    for author in value:
        if not isinstance(author, dict):
            continue
        name = normalize_whitespace(
            " ".join(part for part in (_clean_text(author.get("given")), _clean_text(author.get("family"))) if part)
        )
        if name:
            authors.append(name)
    return authors


def _extract_date(item: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = item.get(key)
        if not isinstance(value, dict):
            continue
        date_parts = value.get("date-parts")
        if isinstance(date_parts, list) and date_parts and isinstance(date_parts[0], list):
            parts = date_parts[0]
            try:
                year = int(parts[0])
                month = int(parts[1]) if len(parts) > 1 else 1
                day = int(parts[2]) if len(parts) > 2 else 1
                return date(year, month, day).isoformat()
            except (IndexError, TypeError, ValueError):
                pass
        date_time = value.get("date-time")
        if isinstance(date_time, str) and date_time:
            return date_time[:10]
    return ""


def _find_pdf_url(item: dict[str, Any]) -> str:
    links = item.get("link")
    if not isinstance(links, list):
        return ""
    for link in links:
        if not isinstance(link, dict):
            continue
        content_type = _clean_text(link.get("content-type")).lower()
        if content_type == "application/pdf":
            return _clean_text(link.get("URL"))
    return ""
