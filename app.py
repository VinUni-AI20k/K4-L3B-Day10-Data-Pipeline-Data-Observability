from __future__ import annotations

from datetime import datetime

import pandas as pd
import streamlit as st

from core.config import load_settings
from ui.artifacts import comparison_frame, load_dashboard_data


st.set_page_config(
    page_title="Data Pipeline & Observability Dashboard",
    page_icon=":material/monitoring:",
    layout="wide",
    initial_sidebar_state="expanded",
)


def _status_message(result: dict, label: str) -> None:
    if result.get("status") == "missing":
        st.warning(f"{label}: Chưa chạy bước này.")
    elif result.get("status") == "invalid":
        st.error(f"{label}: Không đọc được artifact. {result.get('error', '')}")


def _artifact_hint(result: dict, command: str = "python script/run_phase1.py") -> None:
    if result.get("status") != "ok":
        st.caption(f"Gợi ý chạy: `{command}`")


def _bool_status(value: object) -> str:
    if value is True:
        return "Đạt"
    if value is False:
        return "Không đạt"
    return "Không có dữ liệu"


def _render_overview(data: dict) -> None:
    clean_df = data["clean_df"]
    quality = data["quality"]
    freshness = data["freshness"]
    steps = data["pipeline_steps"]
    passed_steps = sum(step["status"] == "PASS" for step in steps)
    latest = data["latest_mtime"]
    st.subheader("Tổng quan pipeline")
    with st.container(horizontal=True):
        st.metric("Số bài báo sạch", len(clean_df), border=True)
        st.metric("Pipeline gần nhất", f"{passed_steps}/{len(steps)} bước", border=True)
        st.metric("Quality gate", _bool_status(quality.get("success")), border=True)
        st.metric("Freshness", _bool_status(freshness.get("is_fresh")), border=True)
    if latest:
        stamp = datetime.fromtimestamp(latest).astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
        st.caption(f"Thời điểm artifact mới nhất: {stamp}")
    else:
        st.info("Chưa có artifact để xác định thời điểm chạy.")
    st.divider()
    st.subheader("Bản ghi mẫu")
    if clean_df.empty:
        _status_message(data["artifacts"]["clean_csv"], "Clean records")
        _artifact_hint(data["artifacts"]["clean_csv"])
    else:
        st.dataframe(clean_df.head(8), hide_index=True, width="stretch")


def _render_quality(data: dict) -> None:
    st.subheader("Data quality")
    report = data["artifacts"]["baseline_quality"]
    if report.get("status") != "ok":
        _status_message(report, "Quality report")
        _artifact_hint(report)
        return
    quality = data["quality"]
    st.metric("Quality gate", _bool_status(quality.get("success")), border=True)
    expectations = quality.get("expectations")
    if not isinstance(expectations, dict) or not expectations:
        st.info("Không có dữ liệu expectation trong report thực tế.")
        return
    rows = []
    for name, result in expectations.items():
        result = result if isinstance(result, dict) else {}
        nested_result = result.get("result") if isinstance(result.get("result"), dict) else {}
        details = result.get("details", result.get("observed_value"))
        if details is None:
            details = nested_result.get("observed_value", nested_result.get("unexpected_count", "Không có dữ liệu"))
        rows.append({
            "expectation": name,
            "status": _bool_status(result.get("success")),
            "details": details,
        })
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
    with st.expander("Raw quality report"):
        st.json(quality)


