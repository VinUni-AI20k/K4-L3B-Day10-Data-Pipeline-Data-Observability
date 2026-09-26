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
from core.utils import normalize_whitespace, read_json, write_json


CROSSREF_WORKS_URL = "https://api.crossref.org/works"
_RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
_MAX_ATTEMPTS = 4


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
    """Parse a Crossref ``/works`` response into normalized paper records.

    Records without a DOI, title, abstract, or publication date are skipped. A
    malformed top-level payload is treated as an empty response so that callers
    can safely process API snapshots as well as live responses.
    """
    message = payload.get("message") if isinstance(payload, dict) else None
    items = message.get("items") if isinstance(message, dict) else None
    if not isinstance(items, list):
        return []

    records: list[PaperRecord] = []
    seen_dois: set[str] = set()

    for item in items:
        if not isinstance(item, dict):
            continue

        doi = _normalize_text(item.get("DOI"))
        title = _first_text(item.get("title"))
        summary = _normalize_text(item.get("abstract"))
        published = _crossref_date(
            item.get("published"),
            item.get("published-print"),
            item.get("published-online"),
            item.get("issued"),
        )

        # These fields form the minimum useful document for the downstream RAG
        # pipeline. Crossref can occasionally return incomplete metadata even
        # when filters such as ``has-abstract:true`` are used.
        if not doi or not title or not summary or not published:
            continue

        doi_key = doi.casefold()
        if doi_key in seen_dois:
            continue
        seen_dois.add(doi_key)

        authors = _parse_authors(item.get("author"))
        categories = _string_list(item.get("subject"))
        updated = _crossref_date(
            item.get("indexed"), item.get("deposited"), item.get("created")
        ) or published
        abs_url = _normalize_text(item.get("URL")) or f"https://doi.org/{doi}"
        pdf_url = _find_pdf_url(item) or abs_url

        records.append(
            PaperRecord(
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
            )
        )

    return records


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """Fetch Crossref metadata, persist raw artifacts, and return records.

    Transient failures are retried with exponential backoff. If the live API is
    unavailable, the existing raw API snapshot is used as an offline fallback.
    """
    params = {
        "query": settings.source_query,
        "filter": settings.source_filter,
        "rows": settings.max_results,
    }
    headers = {
        "Accept": "application/json",
        "User-Agent": "data-observability-lab/1.0 (Crossref metadata ingestion)",
    }

    payload: dict[str, Any] | None = None
    request_error: Exception | None = None

    for attempt in range(_MAX_ATTEMPTS):
        response: requests.Response | None = None
        try:
            response = requests.get(
                CROSSREF_WORKS_URL,
                params=params,
                headers=headers,
                timeout=30,
            )
            response.raise_for_status()
            candidate = response.json()
            if not isinstance(candidate, dict):
                raise ValueError("Crossref response must be a JSON object.")

            payload = candidate
            write_json(settings.paths.raw_api_response, payload)
            break
        except (requests.RequestException, ValueError) as exc:
            request_error = exc
            status_code = response.status_code if response is not None else None
            should_retry = (
                status_code is None or status_code in _RETRYABLE_STATUS_CODES
            )
            if not should_retry or attempt == _MAX_ATTEMPTS - 1:
                break
            time.sleep(_retry_delay(response, attempt))

    if payload is None:
        snapshot_path = settings.paths.raw_api_response
        if not snapshot_path.exists():
            raise RuntimeError(
                "Could not fetch Crossref metadata and no local API snapshot is available."
            ) from request_error

        candidate = read_json(snapshot_path)
        if not isinstance(candidate, dict):
            raise ValueError(
                f"Invalid Crossref snapshot at {snapshot_path}: expected an object."
            )
        payload = candidate

    records = parse_crossref_payload(payload)
    write_json(settings.paths.raw_records_json, [asdict(record) for record in records])
    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    """Load a normalized JSON snapshot and map it to ``PaperRecord`` objects."""
    payload = read_json(path)
    if not isinstance(payload, list):
        raise ValueError(f"Invalid records snapshot at {path}: expected a JSON array.")

    records: list[PaperRecord] = []
    for index, item in enumerate(payload):
        if not isinstance(item, dict):
            raise ValueError(f"Invalid record at index {index}: expected an object.")

        try:
            records.append(
                PaperRecord(
                    paper_id=str(item["paper_id"]),
                    title=str(item["title"]),
                    summary=str(item["summary"]),
                    authors=_string_list(item.get("authors")),
                    categories=_string_list(item.get("categories")),
                    primary_category=str(item.get("primary_category", "")),
                    published=str(item["published"]),
                    updated=str(item.get("updated", item["published"])),
                    abs_url=str(item.get("abs_url", "")),
                    pdf_url=str(item.get("pdf_url", "")),
                    comment=str(item.get("comment", "")),
                )
            )
        except KeyError as exc:
            raise ValueError(
                f"Invalid record at index {index}: missing field {exc.args[0]!r}."
            ) from exc

    return records


