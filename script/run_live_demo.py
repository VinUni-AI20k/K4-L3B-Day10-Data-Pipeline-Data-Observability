"""Run CP6: deterministic data pipeline followed by real Gemini/OpenRouter agent calls.

No online judge or mock fallback: deterministic checks score four focused demo cases.
The ten-question offline benchmark is preserved and reported separately.
"""
from __future__ import annotations

import argparse
from datetime import UTC, datetime
import hashlib
from importlib.metadata import version
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "script"))
for key in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(key, "1")
for key in ("HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE", "HF_HUB_DISABLE_TELEMETRY"):
    os.environ.setdefault(key, "1")
os.environ.setdefault("RUN_RAGAS", "0")
os.environ.setdefault("GX_ANALYTICS_ENABLED", "false")
os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")

DEFAULT_MODEL = "openrouter/free"
ABSTENTION = "I don't know from the indexed corpus."
STATES = ("baseline", "corrupted", "repaired")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path, payload):
    from core.utils import write_json
    write_json(path, payload)


def checked_name(value):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}", value):
        raise argparse.ArgumentTypeError("Use 1-80 letters, digits, underscores or hyphens")
    return value


def build_cases(baseline, corrupted, log):
    """Freeze cases before calling the model; references come from original baseline."""
    original = {r["paper_id"]: r for r in baseline}
    dirty = {r["paper_id"]: r for r in corrupted}
    events = {e["type"]: e for e in log["events"]}
    dropped = events["drop_latest"]["paper_ids"][0]
    stale = events["stale_date"]["paper_ids"][0]
    touched = {doi for e in log["events"] for doi in e["paper_ids"]}
    stable = next(doi for doi in original if doi not in touched and doi in dirty)
    rows = []
    for name, doi in (("dropped_paper", dropped), ("stale_date", stale),
                      ("stable_control", stable), ("absent_control", "10.9999/cp6-not-in-corpus")):
        dates = {"baseline": original.get(doi, {}).get("published", ABSTENTION),
                 "corrupted": dirty.get(doi, {}).get("published", ABSTENTION),
                 "repaired": original.get(doi, {}).get("published", ABSTENTION)}
        rows.append({"id": name, "paper_id": doi,
                     "question": f"When was the paper '{doi}' published? Return only the publication date "
                     f"as YYYY-MM-DD. If unavailable, return exactly: {ABSTENTION}",
                     "ground_truth": dates["baseline"], "expected_by_state": dates})
    return rows


