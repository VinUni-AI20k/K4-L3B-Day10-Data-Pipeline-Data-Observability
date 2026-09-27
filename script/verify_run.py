"""Independently verify a sealed run without opening a writable Chroma client."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sqlite3
from statistics import mean
import struct


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def token_f1(reference, prediction):
    left, right = set(reference.lower().split()), set(prediction.lower().split())
    return 2 * len(left & right) / (len(left) + len(right)) if left and right else 0.0


def verify_run(root: Path, project: Path | None = None) -> dict:
    root = root.resolve()
    manifest = read(root / "run_manifest.json")
    checks = {}

    def check(name, condition):
        checks[name] = bool(condition)

    def located(relative):
        path = (root / relative).resolve()
        if not path.is_relative_to(root):
            raise ValueError("Artifact path escapes run root")
        return path

    for relative, expected in manifest["inputs"].items():
        path = located(relative)
        check("input_hash:" + relative, path.is_file() and digest(path) == expected)
    for name in ("baseline", "comparison"):
        stage = manifest["stages"][name]
        check(name + ":complete", stage["status"] == "complete")
        for relative, expected in stage["artifacts"].items():
            path = located(relative)
            check("artifact_hash:" + relative, path.is_file() and digest(path) == expected)
    if project is not None:
        for relative, expected in manifest["identity"]["source_sha256"].items():
            path = project / relative
            check("source_hash:" + relative, path.is_file() and digest(path) == expected)
        for name, expected in manifest["identity"]["source_raw_sha256"].items():
            path = project / "data/raw" / name
            check("original_raw_hash:" + name, path.is_file() and digest(path) == expected)

    baseline_dir = located(manifest["stages"]["baseline"]["output_dir"])
    comparison_dir = located(manifest["stages"]["comparison"]["output_dir"])
    questions = read(baseline_dir / "eval/test_set.json")
    check("same_frozen_benchmark", questions == read(comparison_dir / "eval/test_set.json"))
    check("ten_questions_four_types", len(questions) == 10 and
          {q["question_type"] for q in questions} == {"summary", "authors", "date", "categories"})
    check("baseline_benchmark_hash", read(baseline_dir / "stage_result.json")["source"]["test_set_sha256"]
          == digest(baseline_dir / "eval/test_set.json"))
    check("comparison_benchmark_hash", read(comparison_dir / "stage_result.json")["test_set_sha256"]
          == digest(comparison_dir / "eval/test_set.json"))
    state_rows, state_metrics, state_quality, state_freshness = {}, {}, {}, {}
    collection_counts = {}
    for state, directory, suffix in (("baseline", baseline_dir, ""),
                                     ("corrupted", comparison_dir, "_corrupted"),
                                     ("repaired", comparison_dir, "_repaired")):
        rows = read(directory / "clean" / f"papers_clean{suffix}.json")
        answers = read(directory / "results" / f"{state}_answers.json")
        metric = read(directory / "results" / f"{state}_metrics.json")
        quality = read(directory / "quality" / f"{state}_quality_report.json")
        freshness = read(directory / "quality" / ("freshness_report.json" if state == "baseline"
                                                   else f"{state}_freshness_report.json"))
        embedding = read(directory / "embeddings" / f"papers_embeddings{suffix}.json")
        state_rows[state], state_metrics[state] = rows, metric
        state_quality[state], state_freshness[state] = quality, freshness
        check(state + ":same_questions", len(answers) == len(questions) and all(
            all(a[k] == q[k] for k in ("id", "question_type", "question", "ground_truth", "ground_truth_doc_ids"))
            for a, q in zip(answers, questions)))
        f1 = [token_f1(a["ground_truth"], a["answer"]) for a in answers]
        hits = [any(doi in a["ground_truth_doc_ids"] for doi in a["retrieved_doc_ids"]) for a in answers]
        source_hits = [any(doi in a["ground_truth_doc_ids"] for doi in a["answer_doc_ids"]) for a in answers]
        calculated = {
            "samples": len(answers), "retrieval_hit_rate": mean(hits), "mean_token_f1": mean(f1),
            "answer_source_hit_rate": mean(source_hits),
            "mean_grounded_token_f1": mean(v if hit else 0 for v, hit in zip(f1, source_hits)),
            "abstention_rate": mean(a["abstained"] for a in answers),
            "judge_accuracy": mean(a["judge"]["correct"] for a in answers),
            "mean_judge_score": mean(a["judge"]["score"] for a in answers),
            "heuristic_judge_count": sum(a["judge"]["backend"] == "heuristic" for a in answers),
        }
        check(state + ":metrics_recomputed", all(math.isclose(metric[k], v, abs_tol=1e-12)
                                                  for k, v in calculated.items()))
        check(state + ":per_answer_scores", all(math.isclose(a["token_f1"], v, abs_tol=1e-12)
                                                 and a["retrieval_hit"] == h and a["answer_source_hit"] == sh
                                                 for a, v, h, sh in zip(answers, f1, hits, source_hits)))
        check(state + ":freshness", freshness["stale_rows"] == sum(r["age_days"] > 180 for r in rows)
              and freshness["total_rows"] == len(rows) and quality["freshness"] == freshness)
        documents = embedding["documents"]
        check(state + ":manifest_matches_clean", len(documents) == len(rows) and all(
            d["paper_id"] == r["paper_id"] and d["content"] == r["text_for_embedding"]
            and all(d["metadata"][k] == r[k] for k in d["metadata"])
            for d, r in zip(documents, rows)))
        embedding_path = directory / "embeddings" / f"papers_embeddings{suffix}.json"
        db_dir = (embedding_path.parent / embedding["persist_path"]).resolve()
        check(state + ":portable_db_path", not Path(embedding["persist_path"]).is_absolute()
              and db_dir.is_relative_to(root))
        with sqlite3.connect((db_dir / "chroma.sqlite3").as_uri() + "?mode=ro&immutable=1", uri=True) as db:
            check(state + ":sqlite_integrity", db.execute("PRAGMA quick_check").fetchall() == [("ok",)])
            collection = db.execute("SELECT id,dimension FROM collections WHERE name=?",
                                    (embedding["collection_name"],)).fetchone()
            check(state + ":dimension", collection is not None and collection[1] == 384)
            if collection is None:
                continue
            count = db.execute("SELECT count(e.id) FROM embeddings e JOIN segments s ON s.id=e.segment_id "
                               "WHERE s.collection=?", (collection[0],)).fetchone()[0]
            collection_counts[state] = count
            check(state + ":index_count", count == len(rows))
            segments = db.execute("SELECT id FROM segments WHERE collection=? AND scope='VECTOR'",
                                  (collection[0],)).fetchall()
            check(state + ":vector_segments_present", bool(segments) and all(
                all((db_dir / segment / filename).is_file()
                    for filename in ("header.bin", "length.bin", "link_lists.bin", "data_level0.bin"))
                for segment, in segments))
            records = db.execute("SELECT e.embedding_id FROM embeddings e JOIN segments s ON s.id=e.segment_id "
                                 "WHERE s.collection=?", (collection[0],)).fetchall()
            check(state + ":record_ids", {r[0] for r in records} == {d["record_id"] for d in documents})
        challenge = read(directory / "results" / f"{state}_challenges.json")
        check(state + ":negative_challenges", challenge["passed"] == challenge["samples"]
              and all(a["abstained"] and not a["answer_doc_ids"] for a in challenge["answers"]))
    check("document_counts", [len(state_rows[s]) for s in ("baseline", "corrupted", "repaired")] == [24, 20, 24])
    check("repair_content_exact", state_rows["baseline"] == state_rows["repaired"])
    check("repair_metrics_exact", state_metrics["baseline"] == state_metrics["repaired"])
    check("quality_sequence", [state_quality[s]["success"] for s in ("baseline", "corrupted", "repaired")]
          == [True, False, True])
    log = read(comparison_dir / "results/corruption_log.json")
    check("six_corruptions", {e["type"] for e in log["events"]} ==
          {"drop_latest", "blank_summary", "inject_noise", "truncate_title", "stale_date", "duplicate_doi"})
    report = (comparison_dir / "reports/corruption_report.md").read_text(encoding="utf-8")
    for label, metric_name, fmt in (("Retrieval Hit Rate", "retrieval_hit_rate", ".2%"),
                                  ("Mean Token F1", "mean_token_f1", ".4f"),
                                  ("Grounded Token F1", "mean_grounded_token_f1", ".4f"),
                                  ("Abstention rate", "abstention_rate", ".2%")):
        expected = "| " + label + " | " + " | ".join(format(state_metrics[s][metric_name], fmt)
                    for s in ("baseline", "corrupted", "repaired")) + " |"
        check("report:" + label, expected in report)
    failed = [name for name, passed in checks.items() if not passed]
    return {"run_id": manifest["run_id"], "passed": not failed, "check_count": len(checks),
            "failed_checks": failed, "collection_counts": collection_counts,
            "metrics": state_metrics, "checks": checks}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--project-dir", type=Path, help="Also match current source and original raw hashes")
    args = parser.parse_args()
    result = verify_run(args.run_dir, args.project_dir)
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
