from __future__ import annotations

from dataclasses import asdict, dataclass, fields
from pathlib import Path
import re
import time

import requests

from core.config import Settings
from core.utils import normalize_whitespace, read_json, write_json


_JATS_TAG_RE = re.compile(r"<[^>]+>")
_CROSSREF_URL = "https://api.crossref.org/works"
_RETRY_STATUSES = {429, 500, 502, 503, 504}


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


def _strip_markup(value: str) -> str:
    return normalize_whitespace(_JATS_TAG_RE.sub(" ", value or ""))


def _as_string_list(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        items = value
    else:
        items = [value]
    cleaned: list[str] = []
    for item in items:
        text = _strip_markup(str(item))
        if text:
            cleaned.append(text)
    return cleaned


def _format_date_parts(value: object) -> str:
    if isinstance(value, str) and value.strip():
        return value.strip()[:10]
    if not isinstance(value, dict):
        return ""
    parts = value.get("date-parts") or value.get("date_parts") or []
    if not parts:
        date_time = value.get("date-time") or value.get("date_time")
        if isinstance(date_time, str) and date_time.strip():
            return date_time.strip()[:10]
        return ""
    first = parts[0] if isinstance(parts[0], list) else parts
    year = int(first[0]) if len(first) >= 1 else 1970
    month = int(first[1]) if len(first) >= 2 else 1
    day = int(first[2]) if len(first) >= 3 else 1
    return f"{year:04d}-{month:02d}-{day:02d}"


def _author_name(author: object) -> str:
    if isinstance(author, str):
        return _strip_markup(author)
    if not isinstance(author, dict):
        return ""
    given = str(author.get("given") or "").strip()
    family = str(author.get("family") or "").strip()
    combined = _strip_markup(f"{given} {family}")
    if combined:
        return combined
    return _strip_markup(str(author.get("name") or author.get("literal") or ""))


def _first_title(item: dict) -> str:
    title = item.get("title")
    if isinstance(title, list) and title:
        return _strip_markup(str(title[0]))
    if isinstance(title, str):
        return _strip_markup(title)
    return ""


def _doi_of(item: dict) -> str:
    doi = item.get("DOI") or item.get("paper_id") or item.get("doi") or ""
    return normalize_whitespace(str(doi))


def _record_from_crossref_item(item: dict) -> PaperRecord | None:
    paper_id = _doi_of(item)
    title = _first_title(item)
    if not paper_id or not title:
        return None

    authors = [_author_name(author) for author in (item.get("author") or [])]
    authors = [author for author in authors if author]
    categories = _as_string_list(item.get("subject") or item.get("categories") or [])
    primary_category = categories[0] if categories else "Uncategorized"
    published = _format_date_parts(item.get("published") or item.get("issued") or item.get("created"))
    updated = _format_date_parts(item.get("created") or item.get("deposited") or item.get("published")) or published
    url = str(item.get("URL") or item.get("abs_url") or f"https://doi.org/{paper_id}")
    summary = _strip_markup(str(item.get("abstract") or item.get("summary") or ""))
    return PaperRecord(
        paper_id=paper_id,
        title=title,
        summary=summary,
        authors=authors,
        categories=categories or [primary_category],
        primary_category=primary_category,
        published=published,
        updated=updated or published,
        abs_url=url,
        pdf_url=str(item.get("pdf_url") or url),
        comment=str(item.get("comment") or f"Crossref record {paper_id}"),
    )


def _record_from_mapping(item: dict) -> PaperRecord | None:
    if "DOI" in item or "message" in item or "author" in item:
        parsed = _record_from_crossref_item(item)
        if parsed:
            return parsed
    allowed = {field.name for field in fields(PaperRecord)}
    payload = {key: item.get(key) for key in allowed}
    paper_id = normalize_whitespace(str(payload.get("paper_id") or ""))
    title = _strip_markup(str(payload.get("title") or ""))
    if not paper_id or not title:
        return None
    authors = _as_string_list(payload.get("authors"))
    categories = _as_string_list(payload.get("categories"))
    primary = _strip_markup(str(payload.get("primary_category") or (categories[0] if categories else "Uncategorized")))
    return PaperRecord(
        paper_id=paper_id,
        title=title,
        summary=_strip_markup(str(payload.get("summary") or "")),
        authors=authors,
        categories=categories or [primary],
        primary_category=primary,
        published=str(payload.get("published") or "")[:10],
        updated=str(payload.get("updated") or payload.get("published") or "")[:10],
        abs_url=str(payload.get("abs_url") or f"https://doi.org/{paper_id}"),
        pdf_url=str(payload.get("pdf_url") or payload.get("abs_url") or f"https://doi.org/{paper_id}"),
        comment=str(payload.get("comment") or f"Crossref record {paper_id}"),
    )


def parse_crossref_payload(payload: dict | list) -> list[PaperRecord]:
    """Parse a Crossref API payload (or a list of items) into PaperRecord rows."""
    if isinstance(payload, list):
        items = payload
    elif isinstance(payload, dict):
        message = payload.get("message")
        if isinstance(message, dict):
            items = message.get("items") or []
        else:
            items = payload.get("items") or []
    else:
        items = []

    records: list[PaperRecord] = []
    seen: set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            continue
        record = _record_from_mapping(item)
        if record is None or record.paper_id in seen:
            continue
        seen.add(record.paper_id)
        records.append(record)
    return records


def _persist_records(settings: Settings, records: list[PaperRecord]) -> None:
    write_json(settings.paths.raw_records_json, [asdict(record) for record in records])


def _load_snapshot_payload(settings: Settings) -> dict | list | None:
    snapshot = settings.paths.raw_api_response
    if snapshot.exists():
        return read_json(snapshot)
    records_path = settings.paths.raw_records_json
    if records_path.exists():
        return read_json(records_path)
    return None


def _fallback_records(settings: Settings) -> list[PaperRecord]:
    payload = _load_snapshot_payload(settings)
    if payload is None:
        raise RuntimeError(
            "Crossref API unavailable and no local snapshot found at "
            f"{settings.paths.raw_api_response} or {settings.paths.raw_records_json}."
        )
    records = parse_crossref_payload(payload) if isinstance(payload, dict) else [
        record
        for item in payload
        if isinstance(item, dict)
        for record in [_record_from_mapping(item)]
        if record is not None
    ]
    if not records and isinstance(payload, list):
        records = parse_crossref_payload({"message": {"items": payload}})
    if not records:
        raise RuntimeError("Local Crossref snapshot did not contain any valid paper records.")
    _persist_records(settings, records)
    return records


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """Fetch Crossref records, falling back to the local snapshot on network/HTTP errors."""
    snapshot_exists = settings.paths.raw_api_response.exists() or settings.paths.raw_records_json.exists()
    if not settings.refresh_source and snapshot_exists:
        return _fallback_records(settings)

    params = {
        "query": settings.source_query,
        "filter": settings.source_filter,
        "rows": settings.max_results,
    }
    headers = {
        "User-Agent": "Day10-DataObservability-Lab/0.1 (mailto:student@local)",
        "Accept": "application/json",
    }

    last_error: Exception | None = None
    for attempt in range(3):
        try:
            response = requests.get(_CROSSREF_URL, params=params, headers=headers, timeout=30)
            if response.status_code in _RETRY_STATUSES:
                last_error = RuntimeError(f"Crossref HTTP {response.status_code}")
                time.sleep(2**attempt)
                continue
            response.raise_for_status()
            payload = response.json()
            records = parse_crossref_payload(payload)
            if len(records) < settings.max_results and snapshot_exists:
                return _fallback_records(settings)
            write_json(settings.paths.raw_api_response, payload)
            _persist_records(settings, records)
            return records
        except Exception as exc:  # noqa: BLE001 - fallback is the recovery path
            last_error = exc
            time.sleep(2**attempt)

    if snapshot_exists:
        return _fallback_records(settings)
    raise RuntimeError(f"Failed to fetch Crossref records: {last_error}")


def load_raw_records(path: Path) -> list[PaperRecord]:
    """Load a JSON snapshot of either raw Crossref payload or parsed records."""
    payload = read_json(path)
    if isinstance(payload, list):
        records = [record for item in payload if isinstance(item, dict) for record in [_record_from_mapping(item)] if record]
        if records:
            return records
        return parse_crossref_payload({"message": {"items": payload}})
    if isinstance(payload, dict):
        return parse_crossref_payload(payload)
    raise ValueError(f"Unsupported raw records payload in {path}")
