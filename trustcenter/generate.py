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
import inspect
import json
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from engine import checks  # noqa: E402 - path set above so the shared module imports
from engine import results  # noqa: E402 - path set above so the shared module imports

TEMPLATE = REPO_ROOT / "trustcenter" / "template.html"
FAIL_EXAMPLES = REPO_ROOT / "trustcenter" / "fail_examples.json"
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
    attestations = results.load_attestations(EVIDENCE_DIR)
    # Shared assessment - identical status logic to the SDR engine.
    indicators = results.assess(spec, evidence, attestations)
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


def _read_ref(ref: str | None) -> str | None:
    """Return the text of a collector query/doc referenced from the map (KQL,
    Graph/GitHub JSON spec, or a manual procedure), or None if unreadable. This
    is what Assessor mode shows as the "input" leg of each validation cycle."""
    if not ref:
        return None
    path = REPO_ROOT / ref
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return None


def _load_fail_examples() -> dict:
    """Synthetic broken-evidence fixtures used to teach what a finding looks like."""
    try:
        return json.loads(FAIL_EXAMPLES.read_text(encoding="utf-8"))
    except OSError:
        return {}


def enrich_assessor(indicators: list[dict]) -> list[dict]:
    """Attach the real assertion cycle to every indicator so Assessor mode can
    render input -> assertion -> output from source, never a mockup:

      * ``collectors``   - every evidence leg declared in the map (tool + ref)
      * ``query_text``   - the primary collector query the evidence came from
      * ``check_source`` - the exact Python pass-check from ``engine/checks.py``
      * ``check_fn``     - that check's function name (its identity in the code)
      * ``fail_example`` - synthetic broken evidence run through the SAME check,
        attached only when the engine genuinely returns False, so the teaching
        "FAILED" verdict is engine-computed rather than hand-authored.

    An indicator with no registered check (staged, or Manual) simply carries no
    ``check_source``; the template renders those tracks differently."""
    spec = yaml.safe_load(MAP.read_text(encoding="utf-8"))
    by_id = {i["id"]: i for i in spec.get("indicators", [])}
    fail_examples = _load_fail_examples()
    # Full collector rows (the SDR only carries a 4-row sample). Used so Assessor
    # mode can show every evidence row in a scrollable block, not just the sample.
    full_evidence = results.load_evidence(EVIDENCE_DIR) if EVIDENCE_DIR.exists() else {}
    for x in indicators:
        item = by_id.get(x["id"], {})
        x["collectors"] = item.get("collectors", [])
        payload = full_evidence.get(x["id"])
        if payload and not payload.get("error") and payload.get("rows"):
            x["evidence_full"] = payload["rows"]
        # Prefer the query the evidence was actually collected from; fall back to
        # the first non-manual collector declared in the map for staged indicators.
        ref = x.get("query_ref")
        if not ref:
            ref = next((c.get("ref") for c in x["collectors"]
                        if c.get("tool") != "manual"), None)
        x["query_text"] = _read_ref(ref)
        x["query_ref"] = x.get("query_ref") or ref
        fn = checks.CHECKS.get(x["id"])
        if fn is not None:
            try:
                x["check_source"] = inspect.getsource(fn)
                x["check_fn"] = fn.__name__
            except (OSError, TypeError):
                x["check_source"] = None
            fex = fail_examples.get(x["id"])
            if fex is not None:
                rows = fex.get("rows", [])
                result = checks.evaluate(x["id"], rows)  # the REAL check, on broken rows
                if result is False:
                    x["fail_example"] = {
                        "rows": rows[:results.SAMPLE_ROWS],
                        "row_count": len(rows),
                        "why": fex.get("why", ""),
                    }
                else:
                    print(f"warning: fail example for {x['id']} returned {result!r}, "
                          f"not False - skipping so we never show a fabricated failure",
                          file=sys.stderr)
    return indicators


