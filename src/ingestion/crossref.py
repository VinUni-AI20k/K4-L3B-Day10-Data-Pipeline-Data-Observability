from __future__ import annotations

from dataclasses import dataclass
import re
import time
from pathlib import Path

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


_JATS_TAG_RE = re.compile(r"<[^>]+>")


def _clean_abstract(raw_abstract: str | None) -> str:
    if not raw_abstract:
        return ""
    without_tags = _JATS_TAG_RE.sub(" ", raw_abstract)
    return normalize_whitespace(without_tags)


def _date_from_parts(date_container: dict | None) -> str:
    if not date_container:
        return ""
    parts = date_container.get("date-parts", [[]])
    if not parts or not parts[0]:
        return ""
    values = list(parts[0]) + [1, 1]
    year, month, day = values[0], values[1], values[2]
    try:
        return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"
    except (TypeError, ValueError):
        return ""


def parse_crossref_payload(payload: dict) -> list[PaperRecord]:
    """Parse Crossref payload thanh list PaperRecord."""
    items = payload.get("message", {}).get("items", [])
    records: list[PaperRecord] = []

    for item in items:
        doi = item.get("DOI", "").strip()
        titles = item.get("title") or []
        title = normalize_whitespace(titles[0]) if titles else ""
        summary = _clean_abstract(item.get("abstract"))

        if not doi or not title or not summary:
            # Bo record khong hop le: thieu DOI, title hoac abstract.
            continue

        authors = []
        for author in item.get("author", []):
            given = (author.get("given") or "").strip()
            family = (author.get("family") or "").strip()
            full_name = normalize_whitespace(f"{given} {family}")
            if full_name:
                authors.append(full_name)

        categories = [normalize_whitespace(subject) for subject in item.get("subject", []) if subject]
        primary_category = categories[0] if categories else "Uncategorized"

        published = _date_from_parts(item.get("published")) or _date_from_parts(item.get("created"))
        updated = _date_from_parts(item.get("created")) or published

        url = item.get("URL", "").strip() or f"https://doi.org/{doi}"

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
                comment=f"Crossref record {doi}",
            )
        )

    return records


def _record_to_dict(record: PaperRecord) -> dict:
    return {
        "paper_id": record.paper_id,
        "title": record.title,
        "summary": record.summary,
        "authors": record.authors,
        "categories": record.categories,
        "primary_category": record.primary_category,
        "published": record.published,
        "updated": record.updated,
        "abs_url": record.abs_url,
        "pdf_url": record.pdf_url,
        "comment": record.comment,
    }


def _dict_to_record(payload: dict) -> PaperRecord:
    return PaperRecord(
        paper_id=payload["paper_id"],
        title=payload["title"],
        summary=payload["summary"],
        authors=list(payload.get("authors", [])),
        categories=list(payload.get("categories", [])),
        primary_category=payload.get("primary_category", "Uncategorized"),
        published=payload.get("published", ""),
        updated=payload.get("updated", ""),
        abs_url=payload.get("abs_url", ""),
        pdf_url=payload.get("pdf_url", ""),
        comment=payload.get("comment", ""),
    )


def _fetch_from_api(settings: Settings) -> dict:
    params = {
        "query": settings.source_query,
        "filter": settings.source_filter,
        "rows": settings.max_results,
    }
    max_attempts = 3
    last_error = ""
    for attempt in range(max_attempts):
        try:
            response = requests.get(
                "https://api.crossref.org/works",
                params=params,
                timeout=15,
                headers={"User-Agent": "day10-lab-student/1.0 (mailto:student@example.com)"},
            )
            if response.status_code in (429, 503):
                last_error = f"HTTP {response.status_code}"
            else:
                response.raise_for_status()
                return response.json()
        except requests.RequestException as exc:
            last_error = str(exc)
        if attempt < max_attempts - 1:
            # Exponential backoff: 1s, 2s (khong sleep sau lan thu cuoi).
            time.sleep(2 ** attempt)
    raise RuntimeError(f"Failed to fetch from Crossref API after {max_attempts} attempts: {last_error}")


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """Goi source API (co fallback offline), luu raw response, parse thanh records."""
    payload: dict | None = None

    if not settings.refresh_source and settings.paths.raw_api_response.exists():
        payload = read_json(settings.paths.raw_api_response)
    else:
        try:
            payload = _fetch_from_api(settings)
        except Exception:
            if settings.paths.raw_api_response.exists():
                payload = read_json(settings.paths.raw_api_response)
            else:
                raise

    ensure_parent(settings.paths.raw_api_response)
    write_json(settings.paths.raw_api_response, payload)

    records = parse_crossref_payload(payload)
    write_json(settings.paths.raw_records_json, [_record_to_dict(record) for record in records])
    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    """Doc JSON snapshot va map thanh PaperRecord."""
    raw = read_json(path)
    return [_dict_to_record(item) for item in raw]
