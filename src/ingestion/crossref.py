import json
import logging
import re
from dataclasses import asdict, dataclass
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


def _clean_abstract(abstract: str | None) -> str:
    if not abstract:
        return ""
    # Strip HTML / XML tags such as <jats:p>, </jats:p>, <jats:title>, etc.
    cleaned = re.sub(r"<[^>]+>", " ", abstract)
    return re.sub(r"\s+", " ", cleaned).strip()


def _format_date(date_parts: list) -> str:
    if not date_parts or not isinstance(date_parts, list) or not date_parts[0]:
        return ""
    parts = date_parts[0]
    year = parts[0] if len(parts) > 0 else 2026
    month = parts[1] if len(parts) > 1 else 1
    day = parts[2] if len(parts) > 2 else 1
    return f"{year:04d}-{month:02d}-{day:02d}"


def parse_crossref_payload(payload: dict) -> list[PaperRecord]:
    """Parse Crossref payload thanh list PaperRecord."""
    items = payload.get("message", {}).get("items", [])
    records: list[PaperRecord] = []

    for item in items:
        doi = item.get("DOI", "").strip()
        
        # Title
        raw_title = item.get("title", [])
        if isinstance(raw_title, list):
            title = raw_title[0].strip() if raw_title else ""
        else:
            title = str(raw_title).strip()

        # Summary / Abstract
        summary = _clean_abstract(item.get("abstract"))
        if not summary:
            # Fallback to subtitle or title if abstract missing
            subtitles = item.get("subtitle", [])
            summary = subtitles[0].strip() if subtitles else title

        # Authors
        authors: list[str] = []
        for author in item.get("author", []):
            given = author.get("given", "").strip()
            family = author.get("family", "").strip()
            full_name = f"{given} {family}".strip()
            if not full_name and "name" in author:
                full_name = author["name"].strip()
            if full_name:
                authors.append(full_name)
        if not authors:
            authors = ["Unknown Author"]

        # Categories / Subjects
        categories = item.get("subject", [])
        if not categories:
            categories = ["Computer Science"]
        primary_category = categories[0]

        # Dates
        published_parts = item.get("published", {}).get("date-parts", [])
        if not published_parts:
            published_parts = item.get("created", {}).get("date-parts", [])
        published = _format_date(published_parts)
        if not published:
            published = "2026-01-01"

        created_info = item.get("created", {})
        updated = created_info.get("date-time", published)

        # URLs
        abs_url = item.get("URL", f"https://doi.org/{doi}" if doi else "")
        pdf_url = ""
        for link in item.get("link", []):
            if "pdf" in link.get("content-type", "").lower():
                pdf_url = link.get("URL", "")
                break

        record = PaperRecord(
            paper_id=doi or title,
            title=title,
            summary=summary,
            authors=authors,
            categories=categories,
            primary_category=primary_category,
            published=published,
            updated=updated,
            abs_url=abs_url,
            pdf_url=pdf_url,
            comment="",
        )
        records.append(record)

    return records


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """Goi source API, luu raw response, parse thanh records co co che fallback."""
    raw_response_path = settings.paths.raw_api_response
    raw_records_path = settings.paths.raw_records_json

    # Ensure parent directory exists
    raw_response_path.parent.mkdir(parents=True, exist_ok=True)
    raw_records_path.parent.mkdir(parents=True, exist_ok=True)

    payload = None

    # Check if refresh is requested or try fetching from live API
    url = "https://api.crossref.org/works"
    params = {
        "query": settings.source_query,
        "filter": settings.source_filter,
        "rows": settings.max_results,
    }
    headers = {
        "User-Agent": "AIVin-ObservabilityLab/1.0 (mailto:student@lab.local)"
    }

    try:
        logger.info(f"Connecting to Crossref API: {url}")
        resp = requests.get(url, params=params, headers=headers, timeout=10)
        if resp.status_code == 200:
            payload = resp.json()
            with open(raw_response_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            logger.info("Saved fresh API response to raw snapshot.")
        else:
            logger.warning(f"Crossref API returned status {resp.status_code}. Activating fallback snapshot.")
    except Exception as exc:
        logger.warning(f"Network error accessing Crossref API: {exc}. Activating fallback snapshot.")

    # Fallback to local snapshot if API call failed or returned empty
    if not payload and raw_response_path.exists():
        with open(raw_response_path, "r", encoding="utf-8") as f:
            payload = json.load(f)

    if not payload:
        raise RuntimeError(f"Could not fetch from Crossref API and no fallback snapshot found at {raw_response_path}")

    records = parse_crossref_payload(payload)
    if settings.max_results and len(records) > settings.max_results:
        records = records[: settings.max_results]

    # Save records to raw_records.json
    records_dict = [asdict(r) for r in records]
    with open(raw_records_path, "w", encoding="utf-8") as f:
        json.dump(records_dict, f, ensure_ascii=False, indent=2)

    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    """Doc JSON snapshot va map thanh PaperRecord."""
    if not path.exists():
        raise FileNotFoundError(f"Raw records file not found at {path}")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return [PaperRecord(**item) for item in data]

