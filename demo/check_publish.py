"""Read-only checks for the explicit demo publication list; never prints secrets."""
from __future__ import annotations

import argparse
from pathlib import Path, PurePosixPath
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
LIST = ROOT / "demo/publish_files.txt"
PATTERNS = (
    rb"sk-(?:or-v1-|proj-|svcacct-)?[A-Za-z0-9_-]{24,}",
    rb"AIza[A-Za-z0-9_-]{30,}",
    rb"gh[pousr]_[A-Za-z0-9]{30,}",
    rb"github_pat_[A-Za-z0-9_]{30,}",
    rb"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----",
)


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, stderr=subprocess.PIPE)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--staged", action="store_true", help="Inspect staged bytes, not working files")
    args = parser.parse_args()
    allowed = {line.strip() for line in LIST.read_text(encoding="utf-8").splitlines()
               if line.strip() and not line.startswith("#")}
    errors = []
    if git("branch", "--show-current").decode().strip() != "khoi":
        errors.append("Current branch must be khoi.")
    names = allowed
    if args.staged:
        names = set(git("diff", "--cached", "--name-only", "-z").decode().strip("\0").split("\0")) - {""}
        if not names:
            errors.append("Nothing is staged.")
        for name in sorted(names - allowed):
            errors.append(f"Staged path is outside the publication list: {name}")
        changed = set(git("diff", "HEAD", "--name-only", "-z", "--", *sorted(allowed)).decode().strip("\0").split("\0")) - {""}
        untracked = set(git("ls-files", "--others", "--exclude-standard", "-z", "--", *sorted(allowed)).decode().strip("\0").split("\0")) - {""}
        for name in sorted((changed | untracked) - names):
            errors.append(f"Required changed/new file is not staged: {name}")
        # Read the complete proposed publication from the index, including files
        # unchanged since HEAD. This also catches new required files hidden by
        # a global ignore rule and therefore missing from ls-files --others.
        names = allowed | names

    # Also compare against configured local secrets, including nonstandard tokens.
    # Values are never logged, even on a failed check.
    known = []
    for env_path in (ROOT / ".env", ROOT.parent / ".env"):
        if env_path.is_file():
            for line in env_path.read_bytes().splitlines():
                key, sep, value = line.lstrip(b"# ").partition(b"=")
                if sep and any(marker in key.upper() for marker in (b"API_KEY", b"TOKEN", b"SECRET", b"PASSWORD")):
                    value = value.strip().strip(b"\"'")
                    if len(value) >= 12:
                        known.append(value)
    total = 0
    for name in sorted(names):
        path = ROOT / name
        rel = PurePosixPath(name)
        if (rel.is_absolute() or ".." in rel.parts or path.is_symlink()
                or not path.resolve().is_relative_to(ROOT)
                or any(p in {".git", ".venv", "__pycache__", "runtime"} for p in rel.parts)
                or (rel.name.startswith(".env") and rel.name != ".env.example")
                or rel.suffix.lower() in {".pem", ".key", ".p12", ".pfx"}):
            errors.append(f"Disallowed path: {name}")
            continue
        try:
            data = git("show", ":" + name) if args.staged else path.read_bytes()
        except (OSError, subprocess.CalledProcessError):
            errors.append(f"Cannot read required file: {name}")
            continue
        total += len(data)
        if any(re.search(pattern, data) for pattern in PATTERNS) or any(key in data for key in known):
            errors.append(f"Possible credential/private key: {name} (value redacted)")
        if len(data) > 50 * 1024 * 1024:
            errors.append(f"File exceeds this demo's 50 MiB review threshold: {name}")
        if args.staged and path.is_file() and data != path.read_bytes():
            errors.append(f"Staged bytes differ from reviewed working file: {name}; check line endings and re-add")
    if git("ls-files", "--", ".env").strip():
        errors.append(".env is tracked; ignoring it does not remove it from Git history.")
    if errors:
        print("FAIL")
        for error in errors:
            print("-", error)
        return 1
    print(f"PASS: {len(names)} files, {total:,} bytes; no configured secret or credential pattern detected.")
    print("Scope: listed working files" if not args.staged else "Scope: staged files, required changes and byte equality")
    print("This is a heuristic check, not a full Git-history or personal-data audit. Review the diff before committing.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
