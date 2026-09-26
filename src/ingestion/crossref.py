from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
import re
from typing import Any
import requests

from core.config import Settings
from core.utils import ensure_parent, normalize_whitespace


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


def _clean_jats_xml(text: str) -> str:
    cleaned = re.sub(r"<[^>]+>", " ", text)
    return normalize_whitespace(cleaned)


def _extract_date(item: dict[str, Any], key: str = "published") -> str:
    date_parts = item.get(key, {}).get("date-parts", [])
    if date_parts and isinstance(date_parts, list) and len(date_parts) > 0 and len(date_parts[0]) > 0:
        parts = date_parts[0]
        year = parts[0]
        month = parts[1] if len(parts) > 1 else 1
        day = parts[2] if len(parts) > 2 else 1
        return f"{year:04d}-{month:02d}-{day:02d}"
    
    # Fallback to created or deposited
    for fallback_key in ("created", "deposited", "issued"):
        dt = item.get(fallback_key, {}).get("date-time")
        if dt and isinstance(dt, str) and len(dt) >= 10:
            return dt[:10]
    return "2026-01-01"


def parse_crossref_payload(payload: dict) -> list[PaperRecord]:
    """Parse Crossref payload into list of PaperRecord objects."""
    message = payload.get("message", {})
    items = message.get("items", []) if isinstance(message, dict) else []
    records: list[PaperRecord] = []

    for item in items:
        paper_id = item.get("DOI", "").strip()
        if not paper_id:
            continue

        raw_title = item.get("title", [""])
        title = raw_title[0] if isinstance(raw_title, list) and raw_title else str(raw_title)
        title = normalize_whitespace(title)
        if not title:
            continue

        raw_abstract = item.get("abstract", "")
        summary = _clean_jats_xml(raw_abstract)

        authors: list[str] = []
        for author in item.get("author", []):
            given = author.get("given", "").strip()
            family = author.get("family", "").strip()
            name = author.get("name", "").strip()
            if given and family:
                authors.append(f"{given} {family}")
            elif family:
                authors.append(family)
            elif name:
                authors.append(name)

        categories = item.get("subject", [])
        if isinstance(categories, str):
            categories = [categories]
        categories = [normalize_whitespace(c) for c in categories if c]

        primary_category = categories[0] if categories else "General"
        published = _extract_date(item, "published")
        updated = published

        abs_url = item.get("URL", f"https://doi.org/{paper_id}")
        pdf_url = abs_url
        if "link" in item and isinstance(item["link"], list):
            for link in item["link"]:
                if link.get("content-type") == "application/pdf" and link.get("URL"):
                    pdf_url = link["URL"]
                    break

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
    """Fetch records from Crossref API with local snapshot fallback."""
    raw_api_path = settings.paths.raw_api_response
    raw_records_path = settings.paths.raw_records_json

    payload: dict[str, Any] | None = None

    if settings.refresh_source:
        try:
            url = "https://api.crossref.org/works"
            params = {
                "query": settings.source_query,
                "filter": settings.source_filter,
                "rows": settings.max_results,
            }
            headers = {
                "User-Agent": "DataObservabilityLab/1.0 (mailto:student@lab.edu)",
            }
            resp = requests.get(url, params=params, headers=headers, timeout=10)
            if resp.status_code == 200:
                payload = resp.json()
                ensure_parent(raw_api_path)
                raw_api_path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")
        except Exception:
            payload = None

    # Fallback to local snapshot if API fetch was skipped or failed
    if payload is None:
        if raw_api_path.exists():
            payload = json.loads(raw_api_path.read_text(encoding="utf-8"))
        elif raw_records_path.exists():
            return load_raw_records(raw_records_path)
        else:
            raise FileNotFoundError(f"Neither source API nor local snapshot available at {raw_api_path}")

    records = parse_crossref_payload(payload)

    # Save raw records JSON
    ensure_parent(raw_records_path)
    records_payload = [asdict(r) for r in records]
    raw_records_path.write_text(json.dumps(records_payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")

    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    """Load JSON snapshot and map into PaperRecord instances."""
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        return parse_crossref_payload(data)
    elif isinstance(data, list):
        return [
            PaperRecord(
                paper_id=item["paper_id"],
                title=item["title"],
                summary=item.get("summary", ""),
                authors=item.get("authors", []),
                categories=item.get("categories", []),
                primary_category=item.get("primary_category", "General"),
                published=item.get("published", "2026-01-01"),
                updated=item.get("updated", item.get("published", "2026-01-01")),
                abs_url=item.get("abs_url", ""),
                pdf_url=item.get("pdf_url", ""),
                comment=item.get("comment", ""),
            )
            for item in data
        ]
    raise ValueError(f"Unrecognized data format in {path}")
