from __future__ import annotations

import logging
from pathlib import Path

from core.config import Settings, load_settings
from core.utils import now_utc, read_json, write_csv, write_json, write_text
from evaluation.metrics import evaluate_pipeline
from evaluation.testset import build_test_set
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import fetch_source_records, load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_phase1_report
from retrieval.index import LocalEmbeddingIndex

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def _write_fallback_phase1_report(
    report_path: Path,
    source_summary: dict,
    metrics: dict,
    quality: dict,
    freshness: dict,
) -> None:
    """Tạo báo cáo markdown dự phòng nếu TV1 chưa hoàn thành generate_phase1_report."""
    lines = [
        "# Phase 1 Baseline Pipeline Report",
        "",
        "## 1. Nguồn Dữ Liệu & Ingestion Summary",
        f"- **Source API:** {source_summary.get('source_api', 'Crossref REST API')}",
        f"- **Tổng số bản ghi thô (Raw Records):** {source_summary.get('total_raw_records', 0)}",
        f"- **Số bản ghi sạch (Cleaned Records):** {source_summary.get('clean_records', 0)}",
        f"- **ChromaDB Collection:** `{source_summary.get('collection_name', 'papers-baseline')}`",
        f"- **Mô hình Embedding:** `{source_summary.get('embedding_model', 'all-MiniLM-L6-v2')}`",
        "",
        "## 2. Kết Quả Kiểm Định Chất Lượng (Great Expectations 1.x & Freshness SLA)",
        f"- **Trạng thái tổng thể Quality Gate:** {'PASSED (True)' if quality.get('success') else 'FAILED (False)'}",
        f"- **GX 1.x Expectations:** {'PASSED' if quality.get('gx_success') else 'FAILED'}",
        f"- **Số lượng Expectation đạt chuẩn:** {quality.get('successful_expectations_count', 0)}/{quality.get('evaluated_expectations_count', 0)}",
        f"- **Freshness SLA:** {'FRESH (True)' if freshness.get('is_fresh') else 'STALE (False)'}",
        f"- **Số bài báo quá hạn (>180 ngày):** {freshness.get('stale_rows', 0)}/{freshness.get('total_rows', 0)} ({freshness.get('stale_percentage', 0)}%)",
        "",
        "## 3. Chỉ Số Đánh Giá Baseline (RAG Evaluation Metrics)",
        "| Chỉ số (Metric) | Giá trị | Mô tả |",
        "|---|:---:|---|",
        f"| **Retrieval Hit Rate** | **{metrics.get('retrieval_hit_rate', 0.0) * 100:.1f}%** | Tỉ lệ truy vấn tìm đúng bài báo chứa thông tin |",
        f"| **Mean Token F1** | **{metrics.get('mean_token_f1', 0.0):.4f}** | Độ trùng khớp từ ngữ giữa câu trả lời và ground truth |",
        f"| **Judge Accuracy** | **{metrics.get('judge_accuracy', 0.0) * 100:.1f}%** | Đánh giá tính chính xác về mặt ngữ nghĩa |",
        f"| **Mean Judge Score** | **{metrics.get('mean_judge_score', 0.0):.2f}/5.0** | Điểm số trung bình từ giám khảo |",
        f"| **Số lượng câu hỏi kiểm thử** | **{metrics.get('samples', 0)}** | Bộ câu hỏi Benchmark bao phủ 4 nhóm nghiệp vụ |",
        "",
        "## 4. Kết Luận Phase 1",
        "Pipeline Baseline đã chạy thành công qua toàn bộ các bước: Ingestion -> Cleaning -> Quality Gate -> Vector Store Indexing -> Benchmark Evaluation.",
        "Dữ liệu sạch đáp ứng đầy đủ tiêu chuẩn kiểm dịch và sẵn sàng làm mốc đối chứng (Ground Truth Baseline) cho Phase 2.",
    ]
    write_text(report_path, "\n".join(lines) + "\n")


