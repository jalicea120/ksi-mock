#!/usr/bin/env python3
"""GitHub REST collectors (READ-ONLY) via the gh CLI.

The repo's own DevOps signals - Actions run history, deployment history, security
features - become KSI evidence (change management, supply chain). Uses ``gh api``
so it authenticates both locally (gh login) and in CI (GITHUB_TOKEN). Per-collector
error capture keeps one failure from breaking the batch.

Each indicator has a JSON spec: a ``gh_api`` endpoint (``{repo}`` substituted) and
an optional ``jq`` projection that yields the evidence rows.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

GH_DIR = Path(__file__).resolve().parent


def _gh() -> str:
    return shutil.which("gh") or "gh"


def _repo() -> str:
    return subprocess.check_output(
        [_gh(), "repo", "view", "--json", "nameWithOwner", "--jq", ".nameWithOwner"],
        text=True).strip()


def run(indicator: str, repo: str) -> dict:
    spec = json.loads((GH_DIR / f"{indicator.lower()}.json").read_text(encoding="utf-8"))
    endpoint = spec["gh_api"].replace("{repo}", repo)
    evidence = {
        "indicator": indicator,
        "tool": "github",
        "query_ref": f"collectors/github/{indicator.lower()}.json",
        "collected_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "gh_api": endpoint,
    }
    try:
        cmd = [_gh(), "api", endpoint]
        if spec.get("jq"):
            cmd += ["--jq", spec["jq"]]
        # Some endpoints (Dependabot alerts) need a scoped PAT the default
        # GITHUB_TOKEN lacks. A spec may name a token_env; if that env is set we
        # run this call under it, else we fall back to the ambient GH_TOKEN
        # (which 403s -> honest Pending, never a fabricated pass).
        env = None
        tok_env = spec.get("token_env")
        if tok_env and os.environ.get(tok_env):
            env = {**os.environ, "GH_TOKEN": os.environ[tok_env]}
        result = subprocess.run(cmd, capture_output=True, text=True, env=env)
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip()[:200])
        parsed = json.loads(result.stdout) if result.stdout.strip() else []
        rows = parsed if isinstance(parsed, list) else [parsed]
        evidence["row_count"] = len(rows)
        evidence["rows"] = rows
    except Exception as exc:  # keep the batch going; record the fault as evidence
        evidence["error"] = str(exc)
        evidence["row_count"] = 0
        evidence["rows"] = []
    return evidence


def main() -> int:
    parser = argparse.ArgumentParser(description="GitHub REST collectors")
    parser.add_argument("indicators", nargs="*", help="indicator ids (default: all specs)")
    parser.add_argument("--out", metavar="DIR", help="write evidence to DIR/<indicator>.json")
    args = parser.parse_args()

    indicators = args.indicators or [p.stem.upper() for p in sorted(GH_DIR.glob("*.json"))]
    if not indicators:
        print("no github collector specs found", file=sys.stderr)
        return 1

    repo = _repo()
    out_dir = Path(args.out) if args.out else None
    if out_dir:
        out_dir.mkdir(parents=True, exist_ok=True)

    for indicator in indicators:
        evidence = run(indicator, repo)
        err = evidence.get("error")
        print(f"{indicator}: {evidence['row_count']} row(s)" + (f"  ERROR {err[:90]}" if err else ""))
        if out_dir:
            (out_dir / f"{indicator.lower()}.json").write_text(
                json.dumps(evidence, indent=2, default=str), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
