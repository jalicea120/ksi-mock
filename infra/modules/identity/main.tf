# Identity (safe subset) -> IAM-SNU (securing non-user authentication).
# A user-assigned managed identity gives the workload a secretless, federated
# machine identity. The PIM-eligible role and Conditional Access policy that
# complete the IAM family are intentionally NOT here - they live in a separate,
# review-gated change (default-off, Conditional Access in Report-Only) because
# they can collide with existing tenant PIM/CA configuration.

resource "azurerm_user_assigned_identity" "workload" {
  name                = "${var.name_prefix}-workload-mi"
  resource_group_name = var.resource_group_name
  location            = var.location
  tags                = var.tags
}
