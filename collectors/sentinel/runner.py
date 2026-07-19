#!/usr/bin/env python3
"""Microsoft Sentinel / Log Analytics collectors (READ-ONLY), Azure Government.

Each indicator has a ``.kql`` file run against the workspace data plane
(``api.loganalytics.us`` in Gov). Results become evidence in the same shape as
the ARG and Graph collectors: raw rows plus a ``collected_at`` UTC timestamp and
source metadata. No pass/fail logic lives here - the shared checks registry does
that.

The workspace ``customerId`` (the query-API GUID) is resolved at runtime from the
workload resource group via ARM, so nothing is hardcoded; override with
``KSI_LAW_CUSTOMER_ID`` / ``KSI_WORKLOAD_RG`` if needed.

Resilient by design: a missing table or permission error is captured per
collector as ``error`` with ``rows: []`` - one failure never breaks the batch,
and the engine treats it as "not measured" rather than fabricating a fail. In a
quiet mock, empty incident tables are an honest Pending, not a pass.

Usage:
    python collectors/sentinel/runner.py                 # run every .kql here
    python collectors/sentinel/runner.py KSI-CMT-LMC      # run one indicator
    python collectors/sentinel/runner.py --out out/evidence
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

import requests
from azure.identity import AzureCliCredential

SENTINEL_DIR = Path(__file__).resolve().parent
ARM = "https://management.usgovcloudapi.net"
LOG_ANALYTICS = "https://api.loganalytics.us"
DEFAULT_RG = "ksi-mock-rg"

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
    az = shutil.which("az") or "az"  # on Windows az is az.cmd
    return subprocess.check_output(
        [az, "account", "show", "--query", "id", "-o", "tsv"], text=True).strip()


def _workspace_customer_id() -> str:
    """The Log Analytics query-API GUID, resolved from the workload RG via ARM."""
    if os.environ.get("KSI_LAW_CUSTOMER_ID"):
        return os.environ["KSI_LAW_CUSTOMER_ID"]
    rg = os.environ.get("KSI_WORKLOAD_RG", DEFAULT_RG)
    url = (f"{ARM}/subscriptions/{_subscription_id()}/resourceGroups/{rg}/providers"
           "/Microsoft.OperationalInsights/workspaces?api-version=2022-10-01")
    response = requests.get(
        url, headers={"Authorization": f"Bearer {_token(f'{ARM}/.default')}"}, timeout=60)
    if response.status_code >= 400:
        raise RuntimeError(f"HTTP {response.status_code}: {response.text[:200]}")
    workspaces = response.json().get("value", [])
    if not workspaces:
        raise RuntimeError(f"no Log Analytics workspace found in {rg}")
    return workspaces[0]["properties"]["customerId"]


def _query(customer_id: str, kql: str) -> list[dict]:
    """Run KQL against the workspace and flatten PrimaryResult to row dicts."""
    url = f"{LOG_ANALYTICS}/v1/workspaces/{customer_id}/query"
    response = requests.post(
        url,
        headers={"Authorization": f"Bearer {_token(f'{LOG_ANALYTICS}/.default')}",
                 "Content-Type": "application/json"},
        json={"query": kql},
        timeout=120,
    )
    if response.status_code >= 400:
        raise RuntimeError(f"HTTP {response.status_code}: {response.text[:200]}")
    tables = response.json().get("tables", [])
    primary = next((t for t in tables if t.get("name") == "PrimaryResult"), tables[0] if tables else None)
    if not primary:
        return []
    columns = [c["name"] for c in primary.get("columns", [])]
    return [dict(zip(columns, row)) for row in primary.get("rows", [])]


def run(indicator: str, customer_id: str) -> dict:
    kql = (SENTINEL_DIR / f"{indicator.lower()}.kql").read_text(encoding="utf-8")
    evidence = {
        "indicator": indicator,
        "tool": "sentinel",
        "query_ref": f"collectors/sentinel/{indicator.lower()}.kql",
        "collected_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "workspace": customer_id,
    }
    try:
        rows = _query(customer_id, kql)
        evidence["row_count"] = len(rows)
        evidence["rows"] = rows
    except Exception as exc:  # keep the batch going; record the fault as evidence
        evidence["error"] = str(exc)
        evidence["row_count"] = 0
        evidence["rows"] = []
    return evidence


def main() -> int:
    parser = argparse.ArgumentParser(description="Sentinel / Log Analytics collectors")
    parser.add_argument("indicators", nargs="*",
                        help="indicator ids (default: every .kql in this dir)")
    parser.add_argument("--out", metavar="DIR",
                        help="write each evidence payload to DIR/<indicator>.json")
    args = parser.parse_args()

    indicators = args.indicators or [p.stem.upper() for p in sorted(SENTINEL_DIR.glob("*.kql"))]
    if not indicators:
        print("no .kql collectors found", file=sys.stderr)
        return 1

    customer_id = _workspace_customer_id()
    out_dir = Path(args.out) if args.out else None
    if out_dir:
        out_dir.mkdir(parents=True, exist_ok=True)

    for indicator in indicators:
        evidence = run(indicator, customer_id)
        err = evidence.get("error")
        print(f"{indicator}: {evidence['row_count']} row(s)" + (f"  ERROR {err[:90]}" if err else ""))
        if out_dir:
            (out_dir / f"{indicator.lower()}.json").write_text(
                json.dumps(evidence, indent=2, default=str), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
