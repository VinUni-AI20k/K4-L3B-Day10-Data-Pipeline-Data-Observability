from __future__ import annotations

from datetime import datetime
from html import unescape
import re

import pandas as pd

from ingestion.crossref import PaperRecord


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    """Return normalized, deduplicated records ready for embedding.

    The raw snapshot is retained unchanged; this function only produces the
    serving dataframe used by the rest of the pipeline.
    """

    def clean_text(value: object) -> str:
        """Remove markup and collapse whitespace in a textual field."""
        if value is None:
            return ""
        text = unescape(str(value))
        text = re.sub(r"<[^>]+>", " ", text)
        return re.sub(r"\s+", " ", text).strip()

    def clean_list(values: object) -> list[str]:
        if not isinstance(values, (list, tuple)):
            values = [] if values is None else [values]
        return [item for value in values if (item := clean_text(value))]

    columns = [
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
        "authors_joined",
        "categories_joined",
        "summary_chars",
        "age_days",
        "text_for_embedding",
    ]
    if not records:
        return pd.DataFrame(columns=columns)

    rows: list[dict[str, object]] = []
    for record in records:
        authors = clean_list(record.authors)
        categories = clean_list(record.categories)
        rows.append(
            {
                "paper_id": clean_text(record.paper_id),
                "title": clean_text(record.title),
                "summary": clean_text(record.summary),
                "authors": authors,
                "categories": categories,
                "primary_category": clean_text(record.primary_category),
                "published": clean_text(record.published),
                "updated": clean_text(record.updated),
                "abs_url": clean_text(record.abs_url),
                "pdf_url": clean_text(record.pdf_url),
                "comment": clean_text(record.comment),
            }
        )

    df = pd.DataFrame(rows)
    df["published"] = pd.to_datetime(df["published"], errors="coerce", utc=True)
    df["updated"] = pd.to_datetime(df["updated"], errors="coerce", utc=True)

    # A paper cannot be indexed without its identity, title, summary, or date.
    df = df.dropna(subset=["published"])
    df = df[(df["paper_id"] != "") & (df["title"] != "") & (df["summary"] != "")]
    df = df.drop_duplicates(subset="paper_id", keep="first").copy()

    run_timestamp = pd.Timestamp(run_date)
    if run_timestamp.tzinfo is None:
        run_timestamp = run_timestamp.tz_localize("UTC")
    else:
        run_timestamp = run_timestamp.tz_convert("UTC")

    df["age_days"] = (run_timestamp - df["published"]).dt.days
    df["authors_joined"] = df["authors"].map(lambda values: ", ".join(values))
    df["categories_joined"] = df["categories"].map(lambda values: ", ".join(values))
    df["summary_chars"] = df["summary"].str.len()
    df["published"] = df["published"].dt.strftime("%Y-%m-%d")
    df["updated"] = df["updated"].dt.strftime("%Y-%m-%d").fillna("")
    df["text_for_embedding"] = df.apply(
        lambda row: (
            f"Title: {row['title']}\n"
            f"Authors: {row['authors_joined']}\n"
            f"Published: {row['published']}\n"
            f"Categories: {row['categories_joined']}\n"
            f"Summary: {row['summary']}"
        ),
        axis=1,
    )

    return df.sort_values("paper_id").reset_index(drop=True)[columns]
