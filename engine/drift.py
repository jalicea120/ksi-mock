#!/usr/bin/env python3
"""SDR drift detection.

Compares the current SDR against the previous run and classifies how each
automated (Auto-mode) indicator moved:

  * regression - an indicator that was ``pass`` is no longer passing;
  * recovery   - an indicator that was not passing is now ``pass``.

Regressions are the actionable signal: the scheduled workflow files a GitHub
issue when any appear. The diff is a pure function so it is unit-testable
without a workflow; the CLI wraps it for CI.

Usage:
    python engine/drift.py --current out/sdr/latest.json \
        --previous hist/latest.json --out-md drift.md --github-output
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

WORSE = {"pass": 0, "pending": 1, "fail": 2}  # ordering for "got worse / better"


def _auto_status(sdr: dict) -> dict[str, dict]:
    """Map indicator id -> assertion, Auto-mode only."""
    return {a["id"]: a for a in sdr.get("assertions", []) if a.get("mode") == "Auto"}


def diff(previous: dict | None, current: dict) -> dict:
    """Classify Auto-indicator transitions between two SDRs."""
    curr = _auto_status(current)
    prev = _auto_status(previous) if previous else {}

    regressions, recoveries, new = [], [], []
    for ind_id, a in curr.items():
        now = a.get("status")
        before = prev.get(ind_id, {}).get("status") if ind_id in prev else None
        entry = {"id": ind_id, "name": a.get("name"), "from": before, "to": now}
        if before is None:
            if now == "pass":
                new.append(entry)
            continue
        if before == "pass" and now != "pass":
            regressions.append(entry)
        elif before != "pass" and now == "pass":
            recoveries.append(entry)

    return {
        "has_previous": previous is not None,
        "regressions": regressions,
        "recoveries": recoveries,
        "newly_verified": new,
        "current_totals": current.get("info", {}).get("totals", {}),
        "current_run_id": current.get("info", {}).get("run_id"),
        "previous_run_id": (previous or {}).get("info", {}).get("run_id"),
    }


def to_markdown(d: dict) -> str:
    """Issue body for a regression event. Assumes d['regressions'] is non-empty."""
    lines = [
        f"## KSI drift: {len(d['regressions'])} automated indicator"
        f"{'' if len(d['regressions']) == 1 else 's'} regressed",
        "",
        f"Run `{d['current_run_id']}` vs previous `{d['previous_run_id']}`.",
        "",
        "| Indicator | Was | Now |",
        "| --- | --- | --- |",
    ]
    lines += [f"| {r['id']} - {r['name']} | {r['from']} | **{r['to']}** |"
              for r in d["regressions"]]
    if d["recoveries"]:
        lines += ["", f"Also recovered: {', '.join(r['id'] for r in d['recoveries'])}."]
    t = d["current_totals"]
    if t:
        lines += ["", f"Current posture: **{t.get('verified')}/{t.get('automated_total')}** "
                  f"automated verified (pass={t.get('pass')} fail={t.get('fail')} "
                  f"pending={t.get('pending')})."]
    lines += ["", "_Filed automatically by the KSI assertions workflow._"]
    return "\n".join(lines)


def _load(path: str | None) -> dict | None:
    if not path:
        return None
    p = Path(path)
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Detect KSI SDR drift vs the previous run")
    parser.add_argument("--current", required=True, help="path to the current SDR")
    parser.add_argument("--previous", help="path to the previous SDR (optional; baseline if absent)")
    parser.add_argument("--out-md", help="write issue markdown here when regressions exist")
    parser.add_argument("--github-output", action="store_true",
                        help="append has_regressions / regression_count to $GITHUB_OUTPUT")
    args = parser.parse_args()

    current = _load(args.current)
    if current is None:
        print(f"current SDR not found: {args.current}", file=sys.stderr)
        return 1
    d = diff(_load(args.previous), current)

    n_reg, n_rec = len(d["regressions"]), len(d["recoveries"])
    if not d["has_previous"]:
        print("no previous SDR - baseline run, no drift computed.")
    else:
        print(f"drift: {n_reg} regression(s), {n_rec} recovery(ies), "
              f"{len(d['newly_verified'])} newly verified.")
        for r in d["regressions"]:
            print(f"  REGRESSED {r['id']}: {r['from']} -> {r['to']}")
        for r in d["recoveries"]:
            print(f"  recovered {r['id']}: {r['from']} -> {r['to']}")

    if args.out_md and n_reg:
        Path(args.out_md).write_text(to_markdown(d), encoding="utf-8")
        print(f"wrote issue markdown -> {args.out_md}")

    gh_out = os.environ.get("GITHUB_OUTPUT")
    if args.github_output and gh_out:
        with open(gh_out, "a", encoding="utf-8") as fh:
            fh.write(f"has_regressions={'true' if n_reg else 'false'}\n")
            fh.write(f"regression_count={n_reg}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
