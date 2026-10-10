#!/usr/bin/env python3
"""FedRAMP Security Decision Record (SDR) export.

The engine's native output (``ksi-sdr/0.x``, see ``schema/ksi-sdr.schema.json``)
is this project's own run record. FedRAMP publishes a different document with
the same initials, the Security Decision Record, which is what FedRAMP tooling
such as the reference JSONViewer renders. This module converts one native run
into that shape and validates it against the vendored FedRAMP schema.

Honesty rules carry over from the engine (see CLAUDE.md non-negotiables):

  * nothing is invented - a field the engine cannot source is left empty
    (``ksiImplementation``, ``ksiAssessment``) rather than filled with prose;
  * a pending indicator gets no ``ksiImplementationStatus``, because the
    FedRAMP enum has no value for "not measured";
  * a pass that still awaits its human review is "Partially Implemented",
    never "Implemented";
  * the mock asserts KSIs only, so ``fedRampRequirements`` is an empty list.

Usage:
    python engine/fedramp_sdr.py --in out/sdr/latest.json --out out/fedramp
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

SCHEMA_DIR = Path(__file__).resolve().parent / "schema"
FEDRAMP_SDR_SCHEMA_PATH = SCHEMA_DIR / "fedramp-security-decision-record-schema-2026-06-24.json"
FEDRAMP_COMMON_SCHEMA_PATH = SCHEMA_DIR / "fedramp-common-definitions-schema-2026-06-24.json"
OUTPUT_NAME = "security-decision-record.json"

# The SDR must point at a Certification Package Overview. The mock has none, so
# the default is an unresolvable placeholder (reserved .invalid TLD); override
# with KSI_COP_URI or --cop-uri.
DEFAULT_COP_URI = "https://example.invalid/ksi-mock/certification-package-overview.json"

# Collector tool -> FedRAMP evidenceType enum value.
EVIDENCE_TYPE = {
    "arg": "Configuration",
    "arm": "Configuration",
    "graph": "Configuration",
    "defender_policy": "Policy",
    "sentinel": "Log",
    "github": "Report",
}
DEFAULT_EVIDENCE_TYPE = "Report"

ERROR_CHARS = 200
ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}")


def _validation_statements(a: dict) -> list[str]:
    """How the indicator is validated, composed only from recorded facts."""
    statements: list[str] = []
    if a.get("pass_criteria"):
        statements.append(f"Pass criterion ({a['mode']} indicator): {a['pass_criteria']}")

    source = f"the {a.get('tool')} collector ({a.get('query_ref')})"
    if a.get("error"):
        statements.append(
            f"Not measured: {source} returned an error, so the indicator is reported "
            f"as pending. Error: {a['error'][:ERROR_CHARS]}")
    elif a.get("tool") and a.get("result") is not None:
        statements.append(
            f"Measured by {source} at {a.get('collected_at')}: "
            f"{a.get('row_count')} row(s) evaluated, result {a['status']}.")
    elif a.get("tool"):
        statements.append(
            f"Evidence collected by {source} at {a.get('collected_at')} "
            f"({a.get('row_count')} row(s)), but no automated check is registered "
            f"yet; reported as pending.")
    elif a["mode"] != "Manual":
        statements.append(
            "Not measured: no collector evidence in this run; reported as pending.")

    if a.get("review_required"):
        att = a.get("attestation") or {}
        doc = f" ({att['doc']})" if att.get("doc") else ""
        if att.get("attested"):
            who = f" by {att['attestor']}" if att.get("attestor") else ""
            when = f" on {att['attested_date']}" if att.get("attested_date") else ""
            statements.append(f"Human review attested{who}{when}{doc}.")
        else:
            statements.append(f"Human review required and not yet attested{doc}.")
    return statements


def _tests(a: dict) -> list[str]:
    refs = [a.get("query_ref"), (a.get("attestation") or {}).get("doc")]
    return list(dict.fromkeys(r for r in refs if r))


def _evidence(a: dict) -> list[dict]:
    items: list[dict] = []
    rows = a.get("evidence")
    if rows:
        item = {
            "evidenceType": EVIDENCE_TYPE.get(a.get("tool"), DEFAULT_EVIDENCE_TYPE),
            "evidenceDescription": (
                f"{a.get('tool')} collector output for {a['id']}: first {len(rows)} of "
                f"{a.get('row_count')} row(s) from {a.get('query_ref')}."),
            "evidenceText": json.dumps(rows, indent=2, default=str),
        }
        if ISO_DATE.match(a.get("collected_at") or ""):
            item["lastUpdated"] = a["collected_at"][:10]
        items.append(item)

    att = a.get("attestation") or {}
    if att.get("attested"):
        item = {
            "evidenceType": "Audit Record",
            "evidenceDescription": f"Manual attestation for {a['id']} recorded in {att.get('doc')}.",
        }
        if ISO_DATE.match(str(att.get("attested_date") or "")):
            item["lastUpdated"] = str(att["attested_date"])[:10]
        items.append(item)
    return items


def _implementation_status(a: dict) -> str | None:
    if a["status"] == "fail":
        return "Not Implemented"
    if a["status"] == "pass":
        attested = (a.get("attestation") or {}).get("attested")
        if a.get("review_required") and not attested:
            return "Partially Implemented"
        return "Implemented"
    return None  # pending: deliberately omitted, see the module docstring


def _ksi(a: dict) -> dict:
    ksi: dict = {"ksiId": a["id"]}
    status = _implementation_status(a)
    if status:
        ksi["ksiImplementationStatus"] = status
    ksi.update({
        "ksiImplementation": [],
        "ksiValidation": _validation_statements(a),
        "ksiAssessment": [],
        "ksiTests": _tests(a),
        "ksiEvidence": _evidence(a),
    })
    return ksi


def to_fedramp_sdr(native: dict, cop_uri: str | None = None) -> dict:
    """Convert a native ksi-sdr run record into a FedRAMP Security Decision Record."""
    info = native["info"]
    return {
        "certificationPackageOverviewUri":
            cop_uri or os.environ.get("KSI_COP_URI") or DEFAULT_COP_URI,
        "metadata": {
            "version": info["run_id"],
            "lastUpdated": info["generated"],
            "updateSource": (
                f"ksi-mock assertion engine ({info['sdr_version']}, FedRAMP "
                f"Consolidated Rules {info.get('rules_version')})"),
        },
        "fedRampRequirements": [],
        "keySecurityIndicators": [_ksi(a) for a in native["assertions"]],
    }


def validate(doc: dict) -> list[str]:
    """Return schema-violation messages (empty means conformant)."""
    common = json.loads(FEDRAMP_COMMON_SCHEMA_PATH.read_text(encoding="utf-8"))
    schema = json.loads(FEDRAMP_SDR_SCHEMA_PATH.read_text(encoding="utf-8"))
    # The SDR schema references common-definitions by its absolute $id.
    registry = Registry().with_resource(common["$id"], Resource.from_contents(common))
    validator = Draft202012Validator(
        schema, registry=registry, format_checker=Draft202012Validator.FORMAT_CHECKER)
    return [
        f"{'/'.join(str(p) for p in err.path) or '<root>'}: {err.message}"
        for err in sorted(validator.iter_errors(doc), key=lambda e: [str(p) for p in e.path])
    ]


def write(doc: dict, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / OUTPUT_NAME
    out_path.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    return out_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Export a FedRAMP Security Decision Record")
    parser.add_argument("--in", dest="src", metavar="FILE", required=True,
                        help="native ksi-sdr run record (e.g. out/sdr/latest.json)")
    parser.add_argument("--out", metavar="DIR", required=True,
                        help=f"directory to write {OUTPUT_NAME} into")
    parser.add_argument("--cop-uri", metavar="URI",
                        help="Certification Package Overview URI (default: KSI_COP_URI or a placeholder)")
    args = parser.parse_args()

    native = json.loads(Path(args.src).read_text(encoding="utf-8"))
    doc = to_fedramp_sdr(native, args.cop_uri)
    errors = validate(doc)
    if errors:
        print("FEDRAMP SDR SCHEMA VALIDATION FAILED (not writing):", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1
    print(f"wrote FedRAMP SDR -> {write(doc, Path(args.out))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
