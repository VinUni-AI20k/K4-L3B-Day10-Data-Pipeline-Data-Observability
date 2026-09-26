from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import re
from typing import Any

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


def parse_crossref_payload(payload: dict | list) -> list[PaperRecord]:
    """Parse Crossref API payload hoặc snapshot JSON thành danh sách PaperRecord."""
    if isinstance(payload, list):
        items = payload
    elif isinstance(payload, dict):
        if "message" in payload and isinstance(payload["message"], dict):
            items = payload["message"].get("items", [])
        elif "items" in payload:
            items = payload.get("items", [])
        else:
            items = []
    else:
        items = []

    records: list[PaperRecord] = []
    for item in items:
        if not isinstance(item, dict):
            continue

        # 1. DOI / paper_id
        paper_id = str(item.get("DOI") or item.get("paper_id") or "").strip()
        if not paper_id:
            continue

        # 2. Title (loại bỏ thẻ XML/HTML & chuẩn hóa khoảng trắng)
        raw_title = item.get("title", "")
        if isinstance(raw_title, list):
            raw_title = raw_title[0] if raw_title else ""
        title = re.sub(r"<[^>]+>", "", str(raw_title))
        title = normalize_whitespace(title)

        # 3. Summary / Abstract (loại bỏ jats tags)
        raw_summary = (
            item.get("abstract") or item.get("summary") or item.get("description") or ""
        )
        if isinstance(raw_summary, list):
            raw_summary = raw_summary[0] if raw_summary else ""
        summary = re.sub(r"<[^>]+>", "", str(raw_summary))
        summary = normalize_whitespace(summary)

        # 4. Authors
        authors: list[str] = []
        raw_authors = item.get("author") or item.get("authors") or []
        if isinstance(raw_authors, list):
            for a in raw_authors:
                if isinstance(a, dict):
                    given = str(a.get("given", "")).strip()
                    family = str(a.get("family", "")).strip()
                    name = f"{given} {family}".strip() or str(a.get("name", "")).strip()
                    if name:
                        authors.append(name)
                elif isinstance(a, str) and a.strip():
                    authors.append(a.strip())

        # 5. Categories / Subjects
        categories: list[str] = []
        raw_cat = item.get("subject") or item.get("categories") or []
        if isinstance(raw_cat, list):
            categories = [str(c).strip() for c in raw_cat if str(c).strip()]
        elif isinstance(raw_cat, str) and raw_cat.strip():
            categories = [raw_cat.strip()]
        primary_category = str(
            item.get("primary_category") or (categories[0] if categories else "General")
        )

        # 6. Published Date
        pub_str = ""
        published = item.get("published")
        if isinstance(published, str):
            pub_str = published.strip()
        elif isinstance(published, dict):
            date_parts = published.get("date-parts", [])
            if date_parts and isinstance(date_parts[0], list):
                parts = date_parts[0]
                if len(parts) >= 3:
                    pub_str = f"{parts[0]:04d}-{parts[1]:02d}-{parts[2]:02d}"
                elif len(parts) == 2:
                    pub_str = f"{parts[0]:04d}-{parts[1]:02d}-01"
                elif len(parts) == 1:
                    pub_str = f"{parts[0]:04d}-01-01"
        if not pub_str:
            for key in ["published-print", "published-online", "issued"]:
                cand = item.get(key)
                if isinstance(cand, dict):
                    date_parts = cand.get("date-parts", [])
                    if date_parts and isinstance(date_parts[0], list):
                        parts = date_parts[0]
                        if len(parts) >= 3:
                            pub_str = f"{parts[0]:04d}-{parts[1]:02d}-{parts[2]:02d}"
                            break
                        elif len(parts) == 2:
                            pub_str = f"{parts[0]:04d}-{parts[1]:02d}-01"
                            break
                        elif len(parts) == 1:
                            pub_str = f"{parts[0]:04d}-01-01"
                            break
        if not pub_str:
            created = item.get("created", {})
            if isinstance(created, dict) and "date-time" in created:
                pub_str = str(created["date-time"])[:10]
        if not pub_str:
            pub_str = "2026-01-01"

        # 7. Updated Date
        up_str = ""
        updated = item.get("updated")
        if isinstance(updated, str):
            up_str = updated.strip()
        elif isinstance(updated, dict):
            date_parts = updated.get("date-parts", [])
            if date_parts and isinstance(date_parts[0], list):
                parts = date_parts[0]
                if len(parts) >= 3:
                    up_str = f"{parts[0]:04d}-{parts[1]:02d}-{parts[2]:02d}"
                elif len(parts) == 2:
                    up_str = f"{parts[0]:04d}-{parts[1]:02d}-01"
                elif len(parts) == 1:
                    up_str = f"{parts[0]:04d}-01-01"
        if not up_str:
            up_str = pub_str

        # 8. URLs & Comment
        abs_url = str(item.get("URL") or item.get("abs_url") or f"https://doi.org/{paper_id}")
        pdf_url = str(item.get("pdf_url") or abs_url)
        comment = str(item.get("comment") or f"Crossref record {paper_id}")

        records.append(
            PaperRecord(
                paper_id=paper_id,
                title=title,
                summary=summary,
                authors=authors,
                categories=categories,
                primary_category=primary_category,
                published=pub_str,
                updated=up_str,
                abs_url=abs_url,
                pdf_url=pdf_url,
                comment=comment,
            )
        )

    return records


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """Lấy dữ liệu từ Crossref API có fallback snapshot offline và lưu data lineage."""
    payload = None
    if settings.refresh_source:
        try:
            import requests

            url = "https://api.crossref.org/works"
            params = {
                "query": settings.source_query,
                "filter": settings.source_filter,
                "rows": settings.max_results,
            }
            headers = {
                "User-Agent": "DataObservabilityLab/1.0 (mailto:student@vinuni.edu.vn)"
            }
            resp = requests.get(url, params=params, headers=headers, timeout=10)
            if resp.status_code == 200:
                payload = resp.json()
                write_json(settings.paths.raw_api_response, payload)
        except Exception:
            payload = None

    # Cơ chế Fallback sang snapshot offline
    if payload is None:
        if settings.paths.raw_api_response.exists():
            payload = read_json(settings.paths.raw_api_response)
        elif settings.paths.raw_records_json.exists():
            return load_raw_records(settings.paths.raw_records_json)
        else:
            raise FileNotFoundError(
                f"Neither online Crossref API nor local snapshots exist at {settings.paths.raw_api_response}"
            )

    records = parse_crossref_payload(payload)
    if not records and settings.paths.raw_records_json.exists():
        return load_raw_records(settings.paths.raw_records_json)

    # Bảo tồn lineage: lưu ra raw_records_json
    write_json(settings.paths.raw_records_json, [asdict(record) for record in records])
    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    """Đọc snapshot JSON và chuyển đổi thành danh sách PaperRecord."""
    raw = read_json(path)
    if isinstance(raw, list):
        records: list[PaperRecord] = []
        for item in raw:
            if isinstance(item, dict):
                if "paper_id" in item:
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
                elif "DOI" in item:
                    records.extend(parse_crossref_payload({"items": [item]}))
        return records
    elif isinstance(raw, dict):
        return parse_crossref_payload(raw)
    return []
