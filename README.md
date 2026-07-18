# KSI Evidence Mock

A disposable "evidence surface" on **Azure Government** that gives every FedRAMP 20x
**Key Security Indicator (KSI)** a live target to measure, plus read-only collectors and an
assertion engine that computes KSI assertions and writes Security Decision Record (SDR)-shaped JSON.

> This is **not** a real product and is unrelated to any client engagement. Synthetic data only.
> KSIs track FedRAMP Consolidated Rules **v2026.07.06.01** (provisional preview, not final guidance).

## Layers

1. **Mock workload** - minimal Azure Gov footprint (Terraform IaC) touching every KSI family.
2. **Collectors** (read-only) - Azure Resource Graph, Microsoft Graph, Azure Policy + Defender assessments, Log Analytics / Sentinel, GitHub REST.
3. **Assertion engine** - `engine/assert.py` reads `engine/map.yaml`, runs mapped collectors, computes a boolean per indicator, writes `out/sdr/<run-id>.json` validated against the CR26 schema.

## Layout

```
infra/        Terraform (azurerm, Azure Government, OIDC + remote state)
collectors/   arg/ graph/ defender_policy/ sentinel/ github/
engine/       map.yaml, assert.py, schema/
out/sdr/      generated evidence + assertions (gitignored)
scripts/      deploy.sh, teardown.sh, run_assertions.sh
.github/      workflows: ci.yml (PR gate), deploy.yml, assertions.yml (scheduled drift)
```

## Coverage (46 indicators)

- **Auto (31)** - fully computed from config/telemetry.
- **Hybrid (10)** - tool evidence + human review.
- **Manual (5)** - process/organizational; explicit manual assertion, `review_required: true`.

## Quick start

```bash
# 1. Auth to Azure Government
az cloud set --name AzureUSGovernment
az login

# 2. Dry-run the engine (no Azure calls, validates map.yaml + schema wiring)
python engine/assert.py --dry-run

# 3. Deploy the mock workload (Phase 1) via pipeline, or locally:
scripts/deploy.sh

# 4. Collect evidence + compute assertions
scripts/run_assertions.sh

# 5. Tear it all down
scripts/teardown.sh
```

Auth in CI/CD is **OIDC only** - no secrets stored. See `CLAUDE.md` for the full workflow.
