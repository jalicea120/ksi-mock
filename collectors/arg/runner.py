#!/usr/bin/env python3
"""Azure Resource Graph collectors (READ-ONLY).

Runs the ``.kql`` query bound to a KSI indicator against Azure Resource Graph
(Azure Government) and returns structured evidence: the raw result rows plus a
``collected_at`` UTC timestamp and source metadata.

There is deliberately NO pass/fail logic here. Collectors observe; the assertion
engine (Phase 3) computes the boolean from this evidence. The timestamped,
machine-readable shape is what the scheduled runs and the Trust Center consume.

Usage:
    python collectors/arg/runner.py                 # run every .kql in this dir
    python collectors/arg/runner.py KSI-SVC-SIN      # run one indicator
    python collectors/arg/runner.py --out out/evidence
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

from azure.identity import AzureCliCredential
from azure.mgmt.resourcegraph import ResourceGraphClient
from azure.mgmt.resourcegraph.models import QueryRequest, QueryRequestOptions

ARG_DIR = Path(__file__).resolve().parent
GOV_ARM = "https://management.usgovcloudapi.net"


def _client() -> ResourceGraphClient:
    # AzureCliCredential reuses the operator's `az login` (already set to the Gov
    # cloud), and in CI azure/login provides the same context.
    cred = AzureCliCredential()
    return ResourceGraphClient(
        credential=cred,
        base_url=GOV_ARM,
        credential_scopes=[f"{GOV_ARM}/.default"],
    )


def _subscription_id() -> str:
    sub = os.environ.get("AZURE_SUBSCRIPTION_ID")
    if sub:
        return sub
    # Resolve az explicitly - on Windows it is az.cmd, which a bare "az" in
    # subprocess cannot find.
    az = shutil.which("az") or "az"
    return subprocess.check_output(
        [az, "account", "show", "--query", "id", "-o", "tsv"], text=True
    ).strip()


def run(indicator: str, client: ResourceGraphClient, subscription_id: str) -> dict:
    """Run one indicator's query and return its evidence payload."""
    kql_path = ARG_DIR / f"{indicator.lower()}.kql"
    query = kql_path.read_text(encoding="utf-8")

    rows: list = []
    skip_token = None
    while True:
        options = QueryRequestOptions(result_format="objectArray", skip_token=skip_token)
        request = QueryRequest(subscriptions=[subscription_id], query=query, options=options)
        response = client.resources(request)
        rows.extend(response.data or [])
        skip_token = response.skip_token
        if not skip_token:
            break

    return {
        "indicator": indicator,
        "tool": "arg",
        "query_ref": f"collectors/arg/{indicator.lower()}.kql",
        "collected_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "subscription": subscription_id,
        "row_count": len(rows),
        "rows": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Azure Resource Graph collectors")
    parser.add_argument("indicators", nargs="*",
                        help="indicator ids (default: every .kql in this dir)")
    parser.add_argument("--out", metavar="DIR",
                        help="write each evidence payload to DIR/<indicator>.json")
    args = parser.parse_args()

    indicators = args.indicators or [p.stem.upper() for p in sorted(ARG_DIR.glob("*.kql"))]
    if not indicators:
        print("no .kql collectors found", file=sys.stderr)
        return 1

    client = _client()
    subscription = _subscription_id()
    out_dir = Path(args.out) if args.out else None
    if out_dir:
        out_dir.mkdir(parents=True, exist_ok=True)

    for indicator in indicators:
        evidence = run(indicator, client, subscription)
        print(f"{indicator}: {evidence['row_count']} row(s) @ {evidence['collected_at']}")
        if out_dir:
            target = out_dir / f"{indicator.lower()}.json"
            target.write_text(json.dumps(evidence, indent=2, default=str), encoding="utf-8")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
