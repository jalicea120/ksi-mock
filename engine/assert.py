#!/usr/bin/env python3
"""KSI assertion engine.

Phase 0 scope: load and validate ``engine/map.yaml``, confirm the CR26 schema
parses as a valid JSON Schema, and support a ``--dry-run`` used by the CI gate.

Real collector execution and boolean computation land in Phases 2-4. Until then
``--out`` writes an honest "pending" SDR: no indicator is ever asserted ``true``
without collector evidence (see CLAUDE.md non-negotiables).
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
import sys
import uuid
from collections import Counter
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

ENGINE_DIR = Path(__file__).resolve().parent
REPO_ROOT = ENGINE_DIR.parent
sys.path.insert(0, str(REPO_ROOT))

from engine import results  # noqa: E402 - path set above so the shared module imports

MAP_PATH = ENGINE_DIR / "map.yaml"
SCHEMA_PATH = ENGINE_DIR / "schema" / "fedramp-consolidated-rules.schema.json"
SDR_VERSION = "ksi-sdr/0.1"

# Collector runners, in dependency-free order. Each is invoked as a subprocess
# with --out EVIDENCE_DIR; per-indicator errors are captured by the runners
# themselves, so a whole-runner failure only warns and never aborts the batch.
COLLECTORS = (
    "collectors/arg/runner.py",
    "collectors/graph/runner.py",
    "collectors/github/runner.py",
    "collectors/sentinel/runner.py",
)

REQUIRED_FIELDS = ("id", "name", "family", "mode", "collectors", "pass", "evidence")
VALID_MODES = {"Auto", "Hybrid", "Manual"}
VALID_TOOLS = {"arg", "graph", "defender_policy", "sentinel", "github", "manual"}
EXPECTED_MODE_COUNTS = {"Auto": 31, "Hybrid": 10, "Manual": 5}
EXPECTED_TOTAL = 46


def load_map() -> dict:
    with MAP_PATH.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def validate_map(doc: dict) -> list[str]:
    """Return a list of hard errors (empty means the map is well-formed)."""
    errors: list[str] = []
    indicators = (doc or {}).get("indicators")
    if not isinstance(indicators, list) or not indicators:
        return ["map.yaml has no 'indicators' list"]

    seen_ids: set[str] = set()
    for i, ind in enumerate(indicators):
        where = ind.get("id", f"index {i}") if isinstance(ind, dict) else f"index {i}"
        if not isinstance(ind, dict):
            errors.append(f"{where}: indicator is not a mapping")
            continue
        for field in REQUIRED_FIELDS:
            if field not in ind or ind[field] in (None, ""):
                errors.append(f"{where}: missing required field '{field}'")
        if ind.get("id") in seen_ids:
            errors.append(f"{where}: duplicate id")
        seen_ids.add(ind.get("id"))
        if ind.get("mode") not in VALID_MODES:
            errors.append(f"{where}: invalid mode {ind.get('mode')!r}")
        collectors = ind.get("collectors")
        if not isinstance(collectors, list) or not collectors:
            errors.append(f"{where}: 'collectors' must be a non-empty list")
            continue
        for col in collectors:
            if not isinstance(col, dict) or "tool" not in col:
                errors.append(f"{where}: collector missing 'tool'")
            elif col["tool"] not in VALID_TOOLS:
                errors.append(f"{where}: invalid tool {col['tool']!r}")
        if ind.get("mode") == "Manual" and ind.get("review_required") is not True:
            errors.append(f"{where}: Manual indicator must set review_required: true")
    return errors


def summarize(doc: dict) -> Counter:
    return Counter(ind.get("mode") for ind in doc.get("indicators", []))


def check_schema() -> list[str]:
    if not SCHEMA_PATH.exists():
        return [f"schema not found at {SCHEMA_PATH}"]
    try:
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
    except Exception as exc:  # noqa: BLE001 - dry-run reports any schema fault as one error
        return [f"schema invalid: {exc}"]
    return []


def missing_refs(doc: dict) -> list[str]:
    """Non-Manual collector refs that do not yet exist on disk (informational)."""
    missing = []
    for ind in doc.get("indicators", []):
        for col in ind.get("collectors", []):
            if col.get("tool") == "manual":
                continue
            ref = col.get("ref")
            if ref and not (REPO_ROOT / ref).exists():
                missing.append(ref)
    return missing


def collect(evidence_dir: Path) -> None:
    """Run every collector runner into ``evidence_dir`` (best-effort)."""
    evidence_dir.mkdir(parents=True, exist_ok=True)
    for rel in COLLECTORS:
        runner = REPO_ROOT / rel
        if not runner.exists():
            continue
        print(f"collect: {rel}")
        proc = subprocess.run(
            [sys.executable, str(runner), "--out", str(evidence_dir)],
            cwd=str(REPO_ROOT), text=True, capture_output=True,
        )
        for line in (proc.stdout or "").splitlines():
            print(f"  {line}")
        if proc.returncode != 0:
            # A runner-level failure (e.g. no az login) degrades to Pending for
            # its indicators; it must not abort the whole assertion run.
            print(f"  WARN {rel} exited {proc.returncode}: "
                  f"{(proc.stderr or '').strip()[:160]}", file=sys.stderr)


def build_sdr(doc: dict, assessed: list[dict]) -> dict:
    run_id = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
    return {
        "info": {
            "sdr_version": SDR_VERSION,
            "run_id": run_id,
            "generated": dt.datetime.now(dt.timezone.utc).isoformat(),
            "rules_version": doc.get("version"),
            "subscription": os.environ.get("AZURE_SUBSCRIPTION_ID"),
            "totals": results.summarize(assessed),
        },
        "assertions": assessed,
    }


def write_sdr(sdr: dict, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{sdr['info']['run_id']}.json"
    out_path.write_text(json.dumps(sdr, indent=2, default=str), encoding="utf-8")
    latest = out_dir / "latest.json"
    latest.write_text(json.dumps(sdr, indent=2, default=str), encoding="utf-8")
    return out_path


def main() -> int:
    parser = argparse.ArgumentParser(description="KSI assertion engine")
    parser.add_argument("--dry-run", action="store_true",
                        help="validate map + schema wiring; run no collectors")
    parser.add_argument("--out", metavar="DIR",
                        help="run collectors, compute results, write an SDR to DIR")
    parser.add_argument("--evidence-dir", metavar="DIR",
                        default=str(REPO_ROOT / "out" / "evidence"),
                        help="where collector evidence is read/written")
    parser.add_argument("--skip-collect", action="store_true",
                        help="assert from existing evidence without re-running collectors")
    args = parser.parse_args()

    doc = load_map()
    errors = validate_map(doc)
    errors += check_schema()
    counts = summarize(doc)
    total = sum(counts.values())

    print(f"map.yaml: {total} indicators "
          f"(Auto={counts.get('Auto', 0)}, Hybrid={counts.get('Hybrid', 0)}, "
          f"Manual={counts.get('Manual', 0)})")

    if total != EXPECTED_TOTAL:
        errors.append(f"expected {EXPECTED_TOTAL} indicators, found {total}")
    for mode, want in EXPECTED_MODE_COUNTS.items():
        if counts.get(mode, 0) != want:
            errors.append(f"expected {want} {mode} indicators, found {counts.get(mode, 0)}")

    if errors:
        print("VALIDATION FAILED:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1

    pending = missing_refs(doc)
    if pending:
        print(f"note: {len(pending)} collector ref(s) not yet implemented "
              f"(expected during Phase 0-2).")

    if args.dry_run:
        print("dry-run OK: map + schema valid.")
        return 0

    if args.out:
        evidence_dir = Path(args.evidence_dir)
        if not args.skip_collect:
            collect(evidence_dir)
        evidence = results.load_evidence(evidence_dir)
        assessed = results.assess(doc, evidence)
        sdr = build_sdr(doc, assessed)
        out_path = write_sdr(sdr, Path(args.out))
        t = sdr["info"]["totals"]
        print(f"wrote SDR -> {out_path}")
        print(f"assertions: {t['verified']}/{t['automated_total']} automated verified "
              f"(pass={t['pass']} fail={t['fail']} pending={t['pending']}) over {t['total']} indicators")
        return 0

    print("nothing to do (pass --dry-run or --out DIR).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
