"""Identifier redaction for published outputs.

This repository and its workflow artifacts are public, while collector evidence
carries the tenant's own identifiers (subscription, tenant, principal and client
ids, request ids). Everything that leaves the runner - the SDR, the FedRAMP
export, the Trust Center - passes its evidence through ``redact`` first.

Every GUID becomes a stable placeholder derived from a hash of the original, so
the same id reads the same across rows, files and runs and evidence stays
correlatable, without publishing the id itself. Redaction is applied AFTER the
pass-checks run: checks compare against real ids (e.g. the built-in Owner role).
Raw evidence in ``out/evidence/`` is left untouched for local debugging and is
never uploaded.

Out of scope: resource names and IP addresses are not redacted.
"""

from __future__ import annotations

import hashlib
import re

PLACEHOLDER_PREFIX = "00000000-0000-0000-0000-"
_GUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.IGNORECASE)


def _placeholder(match: re.Match) -> str:
    guid = match.group(0).lower()
    if guid.startswith(PLACEHOLDER_PREFIX):
        return guid  # already redacted - keep redaction idempotent
    return PLACEHOLDER_PREFIX + hashlib.sha256(guid.encode()).hexdigest()[:12]


def redact(value):
    """Return ``value`` with every GUID in its strings replaced (deep, non-mutating)."""
    if isinstance(value, str):
        return _GUID.sub(_placeholder, value)
    if isinstance(value, list):
        return [redact(v) for v in value]
    if isinstance(value, dict):
        return {k: redact(v) for k, v in value.items()}
    return value
