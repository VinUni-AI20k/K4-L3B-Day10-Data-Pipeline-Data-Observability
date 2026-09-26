import html
import json
import logging
import re
import time
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


def _clean_text(text: str) -> str:
    """Loại bỏ thẻ XML/HTML (như <jats:p>) và khoảng trắng thừa."""
    clean = re.sub(r"<[^>]+>", "", text)
    clean = html.unescape(clean)
    return " ".join(clean.split())


def _extract_date(item: dict) -> str:
    """Bóc tách ngày công bố từ cấu trúc Crossref date-parts."""
    pub_data = item.get("published")
    if isinstance(pub_data, dict):
        date_parts = pub_data.get("date-parts", [[]])
        if date_parts and date_parts[0]:
            parts = date_parts[0]
            if len(parts) >= 3:
                return f"{int(parts[0]):04d}-{int(parts[1]):02d}-{int(parts[2]):02d}"
            if len(parts) == 2:
                return f"{int(parts[0]):04d}-{int(parts[1]):02d}-01"
            if len(parts) == 1:
                return f"{int(parts[0]):04d}-01-01"

    created = item.get("created")
    if isinstance(created, dict):
        date_time = created.get("date-time", "")
        if len(date_time) >= 10:
            return date_time[:10]

    if isinstance(pub_data, str) and len(pub_data) >= 10:
        return pub_data[:10]

    return ""


def parse_crossref_payload(payload: dict) -> list[PaperRecord]:
    """Parse Crossref payload thành danh sách PaperRecord.

    1. Duyệt `payload["message"]["items"]`.
    2. Lấy DOI, title, abstract, authors, subject, dates, URLs.
    3. Chuẩn hóa text (loại bỏ thẻ HTML/XML rác như <jats:p>) và bỏ qua record không hợp lệ.
    4. Trả về list `PaperRecord`.
    """
    items = []
    if isinstance(payload, dict):
        msg = payload.get("message")
        if isinstance(msg, dict):
            items = msg.get("items", [])
        elif "items" in payload:
            items = payload.get("items", [])
    elif isinstance(payload, list):
        items = payload

    records: list[PaperRecord] = []
    for item in items:
        if not isinstance(item, dict):
            continue

        paper_id = str(item.get("DOI") or item.get("paper_id") or item.get("id") or "").strip()
        if not paper_id:
            continue

        raw_title = item.get("title", "")
        if isinstance(raw_title, list):
            raw_title = " ".join([str(t) for t in raw_title if t])
        title = _clean_text(str(raw_title))
        if not title:
            continue

        raw_abstract = item.get("abstract") or item.get("summary") or ""
        if isinstance(raw_abstract, list):
            raw_abstract = " ".join([str(a) for a in raw_abstract if a])
        summary = _clean_text(str(raw_abstract))

        raw_authors = item.get("author") or item.get("authors") or []
        authors: list[str] = []
        for a in raw_authors:
            if isinstance(a, dict):
                given = str(a.get("given") or "").strip()
                family = str(a.get("family") or "").strip()
                name = str(a.get("name") or "").strip()
                if given and family:
                    authors.append(f"{given} {family}")
                elif name:
                    authors.append(name)
                elif family:
                    authors.append(family)
                elif given:
                    authors.append(given)
            elif isinstance(a, str) and a.strip():
                authors.append(a.strip())

        raw_subjects = item.get("subject") or item.get("categories") or []
        if isinstance(raw_subjects, str):
            categories = [raw_subjects.strip()]
        elif isinstance(raw_subjects, list):
            categories = [str(s).strip() for s in raw_subjects if str(s).strip()]
        else:
            categories = []

        primary_category = str(
            item.get("primary_category") or (categories[0] if categories else "General")
        ).strip()

        published = str(item.get("published") if isinstance(item.get("published"), str) else _extract_date(item)).strip()
        updated = str(item.get("updated") or published).strip()

        abs_url = str(item.get("abs_url") or item.get("URL") or f"https://doi.org/{paper_id}").strip()
        pdf_url = str(item.get("pdf_url") or item.get("URL") or abs_url).strip()
        comment = str(item.get("comment") or f"Crossref record {paper_id}").strip()

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
    """Gọi Crossref API, lưu raw response, parse thành records.
    Hỗ trợ cơ chế Fallback đọc snapshot offline khi gặp lỗi mạng hoặc 429/503.
    """
    raw_response_path = settings.paths.raw_api_response
    raw_records_path = settings.paths.raw_records_json

    payload: dict | None = None
    should_call_api = settings.refresh_source or not raw_response_path.exists()

    if should_call_api:
        api_url = "https://api.crossref.org/works"
        params = {
            "query": settings.source_query,
            "filter": settings.source_filter,
            "rows": settings.max_results,
        }
        headers = {
            "User-Agent": "DataPipelineLab/1.0 (mailto:student@vinuni.edu.vn)"
        }

        max_retries = 3
        for attempt in range(max_retries):
            try:
                resp = requests.get(api_url, params=params, headers=headers, timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    if data and data.get("message", {}).get("items"):
                        payload = data
                        break
                elif resp.status_code in {429, 503}:
                    time.sleep(1.0 * (attempt + 1))
            except Exception as e:
                logger.warning("Attempt %d to fetch Crossref failed: %s", attempt + 1, e)
                if attempt < max_retries - 1:
                    time.sleep(1.0)

    # Cơ chế Fallback đọc từ snapshot cục bộ nếu API không lấy được kết quả
    if payload is None:
        if raw_response_path.exists():
            with open(raw_response_path, "r", encoding="utf-8") as f:
                payload = json.load(f)
        else:
            raise RuntimeError(
                f"Không thể tải từ Crossref API và không tìm thấy snapshot tại {raw_response_path}"
            )

    # Lưu bản gốc nguyên trạng (Raw Preservation) phục vụ Data Lineage
    raw_response_path.parent.mkdir(parents=True, exist_ok=True)
    with open(raw_response_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    # Parse payload thành PaperRecord
    records = parse_crossref_payload(payload)

    # Lưu danh sách records đã bóc tách
    raw_records_path.parent.mkdir(parents=True, exist_ok=True)
    records_dict_list = [asdict(r) for r in records]
    with open(raw_records_path, "w", encoding="utf-8") as f:
        json.dump(records_dict_list, f, ensure_ascii=False, indent=2)

    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    """Đọc JSON snapshot và map thành danh sách PaperRecord."""
    if not path.exists():
        return []

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, list):
        records: list[PaperRecord] = []
        for item in data:
            if isinstance(item, dict) and "paper_id" in item:
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

    if isinstance(data, dict):
        return parse_crossref_payload(data)

    return []

