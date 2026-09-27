"""Local web demo. All generated files stay beneath demo/runtime/."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import mimetypes
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import threading
import time
from urllib.parse import urlparse
from uuid import uuid4

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.dont_write_bytecode = True
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "script")]
for name in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(name, "1")
for name in ("HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE", "HF_HUB_DISABLE_TELEMETRY"):
    os.environ.setdefault(name, "1")
os.environ.setdefault("GX_ANALYTICS_ENABLED", "false")
os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")
os.environ.setdefault("RUN_RAGAS", "0")

STATES = ("baseline", "corrupted", "repaired")
DEFAULT_RUN = ROOT / "data/runs/cp6_pipeline_20260927_04"
SAVED_ONLINE = ROOT / "data/live_demos/cp6_gemini_20260927_02"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(path)


def online_config():
    from dotenv import dotenv_values
    env = dotenv_values(ROOT / ".env")
    key = (env.get("GEMINI_API_KEY") or env.get("GOOGLE_API_KEY")
           or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or "").strip()
    provider = (env.get("LLM_PROVIDER") or "gemini").lower()
    model = env.get("LLM_MODEL") if provider in {"gemini", "google"} else None
    return key, model or "gemini-3.5-flash-lite"


class Snapshot:
    def __init__(self, directory):
        from verify_run import verify_run
        self.root = Path(directory).resolve()
        verified = verify_run(self.root)
        if not verified["passed"]:
            raise ValueError("Run không vượt kiểm tra artifact: " + ", ".join(verified["failed_checks"][:3]))
        self.manifest = read(self.root / "run_manifest.json")
        self.states = {}
        self.stage_dirs = {}
        for state in STATES:
            stage = "baseline" if state == "baseline" else "comparison"
            folder = self.root / self.manifest["stages"][stage]["output_dir"]
            suffix = "" if state == "baseline" else "_" + state
            rows = read(folder / "clean" / f"papers_clean{suffix}.json")
            self.stage_dirs[state] = folder
            self.states[state] = {
                "rows": rows, "count": len(rows), "unique_dois": len({r["paper_id"] for r in rows}),
                "metrics": read(folder / "results" / f"{state}_metrics.json"),
                "quality": read(folder / "quality" / f"{state}_quality_report.json"),
            }
        self.events = read(self.stage_dirs["corrupted"] / "results/corruption_log.json")["events"]
        self.verified_checks = verified["check_count"]
        self.sha = digest(self.root / "run_manifest.json")

    def public(self):
        key, model = online_config()
        online = None
        if (SAVED_ONLINE / "demo_manifest.json").is_file():
            manifest = read(SAVED_ONLINE / "demo_manifest.json")
            valid = all((SAVED_ONLINE / p).is_file() and digest(SAVED_ONLINE / p) == h
                        for p, h in manifest["artifacts"].items())
            if valid:
                saved = read(SAVED_ONLINE / "online_results.json")
                online = {"model": saved["model"], "summary": saved["summary"],
                          "run_id": saved["pipeline_run_id"], "demo_id": saved["demo_id"],
                          "continued": bool(saved.get("resumed_from_demo")),
                          "answers": [{k: a[k] for k in ("state", "case_id", "answer", "checks")}
                                      for a in saved["answers"]]}
        return {"run_id": self.manifest["run_id"], "created_at": self.manifest["created_at_utc"],
                "manifest_sha256": self.sha, "verified_checks": self.verified_checks,
                "states": self.states, "events": self.events, "saved_online": online,
                "model": model, "gemini_ready": bool(key), "provider": "gemini"}


class Lab:
    def __init__(self, run=DEFAULT_RUN):
        self.snapshot = Snapshot(run)
        self.runtime = HERE / "runtime" / (datetime.now(UTC).strftime("%Y%m%d_%H%M%S") + "_" + uuid4().hex[:6])
        self.jobs = {}
        self.guard = threading.RLock()
        self.pool = ThreadPoolExecutor(max_workers=1)
        self.active = None
        self.indices = {}

    def status(self):
        with self.guard:
            result = self.snapshot.public()
            result["active_job"] = self.active
            return result

    def get_job(self, job_id):
        with self.guard:
            if job_id not in self.jobs:
                raise KeyError("Không tìm thấy tác vụ")
            return json.loads(json.dumps(self.jobs[job_id]))

    def update(self, job_id, **values):
        with self.guard:
            self.jobs[job_id].update(values)

    def submit(self, kind, payload):
        if kind == "chat":
            question = payload.get("question", "")
            states = payload.get("states", [])
            mode = payload.get("mode", "gemini")
            if not isinstance(question, str) or not 1 <= len(question.strip()) <= 2000:
                raise ValueError("Câu hỏi phải dài từ 1 đến 2.000 ký tự")
            if not isinstance(states, list) or not states or len(states) > 3 or any(s not in STATES for s in states):
                raise ValueError("Chọn một hoặc cả ba trạng thái hợp lệ")
            if len(states) != len(set(states)) or mode not in {"gemini", "local"}:
                raise ValueError("Chế độ hoặc trạng thái không hợp lệ")
            if mode == "gemini" and not online_config()[0]:
                raise ValueError("Chưa có GEMINI_API_KEY hoặc GOOGLE_API_KEY trong .env")
            payload = {"question": question.strip(), "states": states, "mode": mode}
        elif kind != "pipeline":
            raise ValueError("Tác vụ không hợp lệ")
        with self.guard:
            if self.active:
                raise RuntimeError("Một tác vụ đang chạy. Vui lòng đợi hoàn tất.")
            job_id = uuid4().hex[:16]
            self.active = job_id
            self.jobs[job_id] = {"id": job_id, "kind": kind, "status": "queued", "progress": "Đang chuẩn bị…", "answers": []}
            if len(self.jobs) > 50:
                self.jobs.pop(next(iter(self.jobs)))
            self.pool.submit(self.execute, job_id, kind, payload)
            return job_id

    def execute(self, job_id, kind, payload):
        self.update(job_id, status="running")
        try:
            if kind == "chat":
                self.chat(job_id, payload)
            else:
                self.pipeline(job_id)
            self.update(job_id, status="complete", progress="Hoàn tất")
        except Exception as exc:
            from run_live_demo import safe_error
            info = safe_error(exc, online_config()[0])
            self.update(job_id, status="failed", progress="Tác vụ chưa hoàn tất", error=info,
                        message="Provider hoặc pipeline báo lỗi. Kết quả đã trả được giữ lại; không chuyển sang mock.")
        finally:
            self.update(job_id, finished_at=datetime.now(UTC).isoformat())
            save(self.runtime / "jobs" / f"{job_id}.json", self.get_job(job_id))
            with self.guard:
                self.active = None

    def index(self, state, settings):
        from retrieval.index import LocalEmbeddingIndex
        if state not in self.indices:
            target = self.runtime / "indices" / self.snapshot.manifest["run_id"] / state
            shutil.copytree(self.snapshot.stage_dirs[state], target)
            suffix = "" if state == "baseline" else "_" + state
            self.indices[state] = LocalEmbeddingIndex.load(settings, target / "embeddings" / f"papers_embeddings{suffix}.json")
        return self.indices[state]

    def chat(self, job_id, payload):
        from dataclasses import replace
        from core.config import load_settings
        from retrieval.agent import build_agent
        from retrieval.qa import answer_question
        from run_live_demo import sanitize_trace
        key, model = online_config()
        settings = replace(load_settings(ROOT), llm_provider="gemini", model_name=model, google_api_key=key)
        llm = None
        callbacks = []
        if payload["mode"] == "gemini":
            from langchain_google_genai import ChatGoogleGenerativeAI
            from langchain_core.callbacks import BaseCallbackHandler

            class Budget(BaseCallbackHandler):
                raise_error = True

                def __init__(self):
                    self.count = 0
                    self.last = 0.0

                def on_chat_model_start(self, serialized, messages, **kwargs):
                    if self.count >= 12:
                        raise RuntimeError("Đã đạt giới hạn 12 lượt gọi model cho câu hỏi này")
                    time.sleep(max(0, 4 - (time.monotonic() - self.last)))
                    self.last = time.monotonic()
                    self.count += 1

            callbacks = [Budget()]
            llm = ChatGoogleGenerativeAI(model=model, google_api_key=key, temperature=0,
                                        max_output_tokens=1500, timeout=60, max_retries=0, include_thoughts=False)
        self.update(job_id, question=payload["question"], mode=payload["mode"], run_id=self.snapshot.manifest["run_id"])
        answers = []
        for state in payload["states"]:
            self.update(job_id, progress="Đang hỏi trên dữ liệu " + state + "…")
            started = time.monotonic()
            index = self.index(state, settings)
            if llm is not None:
                agent = build_agent(settings, index, llm=llm)
                result = agent.invoke({"messages": [{"role": "user", "content": payload["question"]}]},
                                      config={"recursion_limit": 8, "callbacks": callbacks})
                trace = sanitize_trace(result["messages"])
                if not trace or trace[-1]["type"] != "ai" or trace[-1].get("tool_calls"):
                    raise RuntimeError("Model chưa trả lời hoàn chỉnh")
                answer = trace[-1]["content"].strip()
                tool_calls = [call for msg in trace for call in msg.get("tool_calls", [])]
                dois = set(doi for msg in trace if msg["type"] == "tool"
                           for doi in re.findall(r"^paper_id:\s*(\S+)", msg["content"], re.MULTILINE))
                tokens = sum((msg.get("usage") or {}).get("total_tokens", 0) for msg in trace)
                models = sorted({msg.get("response_model") for msg in trace if msg.get("response_model")})
            else:
                local = answer_question(payload["question"], settings, index)
                answer, dois = local.answer, set(local.answer_doc_ids)
                tool_calls, trace, tokens, models = [], [], 0, ["extractive_metadata"]
            sources = []
            for doi in sorted(dois):
                record = index.lookup(doi)
                if record:
                    sources.append({"paper_id": doi, "title": record["title"], "published": record["metadata"]["published"]})
            row = {"state": state, "answer": answer, "sources": sources, "tool_calls": tool_calls,
                   "trace": trace, "tokens": tokens, "models": models, "mode": payload["mode"],
                   "elapsed_seconds": round(time.monotonic() - started, 2)}
            answers.append(row)
            self.update(job_id, answers=list(answers))

    def pipeline(self, job_id):
        target = self.runtime / "pipeline_runs" / ("web_" + uuid4().hex[:10])
        logs = self.runtime / "logs"
        logs.mkdir(parents=True, exist_ok=True)
        for script, label in (("run_phase1.py", "Baseline: làm sạch → quality gate → index → benchmark"),
                              ("run_corruption_flow.py", "Corruption → đánh giá → repair → so sánh")):
            self.update(job_id, progress=label)
            log = logs / f"{job_id}_{script}.log"
            with log.open("w", encoding="utf-8") as stream:
                result = subprocess.run([sys.executable, "-B", str(ROOT / "script" / script), "--output-dir", str(target)],
                                        cwd=ROOT, stdout=stream, stderr=stream, timeout=300,
                                        env={**os.environ, "PYTHONIOENCODING": "utf-8"})
            if result.returncode:
                raise RuntimeError("Pipeline thất bại: " + script)
        updated = Snapshot(target)
        self.close_indices()
        with self.guard:
            self.snapshot = updated
        self.update(job_id, run_id=updated.manifest["run_id"], verified_checks=updated.verified_checks)

    def close_indices(self):
        for index in self.indices.values():
            index.close()
        self.indices = {}

    def close(self):
        self.pool.shutdown(wait=True)
        self.close_indices()


class Handler(BaseHTTPRequestHandler):
    server_version = "DataLab/1.0"

    def log_message(self, format, *args):
        pass

    def send(self, status, body, content_type="application/json; charset=utf-8"):
        data = json.dumps(body, ensure_ascii=False).encode("utf-8") if isinstance(body, dict) else body
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'self'; script-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/dashboard":
            self.send(200, self.server.lab.status())
        elif re.fullmatch(r"/api/jobs/[a-f0-9]{16}", path):
            try:
                self.send(200, self.server.lab.get_job(path.rsplit("/", 1)[-1]))
            except KeyError:
                self.send(404, {"error": "Không tìm thấy tác vụ"})
        elif path in {"/", "/index.html", "/styles.css", "/app.js", "/favicon.svg"}:
            target = HERE / "static" / ("index.html" if path == "/" else path[1:])
            self.send(200, target.read_bytes(), (mimetypes.guess_type(target.name)[0] or "application/octet-stream") + "; charset=utf-8")
        else:
            self.send(404, {"error": "Không tìm thấy trang"})

    def do_POST(self):
        allowed = {f"http://127.0.0.1:{self.server.server_port}", f"http://localhost:{self.server.server_port}"}
        origin = self.headers.get("Origin")
        host = self.headers.get("Host")
        if host not in {f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}"} or (origin and origin not in allowed):
            self.send(403, {"error": "Origin không hợp lệ"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 32000 or self.headers.get_content_type() != "application/json":
                raise ValueError("Yêu cầu phải là JSON, tối đa 32KB")
            payload = json.loads(self.rfile.read(length))
            if not isinstance(payload, dict):
                raise ValueError("JSON phải là object")
            kind = {"/api/chat": "chat", "/api/pipeline": "pipeline"}.get(self.path)
            job_id = self.server.lab.submit(kind, payload)
            self.send(202, {"job_id": job_id})
        except RuntimeError as exc:
            self.send(409, {"error": str(exc)})
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            self.send(400, {"error": str(exc)})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--run", type=Path, default=DEFAULT_RUN)
    args = parser.parse_args()
    lab = Lab(args.run)
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    server.lab = lab
    print(f"Data Observatory: http://127.0.0.1:{args.port}", flush=True)
    print("Ctrl+C to stop. New artifacts stay in demo/runtime/.", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        lab.close()


if __name__ == "__main__":
    main()
