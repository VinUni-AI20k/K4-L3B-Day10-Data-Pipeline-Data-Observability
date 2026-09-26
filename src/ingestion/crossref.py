from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import re
import requests

from core.config import Settings
from core.utils import normalize_whitespace, read_json, write_json


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
    """Parse Crossref payload into a list of PaperRecord."""
    items = payload.get("message", {}).get("items", [])
    records: list[PaperRecord] = []
    for item in items:
        paper_id = item.get("DOI", "").strip()
        if not paper_id:
            continue

        raw_titles = item.get("title", [])
        title = raw_titles[0] if isinstance(raw_titles, list) and raw_titles else str(raw_titles)
        title = normalize_whitespace(title)

        raw_abstract = item.get("abstract", "")
        summary = re.sub(r"<[^>]+>", "", raw_abstract)
        summary = normalize_whitespace(summary)

        authors: list[str] = []
        for author in item.get("author", []):
            given = author.get("given", "").strip()
            family = author.get("family", "").strip()
            full_name = normalize_whitespace(f"{given} {family}")
            if full_name:
                authors.append(full_name)

        categories = [normalize_whitespace(cat) for cat in item.get("subject", []) if cat]
        primary_category = categories[0] if categories else ""

        pub_parts = item.get("published", {}).get("date-parts", [[]])[0]
        if len(pub_parts) >= 3:
            published = f"{pub_parts[0]:04d}-{pub_parts[1]:02d}-{pub_parts[2]:02d}"
        elif len(pub_parts) == 2:
            published = f"{pub_parts[0]:04d}-{pub_parts[1]:02d}-01"
        elif len(pub_parts) == 1:
            published = f"{pub_parts[0]:04d}-01-01"
        else:
            published = "1970-01-01"

        updated = item.get("created", {}).get("date-time", "")
        if not updated:
            updated = f"{published}T00:00:00Z"

        abs_url = item.get("URL", f"https://doi.org/{paper_id}")
        pdf_url = ""
        comment = ""

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
    """Fetch records from source API with offline fallback, preserving raw artifacts."""
    payload = None
    if settings.refresh_source:
        try:
            url = "https://api.crossref.org/works"
            params = {
                "query": settings.source_query,
                "filter": settings.source_filter,
                "rows": settings.max_results,
            }
            resp = requests.get(url, params=params, timeout=15)
            if resp.status_code == 200:
                payload = resp.json()
                write_json(settings.paths.raw_api_response, payload)
        except Exception:
            payload = None

    if payload is None:
        if settings.paths.raw_api_response.exists():
            payload = read_json(settings.paths.raw_api_response)
        else:
            raise RuntimeError(f"Raw API response snapshot not found at {settings.paths.raw_api_response}")

    records = parse_crossref_payload(payload)
    serialized = [asdict(rec) for rec in records]
    write_json(settings.paths.raw_records_json, serialized)
    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    """Load JSON snapshot and map to list of PaperRecord."""
    raw_list = read_json(path)
    records: list[PaperRecord] = []
    for item in raw_list:
        records.append(
            PaperRecord(
                paper_id=item["paper_id"],
                title=item["title"],
                summary=item["summary"],
                authors=item["authors"],
                categories=item["categories"],
                primary_category=item["primary_category"],
                published=item["published"],
                updated=item["updated"],
                abs_url=item["abs_url"],
                pdf_url=item["pdf_url"],
                comment=item["comment"],
            )
        )
    return records
