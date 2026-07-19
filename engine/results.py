"""Shared assessment: evidence + map -> per-indicator results.

Single source of truth for turning collector evidence into a status, used by
BOTH the assertion engine (``assert.py`` -> SDR) and the Trust Center generator,
so the two never disagree. Pass/fail logic itself lives in ``engine.checks``;
this module only wires evidence to indicators and applies the honesty rules:

  * a collector that errored (missing permission / absent table) is "not
    measured" -> Pending, never a fabricated fail;
  * an indicator with no registered check is Pending (staged), not a pass.
"""

from __future__ import annotations

import glob
import json
from pathlib import Path

from engine import checks

SAMPLE_ROWS = 4


def load_evidence(evidence_dir: Path) -> dict[str, dict]:
    """Map indicator id -> latest evidence payload found in ``evidence_dir``.

    Only the top level is scanned; manual attestations live one level down in
    ``manual/`` (see load_attestations) so they never collide with a Hybrid
    indicator's automated-leg evidence at ``<evidence>/<indicator>.json``."""
    evidence: dict[str, dict] = {}
    for path in glob.glob(str(evidence_dir / "*.json")):
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        evidence[payload["indicator"]] = payload
    return evidence


def load_attestations(evidence_dir: Path) -> dict[str, dict]:
    """Map indicator id -> manual attestation evidence (``<evidence>/manual/``)."""
    attestations: dict[str, dict] = {}
    for path in glob.glob(str(evidence_dir / "manual" / "*.json")):
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        attestations[payload["indicator"]] = payload
    return attestations


def _attestation(payload: dict | None) -> dict | None:
    """Compact attestation sub-record from a manual collector payload."""
    if not payload or payload.get("error") or not payload.get("rows"):
        return None
    row = payload["rows"][0]
    return {
        "attested": bool(row.get("attested")),
        "attestor": row.get("attestor") or None,
        "attested_date": row.get("attested_date") or None,
        "review_cadence": row.get("review_cadence") or None,
        "next_review_due": row.get("next_review_due") or None,
        "doc": payload.get("query_ref"),
        "collected_at": payload.get("collected_at"),
    }


def assess_indicator(item: dict, evidence: dict[str, dict],
                     attestations: dict[str, dict] | None = None) -> dict:
    indicator_id = item["id"]
    payload = evidence.get(indicator_id)
    errored = bool(payload and payload.get("error"))
    usable = payload if (payload and not errored) else None
    result = checks.evaluate(indicator_id, usable["rows"]) if usable else None
    status = "pending" if result is None else ("pass" if result else "fail")
    return {
        "id": indicator_id,
        "name": item["name"],
        "family": item["family"],
        "mode": item["mode"],
        "result": result,
        "status": status,
        "review_required": bool(item.get("review_required", False)),
        "pass_criteria": item.get("pass"),
        "tool": payload.get("tool") if payload else None,
        "query_ref": payload.get("query_ref") if payload else None,
        "collected_at": payload.get("collected_at") if payload else None,
        "row_count": payload.get("row_count") if payload else None,
        "evidence": usable["rows"][:SAMPLE_ROWS] if usable else None,
        "error": payload.get("error") if errored else None,
        "attestation": _attestation((attestations or {}).get(indicator_id)),
    }


def assess(map_doc: dict, evidence: dict[str, dict],
           attestations: dict[str, dict] | None = None) -> list[dict]:
    return [assess_indicator(item, evidence, attestations)
            for item in map_doc.get("indicators", [])]


def summarize(results: list[dict]) -> dict:
    """Headline counts. ``verified`` = Auto-mode indicators that pass (the 19/31).

    Attestations are tracked separately from automated verification: an indicator
    requiring review is only ``attested`` when its doc has been signed off."""
    automated = [r for r in results if r["mode"] == "Auto"]
    reviewable = [r for r in results if r["review_required"]]
    return {
        "total": len(results),
        "automated_total": len(automated),
        "verified": sum(1 for r in automated if r["status"] == "pass"),
        "pass": sum(1 for r in results if r["status"] == "pass"),
        "fail": sum(1 for r in results if r["status"] == "fail"),
        "pending": sum(1 for r in results if r["status"] == "pending"),
        "attestable_total": len(reviewable),
        "attested": sum(1 for r in reviewable
                        if (r.get("attestation") or {}).get("attested")),
    }
