"""Pass-criteria evaluators - one per automated indicator.

Single source of truth shared by the assertion engine (Phase 3) and the Trust
Center generator, so pass/fail logic is never duplicated. Each function takes the
collector's evidence rows and returns a bool. ``evaluate`` returns None for
indicators that have no automated check yet (staged), so callers can distinguish
"not measured" from "measured and failing" - we never fabricate a pass.
"""

from __future__ import annotations

from collections.abc import Callable


def _truthy(value: object) -> bool:
    return value in (True, 1, "1", "true", "True")


def ksi_piy_giv(rows: list[dict]) -> bool:
    # Authoritative inventory returns resources on demand.
    return len(rows) > 0


def ksi_cna_mat(rows: list[dict]) -> bool:
    # No publicly-exposed surface in the offering.
    return len(rows) == 0


def ksi_iam_snu(rows: list[dict]) -> bool:
    # At least one managed identity available for secretless workload auth.
    return len(rows) >= 1


def ksi_mla_osm(rows: list[dict]) -> bool:
    # A Sentinel-onboarded workspace is present.
    return len(rows) >= 1


def ksi_svc_sin(rows: list[dict]) -> bool:
    # Every storage account: TLS 1.2 minimum and HTTPS-only.
    return len(rows) >= 1 and all(
        row.get("minimum_tls_version") == "TLS1_2" and _truthy(row.get("https_only"))
        for row in rows
    )


def ksi_svc_asm(rows: list[dict]) -> bool:
    # Every Key Vault: purge protection on and public network access disabled.
    return len(rows) >= 1 and all(
        _truthy(row.get("purge_protection"))
        and row.get("public_network_access") == "Disabled"
        for row in rows
    )


CHECKS: dict[str, Callable[[list[dict]], bool]] = {
    "KSI-PIY-GIV": ksi_piy_giv,
    "KSI-CNA-MAT": ksi_cna_mat,
    "KSI-IAM-SNU": ksi_iam_snu,
    "KSI-MLA-OSM": ksi_mla_osm,
    "KSI-SVC-SIN": ksi_svc_sin,
    "KSI-SVC-ASM": ksi_svc_asm,
}


def evaluate(indicator: str, rows: list[dict]) -> bool | None:
    """Return True/False for an automated indicator, or None if not yet checkable."""
    check = CHECKS.get(indicator)
    if check is None:
        return None
    return bool(check(rows or []))
