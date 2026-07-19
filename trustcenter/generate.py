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
import glob
import json
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from engine import checks  # noqa: E402 - path set above so the shared module imports

TEMPLATE = REPO_ROOT / "trustcenter" / "template.html"
MAP = REPO_ROOT / "engine" / "map.yaml"
EVIDENCE_DIR = REPO_ROOT / "out" / "evidence"
PLACEHOLDER = '/*__TC_DATA__*/ {"generated":"","rules_version":"","indicators":[]} /*__END__*/'


def load_evidence() -> dict[str, dict]:
    evidence: dict[str, dict] = {}
    for path in glob.glob(str(EVIDENCE_DIR / "*.json")):
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        evidence[payload["indicator"]] = payload
    return evidence


def build_model() -> dict:
    spec = yaml.safe_load(MAP.read_text(encoding="utf-8"))
    evidence = load_evidence()

    indicators = []
    for item in spec["indicators"]:
        indicator_id = item["id"]
        payload = evidence.get(indicator_id)
        result = checks.evaluate(indicator_id, payload["rows"]) if payload else None
        status = "pending" if result is None else ("pass" if result else "fail")
        indicators.append({
            "id": indicator_id,
            "name": item["name"],
            "family": item["family"],
            "mode": item["mode"],
            "status": status,
            "pass_criteria": item.get("pass"),
            "collected_at": payload["collected_at"] if payload else None,
            "row_count": payload["row_count"] if payload else None,
            "evidence": payload["rows"][:4] if payload else None,
        })

    return {
        "generated": dt.datetime.now(dt.timezone.utc).isoformat(),
        "rules_version": spec.get("version"),
        "indicators": indicators,
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
    args = parser.parse_args()

    model = build_model()
    html = render(model)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")

    verified = sum(1 for i in model["indicators"] if i["status"] == "pass")
    automated = sum(1 for i in model["indicators"] if i["mode"] == "Auto")
    print(f"wrote {out_path} - {verified}/{automated} automated indicators verified, "
          f"{len(model['indicators'])} total")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
