from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
import re
import urllib.parse
import urllib.request

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

    for item in items:
        paper_id = str(item.get("DOI", "")).strip()
        if not paper_id:
            continue

        raw_title = item.get("title", [])
        if isinstance(raw_title, list):
            title = str(raw_title[0]).strip() if raw_title else ""
        else:
            title = str(raw_title).strip()
        title = normalize_whitespace(title)

        raw_abstract = str(item.get("abstract", "") or "")
        clean_abstract = re.sub(r"<[^>]+>", " ", raw_abstract)
        summary = normalize_whitespace(clean_abstract)

        authors: list[str] = []
        for author in item.get("author", []):
            given = str(author.get("given", "")).strip()
            family = str(author.get("family", "")).strip()
            full_name = f"{given} {family}".strip() or str(author.get("name", "")).strip()
            if full_name:
                authors.append(full_name)
        if not authors:
            authors = ["Unknown Author"]

        raw_subjects = item.get("subject", [])
        categories = [normalize_whitespace(str(s)) for s in raw_subjects if str(s).strip()]
        if not categories:
            categories = ["General"]
        primary_category = categories[0]

        date_parts = item.get("published", {}).get("date-parts", [[]])[0]
        if isinstance(date_parts, list) and len(date_parts) >= 3:
            published = f"{int(date_parts[0]):04d}-{int(date_parts[1]):02d}-{int(date_parts[2]):02d}"
        elif isinstance(date_parts, list) and len(date_parts) == 2:
            published = f"{int(date_parts[0]):04d}-{int(date_parts[1]):02d}-01"
        elif isinstance(date_parts, list) and len(date_parts) == 1:
            published = f"{int(date_parts[0]):04d}-01-01"
        else:
            published = str(item.get("created", {}).get("date-time", "2026-01-01"))[:10]

        updated_parts = item.get("updated", {}).get("date-parts", [[]])[0]
        if isinstance(updated_parts, list) and len(updated_parts) >= 3:
            updated = f"{int(updated_parts[0]):04d}-{int(updated_parts[1]):02d}-{int(updated_parts[2]):02d}"
        else:
            updated = published

        abs_url = str(item.get("URL", f"https://doi.org/{paper_id}")).strip()

        pdf_url = abs_url
        for link in item.get("link", []):
            if isinstance(link, dict) and "pdf" in str(link.get("content-type", "")).lower():
                pdf_url = str(link.get("URL", abs_url)).strip()
                break

        comment = str(item.get("publisher", "")).strip()

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
    """Goi source API, luu raw response, parse thanh records co offline fallback."""
    raw_response_path = settings.paths.raw_api_response
    raw_records_path = settings.paths.raw_records_json

    payload: dict | None = None

    if settings.refresh_source:
        try:
            query_params = urllib.parse.urlencode(
                {
                    "query": settings.source_query,
                    "filter": settings.source_filter,
                    "rows": settings.max_results,
                }
            )
            api_url = f"https://api.crossref.org/works?{query_params}"
            req = urllib.request.Request(
                api_url,
                headers={"User-Agent": "EnigmaRAGObservability/1.0 (mailto:hungdq1306@gmail.com)"},
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status == 200:
                    raw_data = resp.read().decode("utf-8")
                    payload = json.loads(raw_data)
                    write_json(raw_response_path, payload)
        except Exception:
            payload = None

    if payload is None:
        if raw_response_path.exists():
            payload = read_json(raw_response_path)
        else:
            raise FileNotFoundError(f"Neither API response nor local snapshot exists at {raw_response_path}")

    records = parse_crossref_payload(payload)

    serialized = [asdict(r) for r in records]
    write_json(raw_records_path, serialized)

    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    """Doc JSON snapshot va map thanh `PaperRecord`."""
    data = read_json(path)
    if isinstance(data, dict) and "message" in data:
        return parse_crossref_payload(data)

    if isinstance(data, list):
        records: list[PaperRecord] = []
        for item in data:
            if isinstance(item, dict):
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

    raise ValueError(f"Unrecognized format in {path}")
