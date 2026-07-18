# KSI Mock - project memory

## What this is

Disposable Azure Government "evidence surface" for FedRAMP 20x KSIs.
Not a real product, and not related to any client engagement.
It is the smallest set of Azure Gov resources needed so each of the 46 KSI indicators has a live target to measure, wrapped in read-only collectors and an assertion engine that emits Security Decision Record (SDR)-shaped JSON.

Source of truth for KSIs: FedRAMP Consolidated Rules v2026.07.06.01 (provisional preview, not final guidance).
Treat all output as informational, pending review by a qualified professional.

## Non-negotiables

- Cloud: Azure Government. Always run: `az cloud set --name AzureUSGovernment`
- Endpoints: ARM `management.usgovcloudapi.net` / Graph `graph.microsoft.us` / login `login.microsoftonline.us`
- Regions: usgovvirginia / usgovtexas / usgovarizona
- Collectors are READ-ONLY. Never modify the environment from a collector.
- KSI assertions are COMPUTED from collector output. Never hard-code a result. If you cannot measure it, mark it manual/placeholder, do not fake a `true`.
- Synthetic / placeholder data only. No real or client data in the tenant.
- Disposable. Everything deploys from IaC and tears down with one script.

## Layout

- `infra/` - Terraform, azurerm provider, Gov environment
- `collectors/{arg,graph,defender_policy,sentinel,github}` - read-only evidence collectors
- `engine/{map.yaml,assert.py,schema}` - assertion engine
- `out/sdr/` - generated evidence + assertions per run (gitignored)
- `scripts/` - deploy.sh / teardown.sh / run_assertions.sh
- `.github/workflows/` - ci.yml / deploy.yml / assertions.yml

## Git & DevOps workflow (follow every time)

- Never commit directly to `main`. Create a short-lived branch: `feat/...` `fix/...` `chore/...`
- Use conventional commit messages (feat:, fix:, chore:, docs:, ci:).
- Open a PR for every change; let CI (ci.yml) pass before squash-merging. `main` is protected.
- Claude Code may use git + the gh CLI to branch, commit, push, and open/merge PRs.
- Azure auth in CI/CD is OIDC only (workload identity federation). NEVER add a client secret, password, or connection string to the repo, a workflow, or this file.
- Secrets/variables live in GitHub (repo or `dev` Environment). Only IDs are stored (AZURE_CLIENT_ID / AZURE_TENANT_ID / AZURE_SUBSCRIPTION_ID), no credentials.
- `azure/login` must set `environment: AzureUSGovernment`.
- Deploy via the pipeline (deploy.yml), not the portal. Evidence runs via assertions.yml.

## Terraform conventions

- IaC is Terraform (azurerm provider, `environment = "usgovernment"`, `use_oidc = true`).
- Remote state in Azure Storage backend (`use_azuread_auth = true`), never local state in CI.
- COMMIT `.terraform.lock.hcl`. NEVER commit `*.tfstate` (contains secrets) or a real `terraform.tfvars`.
- Local loop: `terraform fmt` -> `validate` -> `plan` -> `apply`. CI runs fmt/validate/plan; deploy runs apply.
- Pass inputs via variables + `TF_VAR_` / GitHub secrets, not hardcoded values.
- Every Azure resource carries the standard tag set: App, Environment, GBU, ITSM, JobWBS, Owner (see `infra/variables.tf`).

## Definition of done for any indicator work

- `map.yaml` entry has: collector(s), pass criteria, evidence path, mode (Auto | Hybrid | Manual).
- Auto indicators must pull real data. Manual indicators set `review_required: true`.
- SDR output validates against `engine/schema/fedramp-consolidated-rules.schema.json`.

## Coverage modes (46 indicators)

- Auto (31): config/telemetry evidence pulled by a collector; fully computable.
- Hybrid (10): tool provides evidence input, human review completes the indicator.
- Manual (5): process/organizational, no Azure signal; represent as a manual assertion with `review_required: true`.

## Reference (provisional preview - not final guidance)

- KSI + rules corpus: https://github.com/FedRAMP/2026-markdown
- Machine-readable rules: https://github.com/FedRAMP/rules
- Consolidated rules JSON: https://raw.githubusercontent.com/FedRAMP/rules/main/fedramp-consolidated-rules.json
- Schema: https://raw.githubusercontent.com/FedRAMP/rules/main/schemas/fedramp-consolidated-rules.schema.json
- Consolidated Rules version targeted: 2026.07.06.01