def _normalize_text(value: Any) -> str:
    """Return plain, single-spaced text from a Crossref scalar value."""
    if value is None:
        return ""
    if not isinstance(value, str):
        value = str(value)
    without_tags = re.sub(r"<[^>]*>", " ", value)
    return normalize_whitespace(unescape(without_tags))


def _first_text(value: Any) -> str:
    if isinstance(value, list):
        for item in value:
            text = _normalize_text(item)
            if text:
                return text
        return ""
    return _normalize_text(value)


def _string_list(value: Any) -> list[str]:
    values = value if isinstance(value, list) else [value]
    result: list[str] = []
    seen: set[str] = set()
    for item in values:
        text = _normalize_text(item)
        key = text.casefold()
        if text and key not in seen:
            result.append(text)
            seen.add(key)
    return result


def _parse_authors(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []

    authors: list[str] = []
    seen: set[str] = set()
    for author in value:
        if isinstance(author, dict):
            name = normalize_whitespace(
                " ".join(
                    part
                    for part in (
                        _normalize_text(author.get("given")),
                        _normalize_text(author.get("family")),
                    )
                    if part
                )
            )
            name = name or _normalize_text(author.get("name"))
        else:
            name = _normalize_text(author)

        key = name.casefold()
        if name and key not in seen:
            authors.append(name)
            seen.add(key)
    return authors


def _crossref_date(*values: Any) -> str:
    """Extract an ISO date from Crossref date-parts or date-time objects."""
    for value in values:
        if not isinstance(value, dict):
            continue

        date_time = value.get("date-time")
        if isinstance(date_time, str) and date_time:
            match = re.match(r"^(\d{4})-(\d{2})-(\d{2})", date_time)
            if match:
                try:
                    return date(*map(int, match.groups())).isoformat()
                except ValueError:
                    pass

        date_parts = value.get("date-parts")
        if not isinstance(date_parts, list) or not date_parts:
            continue
        parts = date_parts[0]
        if not isinstance(parts, list) or not parts:
            continue

        try:
            year = int(parts[0])
            month = int(parts[1]) if len(parts) > 1 else 1
            day = int(parts[2]) if len(parts) > 2 else 1
            return date(year, month, day).isoformat()
        except (TypeError, ValueError):
            continue

    return ""


def _find_pdf_url(item: dict[str, Any]) -> str:
    links = item.get("link")
    if isinstance(links, list):
        for link in links:
            if not isinstance(link, dict):
                continue
            content_type = _normalize_text(link.get("content-type")).casefold()
            if "pdf" in content_type:
                url = _normalize_text(link.get("URL"))
                if url:
                    return url

    resource = item.get("resource")
    if isinstance(resource, dict):
        primary = resource.get("primary")
        if isinstance(primary, dict):
            return _normalize_text(primary.get("URL"))
    return ""


def _retry_delay(response: requests.Response | None, attempt: int) -> float:
    """Use Retry-After when present, otherwise a bounded exponential delay."""
    if response is not None:
        retry_after = response.headers.get("Retry-After")
        if retry_after:
            try:
                return min(max(float(retry_after), 0.0), 30.0)
            except ValueError:
                pass
    return min(0.5 * (2**attempt), 4.0)
