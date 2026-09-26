from __future__ import annotations

from datetime import UTC, datetime
import json
import re

import pandas as pd

from core.utils import compact_join, normalize_whitespace
from ingestion.crossref import PaperRecord


_JATS_TAG_RE = re.compile(r"<[^>]+>")


def compose_text_for_embedding(
    title: str,
    authors_joined: str,
    categories_joined: str,
    published: str,
    summary: str,
) -> str:
    """Five-part embedding text: title, authors, categories, published, summary."""
    return (
        f"Title: {title}\n"
        f"Authors: {authors_joined}\n"
        f"Categories: {categories_joined}\n"
        f"Published: {published}\n"
        f"Summary: {summary}"
    )


def _clean_text(value: object) -> str:
    return normalize_whitespace(_JATS_TAG_RE.sub(" ", str(value or "")))


def _as_list(value: object) -> list[str]:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return []
    if isinstance(value, list):
        items = value
    elif isinstance(value, str):
        text = value.strip()
        if not text:
            return []
        if text.startswith("["):
            try:
                parsed = json.loads(text.replace("'", '"'))
                if isinstance(parsed, list):
                    items = parsed
                else:
                    items = [text]
            except json.JSONDecodeError:
                items = re.split(r"\s*,\s*", text)
        else:
            items = re.split(r"\s*,\s*", text)
    else:
        items = [value]
    return [_clean_text(item) for item in items if _clean_text(item)]


def _parse_published(value: object) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    text = text.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        try:
            parsed = datetime.strptime(text[:10], "%Y-%m-%d")
        except ValueError:
            return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _age_days(published: object, run_date: datetime) -> int:
    published_dt = _parse_published(published)
    if published_dt is None:
        return 0
    run_aware = run_date if run_date.tzinfo else run_date.replace(tzinfo=UTC)
    return (run_aware.astimezone(UTC) - published_dt).days


def rebuild_embedding_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Recompute helper columns after cleaning or corruption."""
    out = df.copy()
    out["title"] = out["title"].map(_clean_text)
    out["summary"] = out["summary"].fillna("").map(_clean_text)
    if "authors_joined" not in out.columns:
        out["authors_joined"] = out.get("authors", pd.Series([[]] * len(out))).map(
            lambda value: compact_join(_as_list(value))
        )
    if "categories_joined" not in out.columns:
        out["categories_joined"] = out.get("categories", pd.Series([[]] * len(out))).map(
            lambda value: compact_join(_as_list(value))
        )
    out["authors_joined"] = out["authors_joined"].fillna("").map(_clean_text)
    out["categories_joined"] = out["categories_joined"].fillna("").map(_clean_text)
    out["published"] = out["published"].fillna("").astype(str).str.slice(0, 10)
    out["summary_chars"] = out["summary"].str.len().astype(int)
    out["text_for_embedding"] = out.apply(
        lambda row: compose_text_for_embedding(
            title=str(row["title"]),
            authors_joined=str(row["authors_joined"]),
            categories_joined=str(row["categories_joined"]),
            published=str(row["published"]),
            summary=str(row["summary"]),
        ),
        axis=1,
    )
    return out


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    """Normalize raw records into a deduplicated dataframe ready for embedding."""
    rows: list[dict] = []
    for record in records:
        title = _clean_text(record.title)
        paper_id = normalize_whitespace(record.paper_id)
        if not paper_id or not title:
            continue
        authors = _as_list(record.authors)
        categories = _as_list(record.categories) or [_clean_text(record.primary_category) or "Uncategorized"]
        authors_joined = compact_join(authors)
        categories_joined = compact_join(categories)
        published = (record.published or "")[:10]
        summary = _clean_text(record.summary)
        rows.append(
            {
                "paper_id": paper_id,
                "title": title,
                "summary": summary,
                "authors": authors,
                "categories": categories,
                "primary_category": _clean_text(record.primary_category) or (categories[0] if categories else "Uncategorized"),
                "published": published,
                "updated": (record.updated or published)[:10],
                "abs_url": record.abs_url or f"https://doi.org/{paper_id}",
                "pdf_url": record.pdf_url or record.abs_url or f"https://doi.org/{paper_id}",
                "comment": record.comment or f"Crossref record {paper_id}",
                "authors_joined": authors_joined,
                "categories_joined": categories_joined,
                "summary_chars": len(summary),
                "age_days": _age_days(published, run_date),
                "text_for_embedding": compose_text_for_embedding(
                    title=title,
                    authors_joined=authors_joined,
                    categories_joined=categories_joined,
                    published=published,
                    summary=summary,
                ),
            }
        )

    df = pd.DataFrame(rows)
    if df.empty:
        return df

    df = df.sort_values(["published", "paper_id"], ascending=[False, True])
    df = df.drop_duplicates(subset=["paper_id"], keep="first")
    df = df[df["title"].str.len() > 0].copy()
    df = df.sort_values(["published", "paper_id"], ascending=[False, True]).reset_index(drop=True)
    df["age_days"] = df["age_days"].astype(int)
    df["summary_chars"] = df["summary_chars"].astype(int)
    return df
