# KSI mock workload - Phase 1 resources land here.
#
# Planned footprint (plan section 6), one live target per KSI family:
#   - Compute:    Container App or Function App                -> CNA, CMT
#   - Identity:   Entra app reg + managed identity + PIM + CA  -> IAM
#   - Secrets:    Key Vault + secret + rotation policy         -> SVC-ASM
#   - Data:       Storage account, TLS-only, CMK / infra enc   -> SVC-SIN
#   - Logging:    Log Analytics + Sentinel + diag settings     -> MLA
#   - Governance: FedRAMP High initiative + custom deny policy -> CNA/SVC/MLA-EVC
#   - Posture:    Defender for Cloud on the subscription       -> CNA/SVC/SCR
#   - Recovery:   Recovery Services vault + backup policy       -> RPL
#   - Network:    VNet + subnets + NSGs + private endpoints     -> CNA-RNT/ULN/RVP
#
# Nothing is deployed in Phase 0. The plan for these resources is reported for
# review before any apply (plan section 13, step 5).

locals {
  tags = var.tags
}
