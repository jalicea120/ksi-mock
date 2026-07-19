#!/usr/bin/env python3
"""Manual attestation collector (READ-ONLY).

Turns the human attestation docs (``docs/manual/*.md``) into machine-readable
evidence, in the same shape as the live collectors. Each doc carries YAML
frontmatter (``attested``, ``attestor``, ``attested_date``, ``review_cadence``,
``next_review_due``); this reads it and emits an evidence payload per indicator.

Attestations are written to a ``manual/`` subdirectory of the evidence dir so
they never collide with a Hybrid indicator's automated-leg evidence (which lives
at ``<evidence>/<indicator>.json``). The engine reads both: the automated leg
drives status, the attestation adds the human-sign-off record.

No fabricated sign-off: an attestation is only "attested" if the doc says so.

Usage:
    python collectors/manual/runner.py --out out/evidence
    python collectors/manual/runner.py KSI-CED-RAT
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DOCS_DIR = REPO_ROOT / "docs" / "manual"
FIELDS = ("attested", "attestor", "role", "attested_date",
          "review_cadence", "next_review_due", "evidence_refs")


def _frontmatter(md_path: Path) -> dict:
    text = md_path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        raise ValueError(f"{md_path.name}: no YAML frontmatter")
    _, fm, _body = text.split("---", 2)
    data = yaml.safe_load(fm) or {}
    if not isinstance(data, dict):
        raise ValueError(f"{md_path.name}: frontmatter is not a mapping")
    return data


def run(indicator: str) -> dict:
    md_path = DOCS_DIR / f"{indicator.lower()}.md"
    evidence = {
        "indicator": indicator,
        "tool": "manual",
        "query_ref": f"docs/manual/{indicator.lower()}.md",
        "collected_at": dt.datetime.now(dt.timezone.utc).isoformat(),
    }
    try:
        fm = _frontmatter(md_path)
        row = {k: fm.get(k) for k in FIELDS}
        row["attested"] = bool(fm.get("attested"))
        evidence["row_count"] = 1
        evidence["rows"] = [row]
    except Exception as exc:  # keep the batch going; record the fault as evidence
        evidence["error"] = str(exc)
        evidence["row_count"] = 0
        evidence["rows"] = []
    return evidence


def main() -> int:
    parser = argparse.ArgumentParser(description="Manual attestation collector")
    parser.add_argument("indicators", nargs="*",
                        help="indicator ids (default: every doc in docs/manual)")
    parser.add_argument("--out", metavar="DIR",
                        help="write evidence to DIR/manual/<indicator>.json")
    args = parser.parse_args()

    indicators = args.indicators or [p.stem.upper() for p in sorted(DOCS_DIR.glob("*.md"))]
    if not indicators:
        print("no attestation docs found in docs/manual", file=sys.stderr)
        return 1

    out_dir = (Path(args.out) / "manual") if args.out else None
    if out_dir:
        out_dir.mkdir(parents=True, exist_ok=True)

    attested = 0
    for indicator in indicators:
        evidence = run(indicator)
        signed = bool(evidence.get("rows") and evidence["rows"][0].get("attested"))
        attested += signed
        err = evidence.get("error")
        state = "attested" if signed else ("ERROR " + err[:80] if err else "awaiting attestation")
        print(f"{indicator}: {state}")
        if out_dir:
            (out_dir / f"{indicator.lower()}.json").write_text(
                json.dumps(evidence, indent=2, default=str), encoding="utf-8")
    print(f"attestations signed: {attested}/{len(indicators)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
