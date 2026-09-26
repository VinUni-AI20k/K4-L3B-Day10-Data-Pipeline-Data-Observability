from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path

import requests

from core.config import Settings


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
    records = []
    items = payload.get("message", {}).get("items", [])
    for item in items:
        doi = item.get("DOI", "")
        title_list = item.get("title", [])
        title = title_list[0] if title_list else ""
        
        abstract = item.get("abstract", "")
        abstract = abstract.replace("<jats:p>", "").replace("</jats:p>", "").strip()
        
        authors = []
        for a in item.get("author", []):
            given = a.get("given", "")
            family = a.get("family", "")
            authors.append(f"{given} {family}".strip())
            
        categories = item.get("subject", [])
        primary_category = categories[0] if categories else ""
        
        pub = item.get("published", {}).get("date-parts", [[1970, 1, 1]])[0]
        y = pub[0] if len(pub) > 0 else 1970
        m = pub[1] if len(pub) > 1 else 1
        d = pub[2] if len(pub) > 2 else 1
        published = f"{y}-{m:02d}-{d:02d}"
        
        created = item.get("created", {}).get("date-time", published)
        updated = str(created)
        
        url = item.get("URL", "")
        
        if not doi or not title:
            continue
            
        record = PaperRecord(
            paper_id=doi,
            title=title,
            summary=abstract,
            authors=authors,
            categories=categories,
            primary_category=primary_category,
            published=published,
            updated=updated,
            abs_url=url,
            pdf_url="",
            comment=""
        )
        records.append(record)
    return records


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    if not settings.refresh_source:
        if settings.paths.raw_api_response.exists():
            with open(settings.paths.raw_api_response, "r", encoding="utf-8") as f:
                payload = json.load(f)
            records = parse_crossref_payload(payload)
            records_dicts = [r.__dict__ for r in records]
            settings.paths.raw_records_json.parent.mkdir(parents=True, exist_ok=True)
            with open(settings.paths.raw_records_json, "w", encoding="utf-8") as f:
                json.dump(records_dicts, f, ensure_ascii=False, indent=2)
            return records
        return []
        
    url = "https://api.crossref.org/works"
    params = {
        "query": settings.source_query,
        "filter": settings.source_filter,
        "rows": settings.max_results
    }
    
    max_retries = 3
    payload = None
    for attempt in range(max_retries):
        try:
            response = requests.get(url, params=params, timeout=10)
            if response.status_code in [429, 503]:
                time.sleep(2 ** attempt)
                continue
            response.raise_for_status()
            payload = response.json()
            break
        except Exception as e:
            if attempt == max_retries - 1:
                print(f"API failed: {e}. Falling back to local snapshot.")
                payload = None
            else:
                time.sleep(2 ** attempt)
                
    if payload is None:
        if settings.paths.raw_api_response.exists():
            with open(settings.paths.raw_api_response, "r", encoding="utf-8") as f:
                payload = json.load(f)
        else:
            return []
            
    settings.paths.raw_api_response.parent.mkdir(parents=True, exist_ok=True)
    with open(settings.paths.raw_api_response, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        
    records = parse_crossref_payload(payload)
    
    records_dicts = [r.__dict__ for r in records]
    with open(settings.paths.raw_records_json, "w", encoding="utf-8") as f:
        json.dump(records_dicts, f, ensure_ascii=False, indent=2)
        
    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return [PaperRecord(**item) for item in data]
