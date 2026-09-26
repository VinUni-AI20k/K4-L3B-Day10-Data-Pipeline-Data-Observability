from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
from html import unescape
import logging
from pathlib import Path
import re

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from core.config import Settings
from core.utils import ensure_parent, normalize_whitespace, read_json, write_json


logger = logging.getLogger(__name__)


def _text(value: object) -> str:
    if not isinstance(value, str):
        return ""
    return normalize_whitespace(unescape(re.sub(r"<[^>]+>", " ", value)))


def _date(value: object) -> str:
    if not isinstance(value, dict):
        return ""
    parts = value.get("date-parts")
    if parts and isinstance(parts, list) and isinstance(parts[0], list):
        fields = parts[0]
        if 1 <= len(fields) <= 3:
            try:
                return date(*(fields + [1] * (3 - len(fields)))).isoformat()
            except (TypeError, ValueError):
                pass
    timestamp = value.get("date-time")
    if isinstance(timestamp, str):
        try:
            return date.fromisoformat(timestamp[:10]).isoformat()
        except ValueError:
            pass
    return ""


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
    """Parse works without mutating the payload; skip works missing DOI/title.

    Optional metadata defaults to empty values. Partial publication dates use
    January/the first day when the source only supplies a year/year and month.
    """
    message = payload.get("message") if isinstance(payload, dict) else None
    if not isinstance(message, dict) or not isinstance(message.get("items"), list):
        raise ValueError("Expected a Crossref payload with message.items as a list.")

    records = []
    for item in message["items"]:
        if not isinstance(item, dict):
            continue
        paper_id = _text(item.get("DOI")).lower()
        titles = item.get("title") or []
        title = _text(titles if isinstance(titles, str) else next(iter(titles), ""))
        if not paper_id or not title:
            continue
        authors = []
        for author in item.get("author") or []:
            if isinstance(author, dict):
                name = _text(author.get("name")) or " ".join(
                    part for part in (_text(author.get("given")), _text(author.get("family"))) if part
                )
                if name:
                    authors.append(name)
        subjects = item.get("subject") or []
        if isinstance(subjects, str):
            subjects = [subjects]
        categories = [text for subject in subjects if (text := _text(subject))]
        published = next((value for key in (
            "published", "published-print", "published-online", "issued", "created"
        ) if (value := _date(item.get(key)))), "")
        updated = _date(item.get("deposited")) or _date(item.get("created")) or published
        abs_url = _text(item.get("URL")) or f"https://doi.org/{paper_id}"
        pdf_url = next((
            _text(link.get("URL")) for link in item.get("link") or []
            if isinstance(link, dict) and link.get("content-type") == "application/pdf"
            and _text(link.get("URL"))
        ), abs_url)
        records.append(PaperRecord(
            paper_id=paper_id, title=title, summary=_text(item.get("abstract")),
            authors=authors, categories=categories,
            primary_category=categories[0] if categories else "",
            published=published, updated=updated, abs_url=abs_url, pdf_url=pdf_url,
            comment=f"Crossref record {paper_id}",
        ))
    return records


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """Fetch Crossref works, preserving response bytes, or reuse an offline snapshot.

    Retry transient failures twice. Never overwrite the snapshot with an error
    response or malformed payload; fail clearly if no usable snapshot exists.
    """
    params = {"query": settings.source_query, "rows": settings.max_results}
    if settings.source_filter:
        params["filter"] = settings.source_filter
    retry = Retry(
        total=2, backoff_factor=0.5,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET"}), respect_retry_after_header=False,
    )
    raw_path = settings.paths.raw_api_response
    try:
        with requests.Session() as session:
            session.mount("https://", HTTPAdapter(max_retries=retry))
            response = session.get(
                "https://api.crossref.org/works", params=params, timeout=(5, 20),
                headers={"User-Agent": "DataObservabilityLab/0.1", "Accept": "application/json"},
            )
            response.raise_for_status()
            records = parse_crossref_payload(response.json())
    except (requests.RequestException, ValueError) as exc:
        if not raw_path.is_file():
            raise RuntimeError(f"Crossref fetch failed and no snapshot exists at {raw_path}") from exc
        logger.warning("Crossref unavailable; using snapshot %s: %s", raw_path, exc)
        records = parse_crossref_payload(read_json(raw_path))
    else:
        ensure_parent(raw_path)
        raw_path.write_bytes(response.content)

    write_json(settings.paths.raw_records_json, [asdict(record) for record in records])
    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    """Read the extracted JSON snapshot without calling the source API."""
    payload = read_json(path)
    if not isinstance(payload, list):
        raise ValueError(f"Expected a list of paper records in {path}")
    return [PaperRecord(**record) for record in payload]