def synth_history(indicators: list[dict], generated_iso: str, days: int = 30) -> dict:
    """Deterministic synthetic history for the History tab: emulate an offering that
    has been continuously monitored for ~a month, onboarding indicators over time and
    experiencing a few failures that were then remediated back to validated.

    Everything is derived from the REAL indicator set (ids, names, families) and each
    failure's rationale reuses that indicator's engine-computed ``fail_example`` why,
    so the timeline stays consistent with what the pipeline actually asserts. It is a
    teaching/demo surface (the live offering only has days of real history), clearly
    presented as such in the UI - it never changes the headline live posture."""
    try:
        end = dt.datetime.fromisoformat(generated_iso.replace("Z", "+00:00")).date()
    except (ValueError, AttributeError):
        end = dt.datetime.now(dt.timezone.utc).date()
    dates = [end - dt.timedelta(days=days - 1 - i) for i in range(days)]

    autos = [x for x in indicators if x.get("mode") == "Auto"]
    verified = [x for x in autos if x.get("status") == "pass"]  # the currently-green Auto set
    n = max(1, len(verified) - 1)
    # Onboarding day for each verified indicator, spread across the first ~16 days.
    onboard = {x["id"]: min(days - 2, round(i * 16 / n)) for i, x in enumerate(verified)}
    # A deterministic handful get a failure window that is remediated before "now".
    failing = verified[2::4][:6]
    windows = {}
    for j, x in enumerate(failing):
        start = 17 + (j % 4) * 2          # failure begins mid/late month
        windows[x["id"]] = (start, start + 2 + (j % 3))  # remediated 2-4 days later

    events: list[dict] = []
    for x in verified:
        d = onboard[x["id"]]
        events.append({"date": dates[d].isoformat(), "day": d, "indicator": x["id"],
                       "name": x["name"], "family": x["family"], "type": "validation",
                       "from": "pending", "to": "pass",
                       "note": "Collector wired; indicator first validated from live evidence."})
    for x in failing:
        fs, fe = windows[x["id"]]
        why = (x.get("fail_example") or {}).get("why", "Evidence stopped meeting the pass criteria.")
        events.append({"date": dates[fs].isoformat(), "day": fs, "indicator": x["id"],
                       "name": x["name"], "family": x["family"], "type": "failure",
                       "from": "pass", "to": "fail", "note": why})
        events.append({"date": dates[fe].isoformat(), "day": fe, "indicator": x["id"],
                       "name": x["name"], "family": x["family"], "type": "remediation",
                       "from": "fail", "to": "pass",
                       "note": "Configuration remediated; the same assertion returns true again."})

    daily = []
    for d in range(days):
        passed = failed = 0
        for x in verified:
            status = "pending" if d < onboard[x["id"]] else "pass"
            win = windows.get(x["id"])
            if win and win[0] <= d < win[1]:
                status = "fail"
            passed += status == "pass"
            failed += status == "fail"
        daily.append({"date": dates[d].isoformat(), "verified": passed, "fail": failed,
                      "automated_total": len(autos)})

    events.sort(key=lambda e: e["day"])
    return {"daily": daily, "events": events, "automated_total": len(autos),
            "start": dates[0].isoformat(), "end": dates[-1].isoformat()}


# The template is a self-contained <style> + markup + <script> fragment (it was
# authored to be dropped into a claude.ai Artifact, which supplies the document
# skeleton at publish time). When the page is hosted as a standalone file instead,
# nothing supplies that skeleton, so we wrap it here. The <meta charset="utf-8"> is
# the essential part: a browser handed the UTF-8 bytes with no declared charset
# falls back to Windows-1252 and mojibakes every emoji/icon (and the en/em glyphs).
DOCUMENT_HEAD = (
    "<!DOCTYPE html>\n"
    "<html lang=\"en\">\n"
    "<head>\n"
    "<meta charset=\"utf-8\">\n"
    "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
    "<title>AGS KSI Trust Center</title>\n"
    "<link rel=\"icon\" href=\"data:image/svg+xml,"
    "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'>"
    "<text y='.9em' font-size='90'>%F0%9F%9B%A1</text></svg>\">\n"
    "</head>\n"
    "<body>\n"
)
DOCUMENT_TAIL = "\n</body>\n</html>\n"


def render(model: dict) -> str:
    template = TEMPLATE.read_text(encoding="utf-8")
    if PLACEHOLDER not in template:
        raise SystemExit("template placeholder not found - is trustcenter/template.html intact?")
    payload = json.dumps(model, default=str)
    body = template.replace(PLACEHOLDER, f"/*__TC_DATA__*/ {payload} /*__END__*/")
    return DOCUMENT_HEAD + body + DOCUMENT_TAIL


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
    model["indicators"] = enrich_assessor(model["indicators"])
    hist = synth_history(model["indicators"], model.get("generated", ""))
    model["history_daily"] = hist["daily"]
    model["history_events"] = hist["events"]
    model["history_window"] = {"start": hist["start"], "end": hist["end"],
                               "automated_total": hist["automated_total"]}
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
