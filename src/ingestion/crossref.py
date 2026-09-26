from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
import json
import logging
from pathlib import Path
import re
from typing import Any
import urllib.request
import urllib.parse
import urllib.error

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


def _clean_jats_tags(text: str) -> str:
    """Loại bỏ thẻ XML/JATS và chuẩn hóa khoảng trắng thừa."""
    if not text:
        return ""
    cleaned = re.sub(r"<[^>]+>", " ", text)
    return " ".join(cleaned.split())


def _format_date_parts(date_parts: list[Any]) -> str:
    """Chuyển date-parts của Crossref [[yyyy, mm, dd]] thành ISO date string (YYYY-MM-DD)."""
    if not date_parts or not isinstance(date_parts, list) or not date_parts[0]:
        return datetime.now().strftime("%Y-%m-%d")
    
    parts = date_parts[0]
    year = int(parts[0]) if len(parts) > 0 and parts[0] is not None else 2026
    month = int(parts[1]) if len(parts) > 1 and parts[1] is not None else 1
    day = int(parts[2]) if len(parts) > 2 and parts[2] is not None else 1
    
    try:
        return f"{year:04d}-{month:02d}-{day:02d}"
    except Exception:
        return f"{year:04d}-01-01"


def parse_crossref_payload(payload: dict) -> list[PaperRecord]:
    """Parse Crossref response payload thành danh sách PaperRecord."""
    items = payload.get("message", {}).get("items", [])
    records: list[PaperRecord] = []

    for item in items:
        # 1. DOI -> paper_id
        doi = str(item.get("DOI", "")).strip()
        if not doi:
            continue

        # 2. Title
        raw_titles = item.get("title", [])
        if isinstance(raw_titles, list) and raw_titles:
            title = _clean_jats_tags(str(raw_titles[0]))
        else:
            title = _clean_jats_tags(str(raw_titles))
        if not title:
            continue

        # 3. Summary / Abstract
        raw_abstract = item.get("abstract", "")
        summary = _clean_jats_tags(str(raw_abstract))

        # 4. Authors
        authors: list[str] = []
        for author in item.get("author", []):
            if not isinstance(author, dict):
                continue
            given = author.get("given", "").strip()
            family = author.get("family", "").strip()
            name = author.get("name", "").strip()
            if given or family:
                full_name = f"{given} {family}".strip()
                if full_name:
                    authors.append(full_name)
            elif name:
                authors.append(name)
        if not authors:
            authors = ["Unknown Author"]

        # 5. Categories / Subjects
        categories: list[str] = [str(s).strip() for s in item.get("subject", []) if str(s).strip()]
        if not categories:
            categories = ["General Computer Science"]
        primary_category = categories[0]

        # 6. Dates
        pub_date_parts = item.get("published", {}).get("date-parts", [])
        if not pub_date_parts:
            pub_date_parts = item.get("created", {}).get("date-parts", [])
        published = _format_date_parts(pub_date_parts)

        created_dt = item.get("created", {}).get("date-time", "")
        updated = created_dt if created_dt else published

        # 7. URLs
        abs_url = str(item.get("URL", f"https://doi.org/{doi}")).strip()
        pdf_url = ""
        links = item.get("link", [])
        if isinstance(links, list) and links:
            for link in links:
                if isinstance(link, dict) and "pdf" in link.get("content-type", "").lower():
                    pdf_url = link.get("URL", "")
                    break
        if not pdf_url:
            pdf_url = abs_url

        # 8. Comment / Publisher
        comment = str(item.get("publisher", "")).strip()

        record = PaperRecord(
            paper_id=doi,
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
        records.append(record)

    return records


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """Tải dữ liệu từ Crossref API (hoặc fallback đọc snapshot local khi mất mạng/lỗi 429)."""
    payload = None
    raw_api_path = settings.paths.raw_api_response
    raw_records_path = settings.paths.raw_records_json

    # Đảm bảo thư mục raw tồn tại
    raw_api_path.parent.mkdir(parents=True, exist_ok=True)

    if settings.refresh_source:
        try:
            logger.info("Đang gọi Crossref REST API...")
            query_params = {
                "query": settings.source_query,
                "filter": settings.source_filter,
                "rows": settings.max_results,
            }
            url = f"https://api.crossref.org/works?{urllib.parse.urlencode(query_params)}"
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Day10-RAG-Observability-Lab/1.0 (mailto:student@lab.edu)"},
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                if response.status == 200:
                    payload = json.loads(response.read().decode("utf-8"))
                    with open(raw_api_path, "w", encoding="utf-8") as f:
                        json.dump(payload, f, indent=2, ensure_ascii=False)
                    logger.info("Đã lưu Crossref response mới vào %s", raw_api_path)
        except Exception as e:
            logger.warning("Không thể gọi API trực tiếp (%s). Đang chuyển sang dùng snapshot local.", e)

    # Fallback: Đọc từ local snapshot nếu không gọi được API
    if payload is None:
        if raw_api_path.exists():
            logger.info("Đang đọc dữ liệu thô từ local snapshot: %s", raw_api_path)
            with open(raw_api_path, "r", encoding="utf-8") as f:
                payload = json.load(f)
        else:
            raise FileNotFoundError(f"Không tìm thấy file snapshot raw tại {raw_api_path}")

    records = parse_crossref_payload(payload)

    # Lưu danh sách PaperRecord ra file data/raw/crossref_records.json
    with open(raw_records_path, "w", encoding="utf-8") as f:
        json.dump([asdict(r) for r in records], f, indent=2, ensure_ascii=False)
    logger.info("Đã lưu %d records vào %s", len(records), raw_records_path)

    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    """Đọc snapshot JSON và parse thành danh sách PaperRecord."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    records: list[PaperRecord] = []
    for item in data:
        record = PaperRecord(
            paper_id=item["paper_id"],
            title=item["title"],
            summary=item.get("summary", ""),
            authors=item.get("authors", []),
            categories=item.get("categories", []),
            primary_category=item.get("primary_category", ""),
            published=item.get("published", ""),
            updated=item.get("updated", ""),
            abs_url=item.get("abs_url", ""),
            pdf_url=item.get("pdf_url", ""),
            comment=item.get("comment", ""),
        )
        records.append(record)

    return records
