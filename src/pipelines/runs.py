"""Versioned offline runs: immutable inputs, verified reuse, and isolated retries."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from dataclasses import replace
from datetime import UTC, datetime
import hashlib
from importlib.metadata import PackageNotFoundError, version
import json
from pathlib import Path
import re
import shutil
from typing import Callable

from core.config import Settings, load_settings, with_output_dir
from core.utils import read_json, write_json
from ingestion.crossref import load_raw_records


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inventory(directory: Path) -> dict[str, str]:
    return {p.relative_to(directory).as_posix(): digest(p)
            for p in sorted(directory.rglob("*")) if p.is_file()}


def checked_path(root: Path, relative: str) -> Path:
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError(f"Manifest path escapes run directory: {relative}")
    return path


def verify_inventory(root: Path, expected: dict[str, str]) -> None:
    for relative, expected_hash in expected.items():
        path = checked_path(root, relative)
        if not path.is_file() or digest(path) != expected_hash:
            raise ValueError(f"Artifact missing or changed: {relative}")


def source_inventory(settings: Settings) -> dict[str, str]:
    root = settings.paths.project_dir
    files = [p for folder in ("src", "script") for p in (root / folder).rglob("*.py")]
    files += [root / name for name in ("pyproject.toml", "requirements.txt", "uv.lock")
              if (root / name).is_file()]
    return {p.relative_to(root).as_posix(): digest(p) for p in sorted(files)}


def run_identity(settings: Settings) -> dict:
    dependencies = {}
    for name in ("chromadb", "great-expectations", "sentence-transformers", "torch",
                 "numpy", "pandas", "langchain", "langchain-core"):
        try:
            dependencies[name] = version(name)
        except PackageNotFoundError:
            dependencies[name] = "not-installed"
    return {
        "source_sha256": source_inventory(settings),
        "dependencies": dependencies,
        "config": {name: getattr(settings, name) for name in (
            "llm_provider", "model_name", "embedding_model", "top_k", "max_results",
            "freshness_threshold_days")},
        "source_raw_sha256": {p.name: digest(p) for p in (
            settings.paths.raw_api_response, settings.paths.raw_records_json) if p.is_file()},
        "supplied_test_set_sha256": digest(settings.paths.eval_testset)
        if settings.paths.eval_testset.is_file() else None,
    }


class RunStore:
    """A completed stage is immutable; a failed stage gets a new attempt directory."""

    def __init__(self, settings: Settings, root: Path):
        self.settings = settings
        self.root = root.resolve()
        data_dir = settings.paths.clean_json.parent.parent.resolve()
        if (self.root == data_dir or data_dir.is_relative_to(self.root)
                or self.root.is_relative_to(settings.paths.raw_api_response.parent.resolve())):
            raise ValueError("Choose a separate run directory; existing data/raw cannot be an output")
        for name in ("src", "script", ".git", ".venv", "docs", "report"):
            if self.root.is_relative_to((settings.paths.project_dir / name).resolve()):
                raise ValueError(f"Run output must not be inside {name}")
        self.path = self.root / "run_manifest.json"
        self.manifest: dict = {}

    @contextmanager
    def locked(self):
        self.root.mkdir(parents=True, exist_ok=True)
        lock = self.root / ".run.lock"
        try:
            handle = lock.open("x", encoding="utf-8")
        except FileExistsError as exc:
            raise RuntimeError("Run is locked. Use another run ID; inspect any interrupted process before removing its lock.") from exc
        try:
            with handle:
                handle.write(f"Locked at {datetime.now(UTC).isoformat()}\n")
            self._open()
            yield self
        finally:
            lock.unlink(missing_ok=True)

    def _open(self) -> None:
        identity = run_identity(self.settings)
        if not identity["source_raw_sha256"]:
            raise FileNotFoundError("No offline raw snapshot is available")
        if self.settings.refresh_source or self.settings.refresh_test_set:
            raise ValueError("Managed runs freeze raw and benchmark inputs; use a new run with explicit offline inputs")
        if self.path.exists():
            self.manifest = read_json(self.path)
            if self.manifest["identity"] != identity:
                raise ValueError("Run inputs, configuration, dependencies or source changed; choose a new --run-id")
            self.verify()
            return
        if any(p.name != ".run.lock" for p in self.root.iterdir()):
            raise FileExistsError("Output directory contains unmanaged files; choose a new --run-id")
        raw_dir = self.root / "raw"
        raw_dir.mkdir()
        for source in (self.settings.paths.raw_api_response, self.settings.paths.raw_records_json):
            if source.is_file():
                shutil.copyfile(source, raw_dir / source.name)
        parsed = raw_dir / "crossref_records.json"
        response = raw_dir / "crossref_response.json"
        if not parsed.exists():
            write_json(parsed, [r.__dict__ for r in load_raw_records(response)])
        elif response.exists() and load_raw_records(parsed) != load_raw_records(response):
            raise ValueError("The two raw snapshots disagree; source files were not changed")
        inputs = {f"raw/{name}": value for name, value in inventory(raw_dir).items()}
        if self.settings.paths.eval_testset.is_file():
            target = self.root / "inputs" / "test_set.json"
            target.parent.mkdir()
            shutil.copyfile(self.settings.paths.eval_testset, target)
            inputs["inputs/test_set.json"] = digest(target)
        self.manifest = {
            "schema_version": 1,
            "run_id": self.root.name,
            "created_at_utc": datetime.now(UTC).isoformat(),
            "identity": identity,
            "inputs": inputs,
            "stages": {},
        }
        self._save()

    def _save(self) -> None:
        write_json(self.path, self.manifest)

    def verify(self) -> None:
        verify_inventory(self.root, self.manifest["inputs"])
        for stage in self.manifest["stages"].values():
            if stage["status"] == "complete":
                verify_inventory(self.root, stage["artifacts"])

    def stage_settings(self, directory: Path) -> Settings:
        settings = with_output_dir(self.settings, directory)
        return replace(settings, paths=replace(settings.paths,
            raw_api_response=self.root / "raw/crossref_response.json",
            raw_records_json=self.root / "raw/crossref_records.json"))

    def completed_settings(self, stage: str) -> Settings:
        record = self.manifest["stages"].get(stage)
        if not record or record["status"] != "complete":
            raise RuntimeError(f"Run {stage} successfully first using the same --run-id")
        return self.stage_settings(checked_path(self.root, record["output_dir"]))

    def execute(self, stage: str, operation: Callable[[Settings], dict]) -> dict:
        self.verify()
        prior = self.manifest["stages"].get(stage)
        if prior and prior["status"] == "complete":
            print(f"Reusing verified {stage} stage; no artifact rewritten.", flush=True)
            return read_json(checked_path(self.root, prior["result_path"]))
        attempts = list(prior.get("attempts", [])) if prior else []
        number = len(attempts) + 1
        directory = self.root / stage / f"attempt-{number:03d}"
        directory.mkdir(parents=True, exist_ok=False)
        attempt = {"output_dir": directory.relative_to(self.root).as_posix(),
                   "started_at_utc": datetime.now(UTC).isoformat(), "status": "running"}
        attempts.append(attempt)
        record = {"status": "running", "output_dir": attempt["output_dir"], "attempts": attempts}
        self.manifest["stages"][stage] = record
        self._save()
        try:
            result = operation(self.stage_settings(directory))
            write_json(directory / "stage_result.json", result)
            # Models/DB clients must be closed by operation before sealing its inventory.
            artifacts = {f"{attempt['output_dir']}/{name}": value for name, value in inventory(directory).items()}
            self.verify()  # Also protect earlier completed stages and frozen inputs.
            record.update(status="complete", artifacts=artifacts,
                          result_path=f"{attempt['output_dir']}/stage_result.json")
            attempt.update(status="complete", finished_at_utc=datetime.now(UTC).isoformat())
            self._save()
            return result
        except Exception as exc:
            attempt.update(status="failed", error_type=type(exc).__name__,
                           finished_at_utc=datetime.now(UTC).isoformat())
            record["status"] = "failed"
            self._save()
            raise


def cli_run(description: str) -> tuple[Settings, Path]:
    parser = argparse.ArgumentParser(description=description)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--run-id", default=None, help="Name under data/runs (default: default)")
    group.add_argument("--output-dir", type=Path, help="Separate directory for this complete run")
    args = parser.parse_args()
    run_id = args.run_id or "default"
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}", run_id):
        parser.error("run-id must use 1-80 letters, digits, underscores or hyphens")
    settings = replace(load_settings(), llm_provider="mock", model_name="mock",
                       refresh_source=False, refresh_test_set=False)
    root = args.output_dir or settings.paths.project_dir / "data" / "runs" / run_id
    return settings, root
