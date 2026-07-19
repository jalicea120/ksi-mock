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


def ksi_cna_rnt(rows: list[dict]) -> bool:
    # Every NSG carries at least one inbound Deny rule (explicit default-deny).
    return len(rows) >= 1 and all(int(row.get("inbound_deny_rules") or 0) >= 1 for row in rows)


def ksi_cna_uln(rows: list[dict]) -> bool:
    # A VNet with real segmentation (>= 2 subnets).
    return len(rows) >= 1 and all(int(row.get("subnet_count") or 0) >= 2 for row in rows)


def ksi_svc_vcm(rows: list[dict]) -> bool:
    # Service-to-service traffic uses private endpoints.
    return len(rows) >= 1


def ksi_rpl_abo(rows: list[dict]) -> bool:
    # At least one backup policy is defined in the vault.
    return len(rows) >= 1


def ksi_cna_dfp(rows: list[dict]) -> bool:
    # At least one policy assignment governs the resource group.
    return len(rows) >= 1


_OWNER_ROLE_ID = "8e3af657-a8ff-443c-a75c-2fe8c4bcb635"


def ksi_iam_elp(rows: list[dict]) -> bool:
    # Access is explicitly scoped and no assignment grants Owner at the RG.
    return len(rows) >= 1 and not any(
        str(row.get("role_definition_id", "")).lower().endswith(_OWNER_ROLE_ID)
        for row in rows
    )


def ksi_iam_apm(rows: list[dict]) -> bool:
    # At least one ENABLED Conditional Access policy requires MFA or an
    # authentication strength (phishing-resistant) - passwordless/strong-MFA posture.
    for policy in rows:
        if policy.get("state") != "enabled":
            continue
        grant = policy.get("grantControls") or {}
        controls = [str(c).lower() for c in (grant.get("builtInControls") or [])]
        if "mfa" in controls or grant.get("authenticationStrength"):
            return True
    return False


def ksi_iam_sus(rows: list[dict]) -> bool:
    # At least one ENABLED risk-based Conditional Access policy (sign-in or user
    # risk) that responds to suspicious activity automatically.
    for policy in rows:
        if policy.get("state") != "enabled":
            continue
        conditions = policy.get("conditions") or {}
        if conditions.get("signInRiskLevels") or conditions.get("userRiskLevels"):
            return True
    return False


def ksi_iam_jit(rows: list[dict]) -> bool:
    # At least one PIM-eligible (not standing) role assignment.
    return len(rows) >= 1


def ksi_svc_eis(rows: list[dict]) -> bool:
    # A Defender secure score is being computed (the improvement-evaluation loop).
    return len(rows) >= 1


def ksi_cna_ibp(rows: list[dict]) -> bool:
    # Best-practice assessments are produced and healthy findings outnumber unhealthy.
    healthy = sum(1 for row in rows if row.get("status") == "Healthy")
    unhealthy = sum(1 for row in rows if row.get("status") == "Unhealthy")
    return (healthy + unhealthy) >= 1 and healthy > unhealthy


def ksi_cna_eis(rows: list[dict]) -> bool:
    # At least one policy assignment is actively enforced (not audit-only).
    return any(row.get("enforcement_mode") == "Default" for row in rows)


CHECKS: dict[str, Callable[[list[dict]], bool]] = {
    "KSI-PIY-GIV": ksi_piy_giv,
    "KSI-CNA-MAT": ksi_cna_mat,
    "KSI-IAM-SNU": ksi_iam_snu,
    "KSI-MLA-OSM": ksi_mla_osm,
    "KSI-SVC-SIN": ksi_svc_sin,
    "KSI-SVC-ASM": ksi_svc_asm,
    "KSI-CNA-RNT": ksi_cna_rnt,
    "KSI-CNA-ULN": ksi_cna_uln,
    "KSI-SVC-VCM": ksi_svc_vcm,
    "KSI-RPL-ABO": ksi_rpl_abo,
    "KSI-CNA-DFP": ksi_cna_dfp,
    "KSI-IAM-ELP": ksi_iam_elp,
    "KSI-IAM-APM": ksi_iam_apm,
    "KSI-IAM-SUS": ksi_iam_sus,
    "KSI-IAM-JIT": ksi_iam_jit,
    "KSI-SVC-EIS": ksi_svc_eis,
    "KSI-CNA-IBP": ksi_cna_ibp,
    "KSI-CNA-EIS": ksi_cna_eis,
}


def evaluate(indicator: str, rows: list[dict]) -> bool | None:
    """Return True/False for an automated indicator, or None if not yet checkable."""
    check = CHECKS.get(indicator)
    if check is None:
        return None
    return bool(check(rows or []))