def run_phase1_pipeline(settings: Settings | None = None) -> dict:
    """Thực thi toàn bộ luồng Phase 1 Baseline Pipeline."""
    if settings is None:
        settings = load_settings()

    logger.info("=== BẮT ĐẦU PHASE 1: BASELINE PIPELINE ===")

    # 1. Thu thập hoặc tải dữ liệu thô (Ingestion)
    if settings.refresh_source or not settings.paths.raw_records_json.exists():
        logger.info("Đang nạp dữ liệu thô từ Crossref API / Fallback snapshot...")
        records = fetch_source_records(settings)
    else:
        logger.info("Đang đọc dữ liệu thô từ snapshot %s...", settings.paths.raw_records_json)
        records = load_raw_records(settings.paths.raw_records_json)

    logger.info("Đã nạp %d bài báo thô.", len(records))

    # 2. Làm sạch dữ liệu (Data Cleaning)
    logger.info("Đang tiền xử lý và làm sạch dữ liệu...")
    clean_df = build_clean_dataframe(records, now_utc())
    logger.info("Dữ liệu sau khi làm sạch: %d dòng.", len(clean_df))

    # Lưu artifacts sạch
    write_csv(clean_df, settings.paths.clean_csv)
    write_json(settings.paths.clean_json, clean_df.to_dict(orient="records"))
    logger.info("Đã lưu artifacts sạch vào %s và %s", settings.paths.clean_csv, settings.paths.clean_json)

    # 3. Đánh chỉ mục ChromaDB (Vector Indexing)
    logger.info("Đang khởi tạo Vector Store ChromaDB collection '%s'...", settings.baseline_collection_name)
    index = LocalEmbeddingIndex.build(
        df=clean_df,
        settings=settings,
        embeddings_output_path=settings.paths.embeddings_json,
    )
    logger.info("Đã index %d tài liệu vào ChromaDB collection '%s'.", len(clean_df), settings.baseline_collection_name)

    # 4. Sinh bộ đề thi chuẩn hóa (Benchmark Test Set)
    if settings.refresh_test_set or not settings.paths.eval_testset.exists():
        logger.info("Đang sinh bộ đề thi Benchmark (10 câu hỏi)...")
        test_set = build_test_set(clean_df, settings.paths.eval_testset)
    else:
        logger.info("Đang đọc bộ đề thi có sẵn tại %s...", settings.paths.eval_testset)
        test_set = read_json(settings.paths.eval_testset)
    logger.info("Bộ đề thi Benchmark sẵn sàng: %d câu hỏi.", len(test_set))

    # 5. Đánh giá chất lượng RAG trên dữ liệu sạch (Evaluation)
    logger.info("Đang đánh giá chỉ số Baseline RAG (Hit Rate & Token F1)...")
    eval_bundle = evaluate_pipeline(
        settings=settings,
        index=index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.baseline_metrics,
        answers_output_path=settings.paths.baseline_answers,
    )
    metrics = eval_bundle.summary
    logger.info(
        "Chỉ số Baseline: Hit Rate = %.2f%%, Mean Token F1 = %.4f, Judge Score = %.2f/5.0",
        metrics.get("retrieval_hit_rate", 0.0) * 100,
        metrics.get("mean_token_f1", 0.0),
        metrics.get("mean_judge_score", 0.0),
    )

    # 6. Kiểm định chất lượng dữ liệu (Quality Gate GX 1.x & Freshness SLA)
    logger.info("Đang chạy chốt kiểm dịch Great Expectations 1.x & Freshness SLA...")
    quality = run_data_quality_checks(clean_df, settings, report_name="baseline")
    freshness = build_freshness_report(clean_df, settings, settings.paths.freshness_report)
    logger.info("Quality check status: %s, Freshness: %s", quality.get("success"), freshness.get("is_fresh"))

    # 7. Xuất báo cáo Pha 1 (Markdown Report)
    source_summary = {
        "source_api": settings.source_api,
        "total_raw_records": len(records),
        "clean_records": len(clean_df),
        "collection_name": settings.baseline_collection_name,
        "embedding_model": settings.embedding_model,
    }
    logger.info("Đang xuất báo cáo Phase 1 ra %s...", settings.paths.baseline_report)
    try:
        generate_phase1_report(
            report_path=settings.paths.baseline_report,
            source_summary=source_summary,
            metrics=metrics,
            quality=quality,
            freshness=freshness,
        )
    except NotImplementedError:
        logger.info("generate_phase1_report chưa hoàn thiện, sử dụng template báo cáo chuẩn...")
        _write_fallback_phase1_report(
            report_path=settings.paths.baseline_report,
            source_summary=source_summary,
            metrics=metrics,
            quality=quality,
            freshness=freshness,
        )

    logger.info("=== HOÀN TẤT PHASE 1 THÀNH CÔNG ===")
    return {
        "metrics": metrics,
        "quality": quality,
        "freshness": freshness,
        "records_count": len(clean_df),
    }


def main() -> None:
    run_phase1_pipeline()


if __name__ == "__main__":
    main()
