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
    """Map indicator id -> latest evidence payload found in ``evidence_dir``."""
    evidence: dict[str, dict] = {}
    for path in glob.glob(str(evidence_dir / "*.json")):
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        evidence[payload["indicator"]] = payload
    return evidence


def assess_indicator(item: dict, evidence: dict[str, dict]) -> dict:
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
    }


def assess(map_doc: dict, evidence: dict[str, dict]) -> list[dict]:
    return [assess_indicator(item, evidence) for item in map_doc.get("indicators", [])]


def summarize(results: list[dict]) -> dict:
    """Headline counts. ``verified`` = Auto-mode indicators that pass (the 23/31)."""
    automated = [r for r in results if r["mode"] == "Auto"]
    return {
        "total": len(results),
        "automated_total": len(automated),
        "verified": sum(1 for r in automated if r["status"] == "pass"),
        "pass": sum(1 for r in results if r["status"] == "pass"),
        "fail": sum(1 for r in results if r["status"] == "fail"),
        "pending": sum(1 for r in results if r["status"] == "pending"),
    }
