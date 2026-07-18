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
import sys
import uuid
from collections import Counter
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

ENGINE_DIR = Path(__file__).resolve().parent
REPO_ROOT = ENGINE_DIR.parent
MAP_PATH = ENGINE_DIR / "map.yaml"
SCHEMA_PATH = ENGINE_DIR / "schema" / "fedramp-consolidated-rules.schema.json"

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


def write_pending_sdr(doc: dict, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    run_id = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
    sdr = {
        "info": {
            "run_id": run_id,
            "generated": dt.datetime.now(dt.timezone.utc).isoformat(),
            "rules_version": doc.get("version"),
            "status": "pending-collectors",
            "note": "Phase 0 placeholder: collectors not yet implemented. No result asserted.",
        },
        "assertions": [
            {
                "id": ind["id"],
                "name": ind["name"],
                "family": ind["family"],
                "mode": ind["mode"],
                "result": None,
                "review_required": bool(ind.get("review_required", False)),
                "evidence": None,
            }
            for ind in doc.get("indicators", [])
        ],
    }
    out_path = out_dir / f"{run_id}.json"
    out_path.write_text(json.dumps(sdr, indent=2), encoding="utf-8")
    return out_path


def main() -> int:
    parser = argparse.ArgumentParser(description="KSI assertion engine")
    parser.add_argument("--dry-run", action="store_true",
                        help="validate map + schema wiring; run no collectors")
    parser.add_argument("--out", metavar="DIR",
                        help="write an SDR to DIR (Phase 0: pending placeholder)")
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
        out_path = write_pending_sdr(doc, Path(args.out))
        print(f"wrote pending SDR -> {out_path}")
        return 0

    print("nothing to do (pass --dry-run or --out DIR).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
