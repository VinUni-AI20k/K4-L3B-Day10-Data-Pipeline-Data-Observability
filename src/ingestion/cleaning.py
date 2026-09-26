from __future__ import annotations

from dataclasses import asdict, fields
from datetime import date, datetime
from html import unescape
import re

import pandas as pd

from core.utils import normalize_whitespace
from ingestion.crossref import PaperRecord


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    """Normalize raw papers into the schema used for embedding and quality checks."""

    def clean_text(value: str) -> str:
        return normalize_whitespace(re.sub(r"<[^>]*>", " ", unescape(value or "")))

    def parse_date(value: str) -> date | None:
        try:
            return datetime.fromisoformat(value.strip().replace("Z", "+00:00")).date()
        except (AttributeError, ValueError):
            return None

    rows = []
    for record in records:
        row = asdict(record)
        row["paper_id"] = clean_text(row["paper_id"]).lower()
        row["title"] = clean_text(row["title"])
        row["summary"] = clean_text(row["summary"])
        published = parse_date(row["published"])
        if not all((row["paper_id"], row["title"], row["summary"], published)):
            continue

        updated = parse_date(row["updated"]) or published
        row["published"] = published.isoformat()
        row["updated"] = updated.isoformat()
        row["authors"] = [name for author in row["authors"] if (name := clean_text(author))]
        row["categories"] = [category for value in row["categories"] if (category := clean_text(value))]
        row["primary_category"] = clean_text(row["primary_category"]) or (
            row["categories"][0] if row["categories"] else ""
        )
        row["abs_url"] = normalize_whitespace(row["abs_url"] or "")
        row["pdf_url"] = normalize_whitespace(row["pdf_url"] or "")
        row["comment"] = clean_text(row["comment"])
        row["age_days"] = (run_date.date() - published).days
        row["authors_joined"] = ", ".join(row["authors"])
        row["categories_joined"] = ", ".join(row["categories"])
        row["summary_chars"] = len(row["summary"])
        row["text_for_embedding"] = "\n".join((
            f"Title: {row['title']}",
            f"Authors: {row['authors_joined']}",
            f"Published: {row['published']}",
            f"Categories: {row['categories_joined']}",
            f"Summary: {row['summary']}",
        ))
        rows.append(row)

    columns = [field.name for field in fields(PaperRecord)] + [
        "age_days", "authors_joined", "categories_joined", "summary_chars", "text_for_embedding"
    ]
    df = pd.DataFrame(rows, columns=columns)
    return (
        df.drop_duplicates(subset="paper_id", keep="first")
        .sort_values(["published", "paper_id"], ascending=[False, True])
        .reset_index(drop=True)
    )
