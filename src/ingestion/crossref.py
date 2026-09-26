from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

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
    """Parse Crossref payload thanh list PaperRecord."""
    records = []
    items = payload.get("message", {}).get("items", [])
    
    for item in items:
        # Extract fields
        paper_id = item.get("DOI", "")
        title = item.get("title", [""])[0] if item.get("title") else ""
        summary = item.get("abstract", "")
        
        # Lấy danh sách author
        authors = []
        for author in item.get("author", []):
            if "given" in author and "family" in author:
                authors.append(f"{author['given']} {author['family']}")
                
        categories = item.get("subject", [])
        primary_category = categories[0] if categories else ""
        
        # Parse dates (nếu có datetime array hoặc date-time string)
        published = ""
        created_dict = item.get("created", {})
        if "date-time" in created_dict:
            published = created_dict["date-time"]
            
        updated = ""
        deposited_dict = item.get("deposited", {})
        if "date-time" in deposited_dict:
            updated = deposited_dict["date-time"]
            
        abs_url = item.get("URL", "")
        pdf_url = item.get("link", [{"URL": ""}])[0].get("URL", "") if item.get("link") else ""
        
        if paper_id and title:  # Đảm bảo có ID và title
            records.append(PaperRecord(
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
                comment=""
            ))
            
    return records


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """Goi source API, luu raw response, parse thanh records."""
    import requests
    import json
    
    url = "https://api.crossref.org/works"
    params = {
        "query": settings.source_query,
        "filter": settings.source_filter,
        "rows": settings.max_results
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        payload = response.json()
        
        # Lưu raw API response
        out_path_raw = settings.paths.raw_api_response
        out_path_raw.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path_raw, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
            
    except Exception as e:
        print(f"Lỗi gọi API: {e}. Thử fallback đọc từ snapshot...")
        # Fallback đọc từ snapshot local nếu có
        if settings.paths.raw_api_response.exists():
            with open(settings.paths.raw_api_response, "r", encoding="utf-8") as f:
                payload = json.load(f)
        else:
            return []

    # Parse payload
    records = parse_crossref_payload(payload)
    
    # Lưu records JSON
    out_path_records = settings.paths.raw_records_json
    with open(out_path_records, "w", encoding="utf-8") as f:
        json.dump([r.__dict__ for r in records], f, ensure_ascii=False, indent=2)
        
    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    """Doc JSON snapshot va map thanh `PaperRecord`."""
    import json
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    return [PaperRecord(**row) for row in data]
