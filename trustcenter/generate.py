#!/usr/bin/env python3
"""Trust Center generator.

Reads the KSI map (``engine/map.yaml``) and the latest collector evidence
(``out/evidence/*.json``), computes each indicator's status via the shared
pass-check registry (``engine/checks.py``), and renders a self-contained HTML
Trust Center from ``trustcenter/template.html`` into ``out/trustcenter/index.html``.

This is the surface the Phase 6 scheduled run republishes each cycle, so the
Trust Center reflects continuous, timestamped evidence rather than a static claim.

Usage:
    python trustcenter/generate.py                 # -> out/trustcenter/index.html
    python trustcenter/generate.py --out path.html
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from engine import results  # noqa: E402 - path set above so the shared module imports

TEMPLATE = REPO_ROOT / "trustcenter" / "template.html"
MAP = REPO_ROOT / "engine" / "map.yaml"
EVIDENCE_DIR = REPO_ROOT / "out" / "evidence"
HISTORY_PATH = REPO_ROOT / "out" / "history" / "summary.jsonl"
HISTORY_CAP = 90  # keep the trend readable - last N runs
PLACEHOLDER = '/*__TC_DATA__*/ {"generated":"","rules_version":"","indicators":[]} /*__END__*/'


def load_history(path: Path) -> list[dict]:
    """Compact trend series from a summary.jsonl (may be absent)."""
    if not path.exists():
        return []
    series = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        raw = raw.strip()
        if not raw:
            continue
        try:
            rec = json.loads(raw)
        except json.JSONDecodeError:
            continue  # skip a torn line rather than fail the whole render
        totals = rec.get("totals", {})
        series.append({
            "generated": rec.get("generated"),
            "verified": totals.get("verified"),
            "automated_total": totals.get("automated_total"),
        })
    return series[-HISTORY_CAP:]


def build_model(history_path: Path) -> dict:
    """Model from live local evidence (the operator's delegated view)."""
    spec = yaml.safe_load(MAP.read_text(encoding="utf-8"))
    evidence = results.load_evidence(EVIDENCE_DIR)
    # Shared assessment - identical status logic to the SDR engine.
    indicators = results.assess(spec, evidence)
    return {
        "generated": dt.datetime.now(dt.timezone.utc).isoformat(),
        "rules_version": spec.get("version"),
        "indicators": indicators,
        "history": load_history(history_path),
    }


def model_from_sdr(sdr: dict, history_path: Path) -> dict:
    """Model from an existing SDR (e.g. the CI-authoritative latest.json), so the
    published surface can reflect exactly what the scheduled run verified rather
    than a local delegated-token view. SDR assertions already carry every field
    the template reads (status, mode, collected_at, row_count, evidence, tool)."""
    return {
        "generated": sdr["info"]["generated"],
        "rules_version": sdr["info"].get("rules_version"),
        "indicators": sdr["assertions"],
        "history": load_history(history_path),
    }


def render(model: dict) -> str:
    template = TEMPLATE.read_text(encoding="utf-8")
    if PLACEHOLDER not in template:
        raise SystemExit("template placeholder not found - is trustcenter/template.html intact?")
    payload = json.dumps(model, default=str)
    return template.replace(PLACEHOLDER, f"/*__TC_DATA__*/ {payload} /*__END__*/")


def main() -> int:
    parser = argparse.ArgumentParser(description="Render the KSI Trust Center")
    parser.add_argument("--out", default=str(REPO_ROOT / "out" / "trustcenter" / "index.html"),
                        help="output HTML path")
    parser.add_argument("--from-sdr", metavar="PATH",
                        help="render from an SDR (e.g. the CI-authoritative latest.json) "
                             "instead of live local evidence")
    parser.add_argument("--history", metavar="PATH", default=str(HISTORY_PATH),
                        help="summary.jsonl trend series to embed")
    args = parser.parse_args()

    history_path = Path(args.history)
    if args.from_sdr:
        sdr = json.loads(Path(args.from_sdr).read_text(encoding="utf-8"))
        model = model_from_sdr(sdr, history_path)
    else:
        model = build_model(history_path)
    html = render(model)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")

    totals = results.summarize(model["indicators"])
    print(f"wrote {out_path} - {totals['verified']}/{totals['automated_total']} "
          f"automated indicators verified, {totals['total']} total")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
