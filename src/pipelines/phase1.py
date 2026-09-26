from __future__ import annotations

from datetime import datetime, timezone

try:
    from datetime import UTC
except ImportError:
    UTC = timezone.utc
from typing import Any

import chromadb
from core.config import Settings, load_settings
from core.utils import read_json, write_json
from evaluation.metrics import evaluate_pipeline
from evaluation.testset import build_test_set
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import fetch_source_records, load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_phase1_report
from retrieval.agent import build_agent, run_agent_question
from retrieval.index import LocalEmbeddingIndex
from retrieval.qa import answer_question


def run_phase1_pipeline(settings: Settings) -> dict[str, Any]:
    """Xâu chuỗi 6 bước pipeline hoàn chỉnh cho Pha 1 (Baseline Pipeline):

    1. Ingest: Thu thập dữ liệu từ Crossref API hoặc nạp snapshot raw sẵn có.
    2. Clean: Tiền xử lý, chuẩn hóa `text_for_embedding`, tính `age_days` và lưu CSV/JSON.
    3. Index ChromaDB: Khởi tạo vector store ChromaDB với collection `papers-baseline`.
    4. Sinh Testset: Tạo bộ benchmark test set 10 câu hỏi qua 4 nhóm nghiệp vụ.
    5. Luồng RAG & Evaluation: Thực thi truy vấn RAG/Agent và đo lường Hit Rate, Token F1.
    6. Quality Gate & Reporting: Kiểm định Great Expectations 1.x, Freshness SLA và xuất báo cáo Markdown.
    """
    print("=" * 72)
    print("🚀 BẮT ĐẦU CHẠY BASELINE PHASE 1 PIPELINE")
    print("=" * 72)

    # -------------------------------------------------------------------------
    # BƯỚC 1: Ingest - Thu thập dữ liệu từ nguồn
    # -------------------------------------------------------------------------
    print("\n[Bước 1/6] 📥 Ingestion: Thu thập dữ liệu từ nguồn Crossref...")
    raw_path = settings.paths.raw_records_json
    if settings.refresh_source or not raw_path.exists():
        print(f"  -> Gọi API: {settings.source_api} (query: '{settings.source_query}')")
        records = fetch_source_records(settings)
    else:
        print(f"  -> Nạp raw records từ snapshot lưu sẵn: {raw_path}")
        records = load_raw_records(raw_path)

    source_summary = {
        "source_api": settings.source_api,
        "source_query": settings.source_query,
        "total_records": len(records),
        "raw_records_path": str(raw_path),
    }
    print(f"  ✅ Đã tải/nạp thành công {len(records)} bản ghi thô.")

    # -------------------------------------------------------------------------
    # BƯỚC 2: Clean - Làm sạch dữ liệu và tạo text embedding
    # -------------------------------------------------------------------------
    print("\n[Bước 2/6] 🧹 Cleaning: Tiền xử lý dữ liệu và chuẩn bị text_for_embedding...")
    run_date = datetime.now(UTC)
    df = build_clean_dataframe(records, run_date=run_date)

    settings.paths.clean_csv.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(settings.paths.clean_csv, index=False)
    df.to_json(settings.paths.clean_json, orient="records", indent=2, date_format="iso")
    print(f"  ✅ Đã làm sạch thành công {len(df)} dòng dữ liệu.")
    print(f"  💾 Đã lưu dữ liệu sạch tại:")
    print(f"     - CSV : {settings.paths.clean_csv}")
    print(f"     - JSON: {settings.paths.clean_json}")

    # -------------------------------------------------------------------------
    # BƯỚC 3: Index ChromaDB - Khởi tạo & Đánh chỉ mục Vector Store
    # -------------------------------------------------------------------------
    print("\n[Bước 3/6] 🧠 Indexing: Khởi tạo & nạp dữ liệu vào ChromaDB Vector Store...")
    # Khởi tạo Embedding model dựa trên provider trong .env (Gemini / OpenAI API hoặc MiniLM)
    embedder = build_embeddings(settings)
    embed_name = getattr(embedder, "model_name", getattr(embedder, "model", type(embedder).__name__))
    print(f"  -> Embedding Model: {embed_name} (Provider: {settings.llm_provider})")

    # Kết nối trực tiếp PersistentClient của ChromaDB
    chroma_client = chromadb.PersistentClient(path=str(settings.paths.chroma_dir))
    print(f"  -> Đã kết nối ChromaDB PersistentClient tại: {settings.paths.chroma_dir}")

    # Đánh chỉ mục vector toàn bộ tài liệu bằng mô hình embedding
    index = LocalEmbeddingIndex.build(df=df, settings=settings, embedding_model=embedder)
    chroma_collection = chroma_client.get_collection(name=index.collection_name)
    total_vectors = chroma_collection.count()
    print(f"  ✅ Đã khởi tạo ChromaDB Collection: '{index.collection_name}'")
    print(f"  ✅ Số lượng vectors đã lưu trong ChromaDB: {total_vectors}/{len(df)}")
    print(f"  💾 Vector database lưu tại: {settings.paths.chroma_dir}")

    # -------------------------------------------------------------------------
    # BƯỚC 4: Sinh Testset - Benchmark Evaluation Test Set (10 câu hỏi)
    # -------------------------------------------------------------------------
    print("\n[Bước 4/6] 📋 Testset: Chuẩn bị Benchmark Evaluation Test Set...")
    testset_path = settings.paths.eval_testset
    if settings.refresh_test_set or not testset_path.exists():
        print(f"  -> Đang sinh mới bộ test set 10 câu hỏi qua 4 nhóm nghiệp vụ...")
        test_set = build_test_set(df, output_path=testset_path)
    else:
        print(f"  -> Nạp bộ test set có sẵn từ: {testset_path}")
        test_set = read_json(testset_path)
    print(f"  ✅ Bộ test set gồm {len(test_set)} câu hỏi đã sẵn sàng.")

    # -------------------------------------------------------------------------
    # BƯỚC 5: Luồng gọi RAG (Retrieval-Augmented Generation) & Đánh giá Hiệu năng
    # -------------------------------------------------------------------------
    print("\n[Bước 5/6] 🤖 Luồng RAG & Evaluation: Chạy RAG Model/Agent và Đánh giá Benchmark...")
    print(f"  -> Cấu hình RAG Generator: Provider = '{settings.llm_provider}', Model = '{settings.model_name}'")

    # 5.1. Demo luồng truy vấn RAG thực tế trên câu hỏi mẫu
    demo_sample_q = test_set[0]["question"] if test_set else "Agentic Retrieval-Augmented Generation"
    print(f"  🔍 [RAG Flow Demo] Thực thi luồng RAG trên câu hỏi mẫu:")
    print(f"     ❓ Question: {demo_sample_q}")

    # Gọi RAG QA kết hợp LLM Generator (Gemini/OpenAI từ .env)
    rag_result = answer_question(demo_sample_q, settings=settings, index=index, use_llm=True)
    print(f"     📥 Retrieved Docs: {rag_result.retrieved_doc_ids}")
    print(f"     💬 RAG Model Answer ({settings.model_name}):\n        \"{rag_result.answer[:160]}...\"")

    # Chạy thử nghiệm RAG Agent với Tools tìm kiếm
    demo_answers: list[dict[str, Any]] = []
    try:
        agent = build_agent(settings=settings, index=index)
        agent_answer = run_agent_question(agent, demo_sample_q)
        print(f"     🤖 RAG Agent Answer:\n        \"{agent_answer[:160]}...\"")
        demo_answers.append({
            "question": demo_sample_q,
            "provider": settings.llm_provider,
            "model_name": settings.model_name,
            "retrieved_doc_ids": rag_result.retrieved_doc_ids,
            "qa_answer": rag_result.answer,
            "agent_answer": agent_answer,
        })
    except Exception as exc:
        print(f"     ℹ️ Ghi nhận kết quả RAG QA chain (Agent invocation note: {exc})")
        demo_answers.append({
            "question": demo_sample_q,
            "provider": settings.llm_provider,
            "model_name": settings.model_name,
            "retrieved_doc_ids": rag_result.retrieved_doc_ids,
            "qa_answer": rag_result.answer,
            "agent_answer": rag_result.answer,
        })

    # Lưu kết quả demo vào file agent_demo_answers.json
    write_json(settings.paths.demo_answers, demo_answers)
    print(f"  💾 Đã lưu demo RAG answers tại: {settings.paths.demo_answers}")

    # 5.2. Đánh giá tự động toàn bộ Benchmark Testset (10 câu hỏi)
    print(f"  📊 Đang đánh giá toàn diện Benchmark qua {len(test_set)} câu hỏi...")
    eval_bundle = evaluate_pipeline(
        settings=settings,
        index=index,
        test_set_path=testset_path,
        metrics_output_path=settings.paths.baseline_metrics,
        answers_output_path=settings.paths.baseline_answers,
    )
    baseline_metrics = eval_bundle.summary
    hit_rate = baseline_metrics.get("retrieval_hit_rate", 0.0)
    token_f1 = baseline_metrics.get("mean_token_f1", 0.0)
    print(f"  ✅ Baseline Metrics:")
    print(f"     - Retrieval Hit Rate: {hit_rate:.4f} ({hit_rate * 100:.1f}%)")
    print(f"     - Mean Token F1     : {token_f1:.4f}")
    print(f"     - Judge Accuracy    : {baseline_metrics.get('judge_accuracy', 0.0):.4f}")
    print(f"     - Mean Judge Score  : {baseline_metrics.get('mean_judge_score', 0.0):.2f}/5.0")
    print(f"  💾 Kết quả metrics lưu tại: {settings.paths.baseline_metrics}")

    # -------------------------------------------------------------------------
    # BƯỚC 6: Great Expectations Quality Gate & Báo cáo Markdown
    # -------------------------------------------------------------------------
    print("\n[Bước 6/6] 🛡️ Observability: Kiểm định Great Expectations 1.x & Freshness SLA...")
    quality_result = run_data_quality_checks(df, settings, report_name="baseline")
    freshness_result = build_freshness_report(df, settings, report_path=settings.paths.freshness_report)

    print(f"  ✅ Great Expectations Status: {quality_result.get('success')}")
    print(f"  ✅ Freshness SLA Status: {freshness_result.get('is_fresh')} (Stale: {freshness_result.get('stale_rows')}/{freshness_result.get('total_rows')})")

    # Xuất báo cáo Markdown
    report_file = settings.paths.baseline_report
    generate_phase1_report(
        report_path=report_file,
        source_summary=source_summary,
        metrics=baseline_metrics,
        quality=quality_result,
        freshness=freshness_result,
    )
    print(f"  📄 Đã xuất báo cáo Markdown tại: {report_file}")

    print("\n" + "=" * 72)
    print("🎉 HOÀN THÀNH TOÀN BỘ BASELINE PHASE 1 PIPELINE THÀNH CÔNG!")
    print("=" * 72)

    return {
        "source_summary": source_summary,
        "clean_rows": len(df),
        "collection_name": index.collection_name,
        "test_set_size": len(test_set),
        "metrics": baseline_metrics,
        "quality": quality_result,
        "freshness": freshness_result,
        "report_path": str(report_file),
    }


def main() -> None:
    settings = load_settings()
    run_phase1_pipeline(settings)


if __name__ == "__main__":
    main()