def message_text(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(part.get("text", "") for part in content if isinstance(part, dict)
                       and part.get("type") == "text")
    return ""


def sanitize_trace(messages):
    """Keep observable answers/tools/usage, never request headers or hidden reasoning."""
    trace = []
    for msg in messages:
        kind = getattr(msg, "type", "")
        if kind not in {"ai", "tool"}:
            continue
        row = {"type": kind, "content": message_text(msg.content)}
        if kind == "ai":
            row["tool_calls"] = getattr(msg, "tool_calls", [])
            row["usage"] = getattr(msg, "usage_metadata", None)
            metadata = getattr(msg, "response_metadata", {})
            row["response_model"] = metadata.get("model_name") or metadata.get("model")
            row["finish_reason"] = metadata.get("finish_reason")
        else:
            row["name"] = getattr(msg, "name", None)
            row["tool_call_id"] = getattr(msg, "tool_call_id", None)
        trace.append(row)
    return trace


def safe_error(exc, api_key=""):
    status = getattr(exc, "status_code", getattr(exc, "code", None))
    result = {"type": type(exc).__name__, "http_status": status if isinstance(status, int) else None}
    body = getattr(exc, "body", None)
    if isinstance(body, dict):
        error = body.get("error", body)
        if isinstance(error, dict):
            metadata = error.get("metadata")
            metadata = metadata if isinstance(metadata, dict) else {}
            for name, value in (("message", error.get("message")),
                                ("provider_message", metadata.get("raw")),
                                ("provider_name", metadata.get("provider_name")),
                                ("limit_source", metadata.get("limit_source"))):
                if isinstance(value, str):
                    if api_key:
                        value = value.replace(api_key, "[REDACTED]")
                    result[name] = re.sub(r"user_[A-Za-z0-9]+", "[ACCOUNT_REDACTED]", value)[:800]
    return result


def score_case(case, state, answer, trace):
    expected = case["expected_by_state"][state]
    clean = answer.strip().strip('`"').strip()
    used_lookup = any(call.get("name") == "lookup_paper" and
                      call.get("args", {}).get("paper_id_or_title", "").lower() == case["paper_id"].lower()
                      for row in trace for call in row.get("tool_calls", []))
    tool_completed = any(row.get("type") == "tool" and row.get("name") == "lookup_paper"
                         for row in trace)
    return {"matches_indexed_context": clean == expected,
            "correct_against_raw": clean == case["ground_truth"],
            "abstained": clean == ABSTENTION,
            "used_exact_lookup": used_lookup and tool_completed,
            "passed": clean == expected and used_lookup and tool_completed}


def render_report(payload):
    lines = ["# CP6 — Live demo online", "",
             f"Status: **{payload['status']}**", "",
             f"Provider: {payload.get('provider', 'unknown')}; requested model: `{payload['model']}`.",
             f"Pipeline run: `{payload['pipeline_run_id']}`.", "",
             "Online answers below come from real tool-agent calls. Checks are deterministic; "
             "no LLM judge or heuristic fallback is used for these cases.", "",
             "| Case | Baseline answer | Corrupted answer | Repaired answer |",
             "| --- | --- | --- | --- |"]
    for case in payload.get("cases", []):
        cells = []
        for state in STATES:
            match = next((r for r in payload["answers"] if r["state"] == state and r["case_id"] == case["id"]), None)
            cells.append(match["answer"].replace("|", "\\|").replace("\n", " ") if match else "Not run")
        lines.append("| " + case["id"] + " | " + " | ".join(cells) + " |")
    lines += ["", "The stale-date answer should follow the damaged index and be wrong against raw. "
              "This demonstrates silent data failure; repair restores the correct date. "
              "The dropped paper should cause abstention and recover after repair.", "",
              "The separate ten-question offline benchmark remains extractive metadata QA/mock judging. "
              "These four online cases are a focused live demonstration, not a replacement full benchmark.", ""]
    if payload.get("summary"):
        lines += ["```json", json.dumps(payload["summary"], indent=2), "```", ""]
    return "\n".join(lines)


def replay(directory):
    directory = directory.resolve()
    manifest = read(directory / "demo_manifest.json")
    for name, expected in manifest["artifacts"].items():
        path = (directory / name).resolve()
        if not path.is_relative_to(directory) or not path.is_file() or sha(path) != expected:
            raise ValueError("Demo evidence missing or changed")
    print("REPLAY OF SAVED EVIDENCE - NO NEW ONLINE REQUESTS", flush=True)
    print((directory / "online_report.md").read_text(encoding="utf-8"))
    return 0 if manifest["status"] == "complete" else 1


def run(args):
    from dataclasses import replace
    from dotenv import dotenv_values
    from core.config import load_settings
    from core.utils import write_text
    from verify_run import verify_run

    directory = ROOT / "data/live_demos" / args.demo_id
    directory.mkdir(parents=True, exist_ok=False)
    payload = {"schema_version": 1, "demo_id": args.demo_id, "status": "running",
               "started_at_utc": datetime.now(UTC).isoformat(), "provider": args.provider,
               "model": args.model, "pipeline_run_id": args.run_id,
               "mode": "offline_rehearsal" if args.offline_rehearsal else "online",
               "answers": [], "online_requests": 0}
    limiter = None
    key = ""
    try:
        credentials = dotenv_values(ROOT / ".env")
        if args.provider == "gemini":
            key = (credentials.get("GOOGLE_API_KEY") or credentials.get("GEMINI_API_KEY")
                   or os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY") or "").strip()
        else:
            key = (credentials.get("OPENROUTER_API_KEY") or credentials.get("1OPENROUTER_API_KEY")
                   or os.getenv("OPENROUTER_API_KEY") or "").strip()
        if not args.offline_rehearsal:
            if not key:
                raise ValueError("API key is missing for selected provider")
            if args.provider == "gemini":
                request = urllib.request.Request(
                    "https://generativelanguage.googleapis.com/v1beta/models/" + args.model,
                    headers={"x-goog-api-key": key})
            else:
                request = urllib.request.Request("https://openrouter.ai/api/v1/key",
                                                 headers={"Authorization": "Bearer " + key})
            with urllib.request.urlopen(request, timeout=25) as response:
                response.read()
            print(f"[1/4] {args.provider} credential accepted; secret not logged.", flush=True)
        else:
            print("[1/4] Offline rehearsal: online acceptance will remain incomplete.", flush=True)

        for name in ("run_phase1", "run_corruption_flow"):
            print(f"[2/4] Running {name}.py --run-id {args.run_id}", flush=True)
            result = subprocess.run([sys.executable, "-B", str(ROOT / "script" / f"{name}.py"),
                                     "--run-id", args.run_id], cwd=ROOT, capture_output=True, text=True,
                                    encoding="utf-8", errors="replace")
            write_text(directory / f"{name}.log", result.stdout + result.stderr)
            if result.returncode:
                raise RuntimeError(f"{name} failed; see its local log")
            for line in result.stdout.splitlines():
                if line.startswith("[") or line.startswith("Reusing"):
                    print(line, flush=True)

        run_root = ROOT / "data/runs" / args.run_id
        verification = verify_run(run_root, ROOT)
        write(directory / "pipeline_verification.json", verification)
        if not verification["passed"]:
            raise RuntimeError("Pipeline artifact verification failed")
        manifest = read(run_root / "run_manifest.json")
        payload["pipeline_manifest_sha256"] = sha(run_root / "run_manifest.json")
        payload["source_sha256"] = manifest["identity"]["source_sha256"]
        payload["dependencies"] = {name: version(name) for name in
                                    ("langchain-openai", "langchain-google-genai", "google-genai",
                                     "langchain", "openai", "chromadb")}
        baseline = run_root / manifest["stages"]["baseline"]["output_dir"]
        comparison = run_root / manifest["stages"]["comparison"]["output_dir"]
        cases = build_cases(read(baseline / "clean/papers_clean.json"),
                            read(comparison / "clean/papers_clean_corrupted.json"),
                            read(comparison / "results/corruption_log.json"))
        payload["cases"] = cases
        write(directory / "demo_cases.json", cases)
        write_text(directory / "corruption_report.md",
                   (comparison / "reports/corruption_report.md").read_text(encoding="utf-8"))
        if args.offline_rehearsal:
            payload["status"] = "offline_rehearsal_only"
            return 0

        from langchain_core.callbacks import BaseCallbackHandler
        from retrieval.agent import build_agent
        from retrieval.index import LocalEmbeddingIndex

        class RateLimit(BaseCallbackHandler):
            raise_error = True

            def __init__(self):
                self.last = 0.0
                self.calls = 0

            def on_chat_model_start(self, serialized, messages, **kwargs):
                if self.calls >= 36:
                    raise RuntimeError("Demo exceeded its 36-request budget")
                delay = max(0, 3.2 - (time.monotonic() - self.last))
                time.sleep(delay)
                self.last = time.monotonic()
                self.calls += 1

        limiter = RateLimit()
        updates = {"llm_provider": args.provider, "model_name": args.model,
                   "refresh_source": False, "refresh_test_set": False,
                   "google_api_key" if args.provider == "gemini" else "openrouter_api_key": key}
        settings = replace(load_settings(ROOT), **updates)
        if args.provider == "gemini":
            from langchain_google_genai import ChatGoogleGenerativeAI
            llm = ChatGoogleGenerativeAI(model=args.model, google_api_key=key, temperature=0,
                                        max_output_tokens=1024, timeout=60, max_retries=0,
                                        include_thoughts=False)
        else:
            from langchain_openai import ChatOpenAI
            llm = ChatOpenAI(model=args.model, api_key=key, base_url="https://openrouter.ai/api/v1",
                             temperature=0, max_tokens=1024, timeout=60, max_retries=0,
                             extra_body={"provider": {"require_parameters": True}})
        # Opening Chroma can write internal files. All online queries use an explicit copy.
        working = directory / "working_index"
        shutil.copytree(run_root, working)
        print("[3/4] Calling real online tool agent for 4 cases x 3 states.", flush=True)
        for state in STATES:
            stage = "baseline" if state == "baseline" else "comparison"
            suffix = "" if state == "baseline" else "_" + state
            path = working / manifest["stages"][stage]["output_dir"] / "embeddings" / f"papers_embeddings{suffix}.json"
            index = LocalEmbeddingIndex.load(settings, path)
            try:
                agent = build_agent(settings, index, llm=llm)
                for case in cases:
                    print(f"ONLINE {state}/{case['id']} ...", flush=True)
                    started = time.monotonic()
                    result = agent.invoke({"messages": [{"role": "user", "content": case["question"]}]},
                                          config={"recursion_limit": 8, "callbacks": [limiter]})
                    trace = sanitize_trace(result["messages"])
                    if not trace or trace[-1]["type"] != "ai" or trace[-1].get("tool_calls"):
                        raise RuntimeError("Agent did not return a final answer")
                    answer = trace[-1]["content"].strip()
                    scores = score_case(case, state, answer, trace)
                    payload["answers"].append({"state": state, "case_id": case["id"],
                                               "question": case["question"], "paper_id": case["paper_id"],
                                               "ground_truth": case["ground_truth"],
                                               "expected_from_index": case["expected_by_state"][state],
                                               "answer": answer, "checks": scores, "trace": trace,
                                               "elapsed_seconds": round(time.monotonic() - started, 3)})
                    payload["online_requests"] = limiter.calls
                    write(directory / "online_results.json", payload)
                    print(f"  {answer} | context={scores['matches_indexed_context']} raw={scores['correct_against_raw']}"
                          f" tool={scores['used_exact_lookup']}", flush=True)
                    if not scores["passed"]:
                        payload["status"] = "acceptance_failed"
                        payload["failure_case"] = {"state": state, "case_id": case["id"]}
                        print("Stopping online calls after failed acceptance; evidence preserved.", flush=True)
                        return 1
            finally:
                index.close()
        payload["summary"] = {
            state: {"samples": 4, "context_checks_passed": sum(r["checks"]["passed"] for r in payload["answers"] if r["state"] == state),
                    "correct_against_raw": sum(r["checks"]["correct_against_raw"] for r in payload["answers"] if r["state"] == state)}
            for state in STATES}
        after = verify_run(run_root, ROOT)
        if not after["passed"] or sha(run_root / "run_manifest.json") != payload["pipeline_manifest_sha256"]:
            raise RuntimeError("Sealed pipeline changed during online demo")
        payload["sealed_pipeline_unchanged"] = True
        payload["status"] = "complete" if all(r["checks"]["passed"] for r in payload["answers"]) else "acceptance_failed"
        print("[4/4] " + payload["status"] + ": " + json.dumps(payload["summary"]), flush=True)
        return 0 if payload["status"] == "complete" else 1
    except (Exception, KeyboardInterrupt) as exc:
        payload["status"] = "interrupted" if isinstance(exc, KeyboardInterrupt) else "failed"
        payload["error"] = safe_error(exc, key)
        print("Demo failed (no mock fallback): " + json.dumps(payload["error"]), flush=True)
        return 1
    finally:
        payload["finished_at_utc"] = datetime.now(UTC).isoformat()
        if limiter is not None:
            payload["online_requests"] = limiter.calls
        write(directory / "online_results.json", payload)
        write_text(directory / "online_report.md", render_report(payload))
        artifacts = {p.relative_to(directory).as_posix(): sha(p) for p in sorted(directory.glob("*")) if p.is_file()}
        write(directory / "demo_manifest.json", {"status": payload["status"], "artifacts": artifacts,
                                                 "pipeline_run_id": args.run_id,
                                                 "pipeline_manifest_sha256": payload.get("pipeline_manifest_sha256")})
        print(f"Demo evidence: {directory.relative_to(ROOT).as_posix()}", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--replay", type=Path, help="Verify and display saved demo evidence without API calls")
    parser.add_argument("--demo-id", type=checked_name, default="cp6_" + datetime.now(UTC).strftime("%Y%m%d_%H%M%S"))
    parser.add_argument("--run-id", type=checked_name, default="cp6_pipeline_20260927_04")
    parser.add_argument("--provider", choices=("gemini", "openrouter"), help="Defaults to LLM_PROVIDER in .env")
    parser.add_argument("--model", help="Defaults to LLM_MODEL in .env for the selected provider")
    parser.add_argument("--offline-rehearsal", action="store_true", help="Prepare data only; does not pass online acceptance")
    args = parser.parse_args()
    if args.replay:
        return replay(args.replay)
    from dotenv import dotenv_values
    configured = dotenv_values(ROOT / ".env")
    configured_provider = (configured.get("LLM_PROVIDER") or "openrouter").lower()
    if configured_provider == "google":
        configured_provider = "gemini"
    args.provider = args.provider or configured_provider
    if args.provider not in {"gemini", "openrouter"}:
        parser.error("Live demo supports gemini or openrouter")
    args.model = args.model or (configured.get("LLM_MODEL") if args.provider == configured_provider else None)
    args.model = args.model or ("gemini-3.5-flash-lite" if args.provider == "gemini" else DEFAULT_MODEL)
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_./:-]*", args.model) or ".." in args.model:
        parser.error("Invalid model name")
    if args.provider == "openrouter" and not args.model.endswith(":free") and args.model != "openrouter/free":
        parser.error("The OpenRouter demo is scoped to free chat models")
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
