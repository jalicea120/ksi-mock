# Identity (safe subset) -> IAM-SNU (securing non-user authentication).
# A user-assigned managed identity gives the workload a secretless, federated
# machine identity.
#
# The rest of the IAM family is deliberately NOT pipeline-managed, to keep the CI
# principal off tenant-wide identity privileges (separation of duties, IAM-ELP):
#   - Conditional Access (IAM-APM): NOT created here. This GCC High tenant already
#     enforces MFA-for-all-users, MFA-for-admins, and block-legacy-auth; the Phase 2
#     IAM-APM collector reads those existing policies as evidence.
#   - PIM-eligible role (IAM-JIT): created operator-side, RG-scoped - an empty group
#     made ELIGIBLE (not active) for Reader on ksi-mock-rg. Kept out of Terraform so
#     CI never needs User Access Administrator or directory write.

resource "azurerm_user_assigned_identity" "workload" {
  name                = "${var.name_prefix}-workload-mi"
  resource_group_name = var.resource_group_name
  location            = var.location
  tags                = var.tags
}