def _render_freshness(data: dict, settings) -> None:
    st.subheader("Freshness monitoring")
    freshness = data["freshness"]
    clean_df = data["clean_df"]
    threshold = settings.freshness_threshold_days
    freshness_artifact = data["artifacts"]["freshness"]
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("SLA age threshold", f"> {threshold} ngày", border=True)
    col2.metric("Stale rows", freshness.get("stale_rows", "Không có dữ liệu"), border=True)
    ratio = freshness.get("stale_ratio")
    col3.metric("Stale ratio", f"{float(ratio):.1%}" if isinstance(ratio, (int, float)) else "Không có dữ liệu", border=True)
    col4.metric("is_fresh", _bool_status(freshness.get("is_fresh")), border=True)
    if freshness_artifact.get("status") != "ok":
        _status_message(freshness_artifact, "Freshness report")
        _artifact_hint(freshness_artifact)
    if "age_days" not in clean_df.columns:
        st.info("Không có cột age_days trong clean records.")
        return
    ages = pd.to_numeric(clean_df["age_days"], errors="coerce").dropna()
    if ages.empty:
        st.info("Không có dữ liệu age_days để vẽ phân bố.")
        return
    chart_df = (
    ages.astype(float)
    .round(0)
    .astype(int)
    .value_counts()
    .sort_index()
    .rename_axis("Tuổi dữ liệu (ngày)")
    .reset_index(name="Số bài báo")
)

st.bar_chart(chart_df, x="Tuổi dữ liệu (ngày)", y="Số bài báo")
    st.caption(f"Kết luận freshness lấy từ report: **{_bool_status(freshness.get('is_fresh'))}**.")


def _render_pipeline_runs(data: dict) -> None:
    st.subheader("Pipeline runs")
    st.caption("PASS chỉ được ghi khi artifact tương ứng tồn tại và đọc được.")
    st.dataframe(pd.DataFrame(data["pipeline_steps"]), hide_index=True, width="stretch")
    for step in data["pipeline_steps"]:
        if step["status"] != "PASS":
            st.caption(f"{step['step']}: Chưa chạy bước này — `{step['command']}`")


def _render_comparison(data: dict) -> None:
    st.subheader("Baseline vs corrupted vs repaired")
    frame = comparison_frame(data)
    if frame.empty:
        st.info("Chưa có artifact corrupted/repaired để so sánh. Không có dữ liệu giả được hiển thị.")
        st.caption("Gợi ý chạy: `python script/run_corruption_flow.py`")
        return
    pivot = frame.pivot(index="metric", columns="state", values="value").reset_index()
    st.dataframe(pivot, hide_index=True, width="stretch")
    st.bar_chart(frame, x="metric", y="value", color="state")
    missing_states = [state for state in ("Corrupted", "Repaired") if state not in frame["state"].unique()]
    if missing_states:
        st.warning(f"Chưa có dữ liệu thực tế cho: {', '.join(missing_states)}.")


def _render_records(data: dict) -> None:
    st.subheader("Clean records explorer")
    frame = data["clean_df"]
    if frame.empty:
        st.info("Chưa có clean records.")
        return
    query = st.text_input("Tìm kiếm paper", placeholder="DOI, title hoặc summary", key="record_search")
    filtered = frame
    if query.strip():
        mask = frame.astype(str).apply(lambda column: column.str.contains(query, case=False, na=False)).any(axis=1)
        filtered = frame.loc[mask]
    st.caption(f"Hiển thị {len(filtered)} / {len(frame)} dòng")
    st.dataframe(filtered, hide_index=True, width="stretch")


settings = load_settings()
st.title("Data Pipeline & Observability Dashboard")
st.caption("K4-L3B Day10 · đọc artifact local, không tự gọi API hoặc chạy pipeline nặng")

with st.sidebar:
    st.header("Điều khiển")
    if st.button("Refresh data", icon=":material/refresh:", type="primary", width="stretch"):
        st.session_state.pop("dashboard_data", None)
        st.rerun()
    st.caption(f"Project root: `{settings.paths.project_dir.name}`")

if "dashboard_data" not in st.session_state:
    with st.spinner("Đang đọc artifact từ ổ đĩa..."):
        st.session_state.dashboard_data = load_dashboard_data(settings)
data = st.session_state.dashboard_data

overview, quality, freshness, runs, comparison = st.tabs([
    "Overview",
    "Data Quality",
    "Freshness",
    "Pipeline Runs",
    "Baseline vs Corrupted vs Repaired",
])
with overview:
    _render_overview(data)
with quality:
    _render_quality(data)
with freshness:
    _render_freshness(data, settings)
with runs:
    _render_pipeline_runs(data)
with comparison:
    _render_comparison(data)

st.divider()
_render_records(data)
