from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests

from core.config import Settings
from core.utils import write_json


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


# ── helpers ──────────────────────────────────────────────────────────────────

def _safe_str(value: Any, fallback: str = "") -> str:
    if isinstance(value, list):
        return " ".join(str(v) for v in value).strip() or fallback
    return str(value).strip() if value else fallback


def _extract_date(date_parts: list | None) -> str:
    """Convert Crossref date-parts [[YYYY, MM, DD]] → 'YYYY-MM-DD'."""
    if not date_parts:
        return ""
    parts = date_parts[0] if date_parts else []
    year  = parts[0] if len(parts) > 0 else 0
    month = parts[1] if len(parts) > 1 else 1
    day   = parts[2] if len(parts) > 2 else 1
    return f"{year:04d}-{month:02d}-{day:02d}"


def _strip_jats(text: str) -> str:
    """Remove JATS/XML tags from abstract text."""
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _records_to_dicts(records: list[PaperRecord]) -> list[dict]:
    return [
        {
            "paper_id":        r.paper_id,
            "title":           r.title,
            "summary":         r.summary,
            "authors":         r.authors,
            "categories":      r.categories,
            "primary_category": r.primary_category,
            "published":       r.published,
            "updated":         r.updated,
            "abs_url":         r.abs_url,
            "pdf_url":         r.pdf_url,
            "comment":         r.comment,
        }
        for r in records
    ]


# ── public API ────────────────────────────────────────────────────────────────

def parse_crossref_payload(payload: dict) -> list[PaperRecord]:
    """Parse a Crossref REST API response payload into PaperRecord list.

    Expected structure: payload["message"]["items"] → list of work objects.
    Records missing a DOI or title are silently skipped.
    """
    items = payload.get("message", {}).get("items", [])
    records: list[PaperRecord] = []

    for item in items:
        doi = str(item.get("DOI", "")).strip()
        if not doi:
            continue

        # title
        title_raw = item.get("title", [])
        title = _safe_str(title_raw)
        if not title:
            continue

        # abstract / summary
        abstract = _strip_jats(_safe_str(item.get("abstract", "")))

        # authors
        authors: list[str] = []
        for auth in item.get("author", []):
            given  = auth.get("given", "")
            family = auth.get("family", "")
            name   = f"{given} {family}".strip()
            if name:
                authors.append(name)

        # categories / subjects
        categories: list[str] = item.get("subject", [])
        primary_category = categories[0] if categories else ""

        # dates
        published = _extract_date(item.get("published", {}).get("date-parts"))
        if not published:
            published = _extract_date(item.get("created", {}).get("date-parts"))
        updated = _extract_date(item.get("deposited", {}).get("date-parts")) or published

        abs_url = f"https://doi.org/{doi}"

        records.append(
            PaperRecord(
                paper_id=doi,
                title=title,
                summary=abstract,
                authors=authors,
                categories=categories,
                primary_category=primary_category,
                published=published,
                updated=updated,
                abs_url=abs_url,
                pdf_url=abs_url,
                comment=f"Crossref record {doi}",
            )
        )

    return records


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """Fetch from Crossref API, save raw response + parsed records.

    Falls back to local snapshot when REFRESH_SOURCE is False or the API
    is unavailable (rate-limited / network error).
    """
    raw_response_path: Path = settings.paths.raw_api_response
    raw_records_path: Path  = settings.paths.raw_records_json

    # If not refreshing and snapshot exists, skip the network call
    if not settings.refresh_source and raw_records_path.exists():
        print(f"[crossref] Loading records from snapshot: {raw_records_path}")
        return load_raw_records(raw_records_path)

    print("[crossref] Fetching from Crossref API…")
    url = "https://api.crossref.org/works"
    params: dict[str, Any] = {
        "query":  settings.source_query,
        "filter": settings.source_filter,
        "rows":   settings.max_results,
        "mailto": "student@example.com",
    }

    for attempt in range(3):
        try:
            resp = requests.get(url, params=params, timeout=30)
            if resp.status_code == 200:
                payload = resp.json()
                write_json(raw_response_path, payload)
                records = parse_crossref_payload(payload)
                write_json(raw_records_path, _records_to_dicts(records))
                print(f"[crossref] Fetched {len(records)} records from API.")
                return records
            elif resp.status_code in {429, 503}:
                wait = 2 ** attempt * 2
                print(f"[crossref] Rate-limited ({resp.status_code}). Retrying in {wait}s…")
                time.sleep(wait)
            else:
                print(f"[crossref] Unexpected status {resp.status_code}. Falling back to snapshot.")
                break
        except Exception as exc:
            print(f"[crossref] Request error: {exc}. Falling back to snapshot.")
            break

    # Fallback 1 – parsed records snapshot
    if raw_records_path.exists():
        print(f"[crossref] Using local records snapshot: {raw_records_path}")
        return load_raw_records(raw_records_path)

    # Fallback 2 – raw API response
    if raw_response_path.exists():
        print(f"[crossref] Parsing raw API response: {raw_response_path}")
        payload = json.loads(raw_response_path.read_text(encoding="utf-8"))
        records = parse_crossref_payload(payload)
        write_json(raw_records_path, _records_to_dicts(records))
        return records

    raise RuntimeError(
        "No local snapshot found and Crossref API is unavailable. "
        "Provide data/raw/crossref_records.json or data/raw/crossref_response.json."
    )


def load_raw_records(path: Path) -> list[PaperRecord]:
    """Load JSON snapshot and deserialise into PaperRecord list."""
    raw: list[dict] = json.loads(path.read_text(encoding="utf-8"))
    return [
        PaperRecord(
            paper_id=        str(item.get("paper_id", "")),
            title=           str(item.get("title", "")),
            summary=         str(item.get("summary", "")),
            authors=         list(item.get("authors", [])),
            categories=      list(item.get("categories", [])),
            primary_category=str(item.get("primary_category", "")),
            published=       str(item.get("published", "")),
            updated=         str(item.get("updated", "")),
            abs_url=         str(item.get("abs_url", "")),
            pdf_url=         str(item.get("pdf_url", "")),
            comment=         str(item.get("comment", "")),
        )
        for item in raw
    ]
