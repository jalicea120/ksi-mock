#!/usr/bin/env python3
"""Microsoft Graph collectors (READ-ONLY), Azure Government (graph.microsoft.us).

Each indicator has a small JSON spec (a Graph endpoint + optional query params).
The runner GETs it (following @odata.nextLink), and returns structured evidence
in the same shape as the ARG collectors.

Resilient by design: a permission or availability error is captured per collector
as ``error`` with ``rows: []`` - so one failure never breaks the batch, and the
engine treats it as "not measured" rather than fabricating a fail. Identity data
is tenant-scoped (there is no resource group for Conditional Access / PIM), which
is the agreed "read existing tenant controls" evidence model.
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
from urllib.parse import urlencode

import requests
from azure.identity import AzureCliCredential

GRAPH = "https://graph.microsoft.us"
ARM = "https://management.usgovcloudapi.net"
GRAPH_DIR = Path(__file__).resolve().parent

_CRED = AzureCliCredential()
_TOKENS: dict[str, str] = {}


def _token(scope: str) -> str:
    if scope not in _TOKENS:
        _TOKENS[scope] = _CRED.get_token(scope).token
    return _TOKENS[scope]


def _subscription_id() -> str:
    sub = os.environ.get("AZURE_SUBSCRIPTION_ID")
    if sub:
        return sub
    az = shutil.which("az") or "az"
    return subprocess.check_output(
        [az, "account", "show", "--query", "id", "-o", "tsv"], text=True).strip()


def _get_all(url: str, headers: dict) -> list:
    rows: list = []
    while url:
        response = requests.get(url, headers=headers, timeout=60)
        if response.status_code >= 400:
            raise RuntimeError(f"HTTP {response.status_code}: {response.text[:200]}")
        body = response.json()
        rows.extend(body.get("value", []))
        url = body.get("@odata.nextLink")
    return rows


def run(indicator: str) -> dict:
    spec = json.loads((GRAPH_DIR / f"{indicator.lower()}.json").read_text(encoding="utf-8"))
    api = spec.get("api", "graph")          # "graph" (default) or "arm"
    base = ARM if api == "arm" else GRAPH
    evidence = {
        "indicator": indicator,
        "tool": api,
        "query_ref": f"collectors/graph/{indicator.lower()}.json",
        "collected_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "graph_url": spec["graph_url"],
    }
    try:
        path = spec["graph_url"].replace("{subscription}", _subscription_id()) \
            if "{subscription}" in spec["graph_url"] else spec["graph_url"]
        url = base + path
        params = spec.get("params")
        if params:
            url += ("&" if "?" in url else "?") + urlencode(params)
        rows = _get_all(url, {"Authorization": f"Bearer {_token(f'{base}/.default')}"})
        evidence["row_count"] = len(rows)
        evidence["rows"] = rows
    except Exception as exc:  # keep the batch going; record the fault as evidence
        evidence["error"] = str(exc)
        evidence["row_count"] = 0
        evidence["rows"] = []
    return evidence


def main() -> int:
    parser = argparse.ArgumentParser(description="Microsoft Graph collectors")
    parser.add_argument("indicators", nargs="*", help="indicator ids (default: all specs)")
    parser.add_argument("--out", metavar="DIR", help="write evidence to DIR/<indicator>.json")
    args = parser.parse_args()

    indicators = args.indicators or [p.stem.upper() for p in sorted(GRAPH_DIR.glob("*.json"))]
    if not indicators:
        print("no graph collector specs found", file=sys.stderr)
        return 1

    out_dir = Path(args.out) if args.out else None
    if out_dir:
        out_dir.mkdir(parents=True, exist_ok=True)

    for indicator in indicators:
        evidence = run(indicator)
        err = evidence.get("error")
        print(f"{indicator}: {evidence['row_count']} row(s)" + (f"  ERROR {err[:90]}" if err else ""))
        if out_dir:
            (out_dir / f"{indicator.lower()}.json").write_text(
                json.dumps(evidence, indent=2, default=str), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
