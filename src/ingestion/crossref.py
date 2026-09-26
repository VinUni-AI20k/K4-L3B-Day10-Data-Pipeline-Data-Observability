from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
import re
from typing import Any

import requests

try:
    from core.config import Settings
except ImportError:
    Settings = Any  # type: ignore


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
    """Parse Crossref API payload thành danh sách PaperRecord chuẩn hóa.

    - Duyệt qua danh sách bài báo trong payload['message']['items'].
    - Ánh xạ các trường thông tin sang PaperRecord.
    - Dọn sạch toàn bộ thẻ HTML/XML trong abstract bằng regex.
    - Bỏ qua các bản ghi bị thiếu thông tin quan trọng (DOI hoặc Title).
    """
    items = payload.get("message", {}).get("items", [])
    records: list[PaperRecord] = []

    for item in items:
        # 1. Trích xuất paper_id từ DOI
        doi = item.get("DOI", "")
        if isinstance(doi, str):
            doi = doi.strip()
        else:
            doi = str(doi).strip() if doi else ""

        # 2. Trích xuất title (lấy phần tử đầu tiên của mảng title)
        raw_titles = item.get("title", [])
        title = ""
        if isinstance(raw_titles, list) and raw_titles:
            title = str(raw_titles[0]).strip()
        elif isinstance(raw_titles, str):
            title = raw_titles.strip()

        # Bỏ qua các bản ghi bị thiếu DOI hoặc Title
        if not doi or not title:
            continue

        # 3. Trích xuất và làm sạch abstract (summary) bằng regex loại bỏ thẻ HTML/XML
        raw_abstract = item.get("abstract", "") or ""
        clean_summary = re.sub(r"<[^>]+>", "", raw_abstract).strip()
        clean_summary = re.sub(r"\s+", " ", clean_summary)

        # 4. Ghép nối given và family name từ mảng author
        authors: list[str] = []
        for author in item.get("author", []):
            if isinstance(author, dict):
                given = author.get("given", "").strip()
                family = author.get("family", "").strip()
                full_name = f"{given} {family}".strip()
                if full_name:
                    authors.append(full_name)
            elif isinstance(author, str) and author.strip():
                authors.append(author.strip())

        # 5. Trích xuất categories từ subject
        raw_categories = item.get("subject", [])
        if isinstance(raw_categories, list):
            categories = [str(cat).strip() for cat in raw_categories if cat]
        elif raw_categories:
            categories = [str(raw_categories).strip()]
        else:
            categories = []
        primary_category = categories[0] if categories else ""

        # 6. Trích xuất published date (ưu tiên created.date-time hoặc published.date-parts)
        published = ""
        created_info = item.get("created", {})
        if isinstance(created_info, dict) and "date-time" in created_info:
            published = str(created_info["date-time"])[:10]

        if not published and "published" in item:
            pub_info = item["published"]
            if isinstance(pub_info, dict):
                date_parts = pub_info.get("date-parts", [[]])
                if date_parts and date_parts[0]:
                    parts = date_parts[0]
                    if len(parts) >= 3:
                        published = f"{int(parts[0]):04d}-{int(parts[1]):02d}-{int(parts[2]):02d}"
                    elif len(parts) == 2:
                        published = f"{int(parts[0]):04d}-{int(parts[1]):02d}-01"
                    elif len(parts) == 1:
                        published = f"{int(parts[0]):04d}-01-01"
                elif "date-time" in pub_info:
                    published = str(pub_info["date-time"])[:10]
            elif isinstance(pub_info, str):
                published = pub_info[:10]

        updated = published
        abs_url = item.get("URL", f"https://doi.org/{doi}")
        pdf_url = abs_url
        comment = f"Crossref record {doi}"

        record = PaperRecord(
            paper_id=doi,
            title=title,
            summary=clean_summary,
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
    """Gửi GET request tới Crossref API, lưu raw payload, fallback khi gặp lỗi/429,

    parse payload thành danh sách PaperRecord và lưu raw records JSON.
    """
    # Xác định đường dẫn file lưu trữ raw artifacts
    if hasattr(settings, "paths") and getattr(settings.paths, "raw_api_response", None):
        raw_response_path = Path(settings.paths.raw_api_response)
    else:
        raw_response_path = Path("data/raw/crossref_response.json")

    if hasattr(settings, "paths") and getattr(settings.paths, "raw_records_json", None):
        raw_records_path = Path(settings.paths.raw_records_json)
    else:
        raw_records_path = Path("data/raw/crossref_records.json")

    # Xác định URL endpoint
    endpoint = (
        getattr(settings, "api_url", None)
        or getattr(settings, "url", None)
        or getattr(settings, "source_api_url", None)
        or (
            settings.source_api
            if hasattr(settings, "source_api") and str(settings.source_api).startswith("http")
            else None
        )
        or "https://api.crossref.org/works"
    )

    params: dict[str, Any] = {}
    if hasattr(settings, "source_query") and settings.source_query:
        params["query"] = settings.source_query
    if hasattr(settings, "source_filter") and settings.source_filter:
        params["filter"] = settings.source_filter
    if hasattr(settings, "max_results") and settings.max_results:
        params["rows"] = settings.max_results

    headers = {
        "User-Agent": "DataPipelineObservability/1.0 (mailto:student@example.edu)"
    }

    payload: dict[str, Any] | None = None

    # Gọi API với cơ chế Fallback (Cứu hộ)
    try:
        response = requests.get(endpoint, params=params, headers=headers, timeout=15)
        if response.status_code == 429:
            print(
                f"[CẢNH BÁO] Crossref API bị giới hạn tần suất (HTTP 429). "
                f"Kích hoạt cơ chế Fallback: Đọc snapshot cục bộ tại {raw_response_path}."
            )
            with open(raw_response_path, "r", encoding="utf-8") as f:
                payload = json.load(f)
        else:
            response.raise_for_status()
            payload = response.json()
            # Lưu toàn bộ payload JSON nguyên bản vừa lấy được từ API đè vào raw_response_path
            raw_response_path.parent.mkdir(parents=True, exist_ok=True)
            with open(raw_response_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2, ensure_ascii=False)
    except requests.exceptions.RequestException as exc:
        print(
            f"[CẢNH BÁO] Không thể kết nối Crossref API ({exc}). "
            f"Kích hoạt cơ chế Fallback: Đọc snapshot cục bộ tại {raw_response_path}."
        )
        if raw_response_path.exists():
            with open(raw_response_path, "r", encoding="utf-8") as f:
                payload = json.load(f)
        else:
            raise RuntimeError(
                f"Không thể kết nối API và không tìm thấy file snapshot tại {raw_response_path}."
            ) from exc

    if payload is None:
        raise RuntimeError("Không có dữ liệu payload hợp lệ để xử lý.")

    # Parse payload thành danh sách PaperRecord
    records = parse_crossref_payload(payload)

    # Lưu danh sách records (dạng dict) vào raw_records_path
    raw_records_path.parent.mkdir(parents=True, exist_ok=True)
    records_dict = [asdict(rec) for rec in records]
    with open(raw_records_path, "w", encoding="utf-8") as f:
        json.dump(records_dict, f, indent=2, ensure_ascii=False)

    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    """Đọc JSON snapshot từ đường dẫn đã lưu và map thành danh sách PaperRecord."""
    target_path = Path(path)
    with open(target_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    records: list[PaperRecord] = []
    for item in data:
        records.append(
            PaperRecord(
                paper_id=item.get("paper_id", ""),
                title=item.get("title", ""),
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
        )
    return records
