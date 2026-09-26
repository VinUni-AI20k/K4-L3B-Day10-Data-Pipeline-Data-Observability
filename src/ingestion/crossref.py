from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
import re
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


def parse_crossref_payload(payload: dict) -> list[PaperRecord]:
    """Parse Crossref payload thanh list PaperRecord."""
    items = payload.get("message", {}).get("items", [])
    records: list[PaperRecord] = []

    def _format_date(date_info: dict | None) -> str:
        if not date_info or not isinstance(date_info, dict):
            return ""
        parts_list = date_info.get("date-parts", [])
        if parts_list and isinstance(parts_list[0], list) and parts_list[0]:
            parts = parts_list[0]
            if len(parts) == 1:
                return f"{parts[0]:04d}-01-01"
            elif len(parts) == 2:
                return f"{parts[0]:04d}-{parts[1]:02d}-01"
            elif len(parts) >= 3:
                return f"{parts[0]:04d}-{parts[1]:02d}-{parts[2]:02d}"
        return ""

    for item in items:
        paper_id = str(item.get("DOI", "")).strip()
        if not paper_id:
            continue

        title_raw = item.get("title", [""])
        if isinstance(title_raw, list):
            title = title_raw[0] if title_raw else ""
        else:
            title = str(title_raw)
        title = normalize_whitespace(title)

        abstract_raw = item.get("abstract", "")
        summary = re.sub(r"<[^>]+>", "", str(abstract_raw))
        summary = normalize_whitespace(summary)

        authors: list[str] = []
        for author in item.get("author", []):
            if isinstance(author, dict):
                given = author.get("given", "").strip()
                family = author.get("family", "").strip()
                name = f"{given} {family}".strip()
                if name:
                    authors.append(name)
                elif author.get("name"):
                    authors.append(str(author["name"]).strip())
            elif isinstance(author, str) and author.strip():
                authors.append(author.strip())

        categories = [str(cat).strip() for cat in item.get("subject", []) if str(cat).strip()]
        primary_category = categories[0] if categories else "General"

        published = _format_date(item.get("published"))
        if not published:
            published = _format_date(item.get("created"))
        if not published and item.get("created", {}).get("date-time"):
            published = str(item["created"]["date-time"])[:10]

        updated = _format_date(item.get("updated"))
        if not updated:
            updated = published

        url = str(item.get("URL", f"https://doi.org/{paper_id}")).strip()
        abs_url = url
        pdf_url = url
        comment = f"Crossref record {paper_id}"

        records.append(
            PaperRecord(
                paper_id=paper_id,
                title=title,
                summary=summary,
                authors=authors,
                categories=categories,
                primary_category=primary_category,
                published=published,
                updated=updated,
                abs_url=abs_url,
                pdf_url=pdf_url,
                comment=comment,
            )
        )
    return records


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """Goi source API, luu raw response, parse thanh records co fallback offline."""
    payload = None
    if settings.refresh_source:
        try:
            params = {
                "query": settings.source_query,
                "filter": settings.source_filter,
                "rows": settings.max_results,
            }
            headers = {
                "User-Agent": "DataObservabilityLab/1.0 (mailto:student@example.com)"
            }
            response = requests.get(
                "https://api.crossref.org/works",
                params=params,
                headers=headers,
                timeout=15,
            )
            if response.status_code == 200:
                payload = response.json()
                write_json(settings.paths.raw_api_response, payload)
        except Exception:
            payload = None

    if payload is None:
        if settings.paths.raw_api_response.exists():
            payload = read_json(settings.paths.raw_api_response)
        elif settings.paths.raw_records_json.exists():
            return load_raw_records(settings.paths.raw_records_json)
        else:
            raise FileNotFoundError(
                f"Raw response snapshot not found at {settings.paths.raw_api_response}"
            )

    records = parse_crossref_payload(payload)
    write_json(settings.paths.raw_records_json, [asdict(r) for r in records])
    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    """Doc JSON snapshot va map thanh `PaperRecord`."""
    data = read_json(path)
    records: list[PaperRecord] = []
    for item in data:
        records.append(
            PaperRecord(
                paper_id=str(item.get("paper_id", "")),
                title=str(item.get("title", "")),
                summary=str(item.get("summary", "")),
                authors=list(item.get("authors", [])),
                categories=list(item.get("categories", [])),
                primary_category=str(item.get("primary_category", "")),
                published=str(item.get("published", "")),
                updated=str(item.get("updated", "")),
                abs_url=str(item.get("abs_url", "")),
                pdf_url=str(item.get("pdf_url", "")),
                comment=str(item.get("comment", "")),
            )
        )
    return records
