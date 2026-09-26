from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import logging
import re
from pathlib import Path

import requests

from core.config import Settings

logger = logging.getLogger(__name__)


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


def _clean_abstract(raw_abstract: str) -> str:
    if not raw_abstract:
        return ""
    # Remove HTML/XML tags such as <jats:p>, </jats:p>, <p>, etc.
    cleaned = re.sub(r"<[^>]+>", "", raw_abstract)
    return cleaned.strip()


def parse_crossref_payload(payload: dict) -> list[PaperRecord]:
    """Parse Crossref API payload into a list of PaperRecord objects."""
    items = payload.get("message", {}).get("items", [])
    if not items and "items" in payload:
        items = payload["items"]

    records: list[PaperRecord] = []
    for item in items:
        # Extract paper_id (DOI)
        paper_id = item.get("DOI", "") or item.get("paper_id", "")
        if not paper_id:
            continue

        # Extract title
        title_val = item.get("title", "")
        if isinstance(title_val, list):
            title = title_val[0] if title_val else ""
        else:
            title = str(title_val)
        title = title.strip()

        # Extract summary / abstract
        raw_abstract = item.get("abstract", "") or item.get("summary", "")
        summary = _clean_abstract(raw_abstract)

        # Extract authors
        authors: list[str] = []
        raw_authors = item.get("author", []) or item.get("authors", [])
        for a in raw_authors:
            if isinstance(a, dict):
                given = a.get("given", "").strip()
                family = a.get("family", "").strip()
                name = f"{given} {family}".strip() if given or family else a.get("name", "").strip()
                if name:
                    authors.append(name)
            elif isinstance(a, str) and a.strip():
                authors.append(a.strip())

        # Extract categories
        categories: list[str] = []
        raw_subjects = item.get("subject", []) or item.get("categories", [])
        for s in raw_subjects:
            if isinstance(s, str) and s.strip():
                categories.append(s.strip())
        primary_category = categories[0] if categories else item.get("primary_category", "")

        # Extract published date
        published = ""
        pub_dict = item.get("published", {})
        if isinstance(pub_dict, dict) and "date-parts" in pub_dict:
            date_parts = pub_dict["date-parts"]
            if date_parts and date_parts[0]:
                parts = date_parts[0]
                y = parts[0] if len(parts) > 0 else 2026
                m = parts[1] if len(parts) > 1 else 1
                d = parts[2] if len(parts) > 2 else 1
                published = f"{y:04d}-{m:02d}-{d:02d}"
        if not published:
            published = item.get("published", "") or "2026-01-01"
            if isinstance(published, dict):
                published = "2026-01-01"

        updated = item.get("created", {}).get("date-time", published) if isinstance(item.get("created"), dict) else published

        abs_url = item.get("URL", "") or item.get("abs_url", f"https://doi.org/{paper_id}")
        pdf_url = item.get("pdf_url", f"{abs_url}.pdf")
        comment = item.get("comment", "")

        record = PaperRecord(
            paper_id=paper_id,
            title=title,
            summary=summary,
            authors=authors,
            categories=categories,
            primary_category=primary_category,
            published=published,
            updated=str(updated),
            abs_url=abs_url,
            pdf_url=pdf_url,
            comment=comment,
        )
        records.append(record)

    return records


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """Fetch source records from Crossref API (or local fallback snapshot), save raw files, return records."""
    raw_api_path = settings.paths.raw_api_response
    raw_records_path = settings.paths.raw_records_json

    raw_api_path.parent.mkdir(parents=True, exist_ok=True)
    raw_records_path.parent.mkdir(parents=True, exist_ok=True)

    payload = None

    if settings.refresh_source or not raw_api_path.exists():
        try:
            url = "https://api.crossref.org/works"
            params = {
                "query": settings.source_query,
                "filter": settings.source_filter,
                "rows": settings.max_results,
            }
            headers = {"User-Agent": "DataObservabilityLab/1.0 (mailto:lab@example.com)"}
            response = requests.get(url, params=params, headers=headers, timeout=10)
            if response.status_code == 200:
                payload = response.json()
                with open(raw_api_path, "w", encoding="utf-8") as f:
                    json.dump(payload, f, ensure_ascii=False, indent=2)
            else:
                logger.warning("Crossref API returned status %s, falling back to local snapshot.", response.status_code)
        except Exception as e:
            logger.warning("Failed to fetch from Crossref API (%s), falling back to local snapshot.", e)

    if payload is None:
        if raw_api_path.exists():
            with open(raw_api_path, "r", encoding="utf-8") as f:
                payload = json.load(f)
        else:
            raise FileNotFoundError(f"Raw API response not found at {raw_api_path} and API request failed.")

    records = parse_crossref_payload(payload)

    # Save records to raw_records_json
    with open(raw_records_path, "w", encoding="utf-8") as f:
        json.dump([asdict(r) for r in records], f, ensure_ascii=False, indent=2)

    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    """Read JSON snapshot and map into a list of PaperRecord objects."""
    if not path.exists():
        raise FileNotFoundError(f"Raw records file not found at {path}")
    with open(path, "r", encoding="utf-8") as f:
        data_list = json.load(f)

    records: list[PaperRecord] = []
    for d in data_list:
        record = PaperRecord(
            paper_id=d.get("paper_id", ""),
            title=d.get("title", ""),
            summary=d.get("summary", ""),
            authors=d.get("authors", []),
            categories=d.get("categories", []),
            primary_category=d.get("primary_category", ""),
            published=d.get("published", ""),
            updated=d.get("updated", ""),
            abs_url=d.get("abs_url", ""),
            pdf_url=d.get("pdf_url", ""),
            comment=d.get("comment", ""),
        )
        records.append(record)
    return records
