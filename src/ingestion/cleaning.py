from __future__ import annotations

from datetime import UTC, datetime
import re
from pathlib import Path

import pandas as pd

from core.config import Settings, load_settings
from core.utils import compact_join, ensure_parent, normalize_whitespace, write_csv
from ingestion.crossref import PaperRecord, fetch_source_records, load_raw_records


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    """Clean raw records thành dataframe sẵn sàng để embed và đánh giá chất lượng.

    Xử lý:
    1. Chuẩn hóa title, summary (loại bỏ thẻ HTML/XML, khoảng trắng thừa), authors, categories.
    2. Parse published/updated date sang định dạng chuẩn YYYY-MM-DD.
    3. Tính toán tuổi đời dữ liệu: age_days = (run_date - published).days.
    4. Tạo các cột trợ giúp:
       - authors_joined: chuỗi tác giả nối bằng dấu phẩy
       - categories_joined: chuỗi thể loại nối bằng dấu phẩy
       - summary_chars: độ dài tóm tắt theo số ký tự
       - text_for_embedding: ngữ cảnh 5 phần phục vụ tạo vector embedding:
         Title: <Tiêu đề>
         Authors: <Tác giả>
         Published: <Ngày công bố>
         Categories: <Lĩnh vực>
         Summary: <Tóm tắt>
    5. Khử trùng lặp theo paper_id và lọc bỏ bản ghi không hợp lệ.
    6. Sắp xếp dataframe theo published giảm dần và trả về pd.DataFrame.
    """
    run_date_val = run_date.date() if hasattr(run_date, "date") else run_date

    cleaned_rows: list[dict] = []
    seen_paper_ids: set[str] = set()

    for record in records:
        paper_id = normalize_whitespace(str(record.paper_id or ""))
        if not paper_id or paper_id in seen_paper_ids:
            continue

        title = normalize_whitespace(str(record.title or ""))
        if not title:
            continue

        # Loại bỏ các thẻ HTML/XML rác (như <jats:p>) và chuẩn hóa khoảng trắng
        summary_raw = re.sub(r"<[^>]+>", " ", str(record.summary or ""))
        summary = normalize_whitespace(summary_raw)
        if not summary:
            continue

        authors = [normalize_whitespace(str(a)) for a in record.authors if str(a).strip()]
        authors_joined = compact_join(authors, ", ")

        categories = [normalize_whitespace(str(c)) for c in record.categories if str(c).strip()]
        categories_joined = compact_join(categories, ", ")

        primary_category = (
            normalize_whitespace(str(record.primary_category))
            if record.primary_category
            else (categories[0] if categories else "General")
        )

        pub_str = str(record.published or "").strip()[:10]
        try:
            pub_date_val = datetime.strptime(pub_str, "%Y-%m-%d").date()
            published = pub_date_val.isoformat()
        except Exception:
            pub_date_val = run_date_val
            published = pub_date_val.isoformat()

        upd_str = str(record.updated or "").strip()[:10]
        try:
            upd_date_val = datetime.strptime(upd_str, "%Y-%m-%d").date()
            updated = upd_date_val.isoformat()
        except Exception:
            updated = published

        age_days = (run_date_val - pub_date_val).days

        text_for_embedding = (
            f"Title: {title}\n"
            f"Authors: {authors_joined}\n"
            f"Published: {published}\n"
            f"Categories: {categories_joined}\n"
            f"Summary: {summary}"
        )

        seen_paper_ids.add(paper_id)
        cleaned_rows.append(
            {
                "paper_id": paper_id,
                "title": title,
                "summary": summary,
                "authors": authors,
                "categories": categories,
                "primary_category": primary_category,
                "published": published,
                "updated": updated,
                "abs_url": str(record.abs_url or "").strip(),
                "pdf_url": str(record.pdf_url or "").strip(),
                "comment": str(record.comment or "").strip(),
                "age_days": age_days,
                "authors_joined": authors_joined,
                "categories_joined": categories_joined,
                "summary_chars": len(summary),
                "text_for_embedding": text_for_embedding,
            }
        )

    if not cleaned_rows:
        return pd.DataFrame(
            columns=[
                "paper_id",
                "title",
                "summary",
                "authors",
                "categories",
                "primary_category",
                "published",
                "updated",
                "abs_url",
                "pdf_url",
                "comment",
                "age_days",
                "authors_joined",
                "categories_joined",
                "summary_chars",
                "text_for_embedding",
            ]
        )

    df = pd.DataFrame(cleaned_rows)
    df = df.sort_values(by=["published", "paper_id"], ascending=[False, True]).reset_index(drop=True)
    return df


def clean_and_save_data(settings: Settings | None = None) -> pd.DataFrame:
    """Load raw records, clean data, and save to CSV and JSON."""
    if settings is None:
        settings = load_settings()

    if settings.paths.raw_records_json.exists():
        records = load_raw_records(settings.paths.raw_records_json)
    else:
        records = fetch_source_records(settings)

    run_date = datetime.now(UTC)
    df = build_clean_dataframe(records, run_date)

    ensure_parent(settings.paths.clean_csv)
    write_csv(df, settings.paths.clean_csv)

    ensure_parent(settings.paths.clean_json)
    df.to_json(settings.paths.clean_json, orient="records", indent=2, force_ascii=False)

    return df


if __name__ == "__main__":
    current_settings = load_settings()
    cleaned_df = clean_and_save_data(current_settings)
    print(f"Cleaned {len(cleaned_df)} records successfully.")
    print(f"Saved CSV to: {current_settings.paths.clean_csv}")
    print(f"Saved JSON to: {current_settings.paths.clean_json}")


