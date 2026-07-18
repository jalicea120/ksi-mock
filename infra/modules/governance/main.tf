# Governance -> CNA/SVC/MLA-EVC.
# Two complementary controls:
#   1. Broad monitoring via the built-in FedRAMP High initiative (audit-only).
#   2. One targeted custom Deny that enforces our private-endpoint storage posture.
#
# Scope note: policy DEFINITIONS live at subscription scope (an Azure requirement),
# so the deploy principal needs "Resource Policy Contributor" at the subscription.
# ASSIGNMENTS are scoped to the workload resource group to keep blast radius small
# and teardown clean.

data "azurerm_policy_set_definition" "fedramp_high" {
  display_name = var.fedramp_initiative_display_name
}

# Custom Deny: storage accounts must not expose a public network endpoint.
# The mock storage already sets public_network_access_enabled = false, so it is
# compliant today; this makes the control explicit and enforced (KSI-CNA-RNT / SVC-SIN).
resource "azurerm_policy_definition" "deny_storage_public_network" {
  name         = "${var.name_prefix}-deny-storage-public-network"
  policy_type  = "Custom"
  mode         = "Indexed"
  display_name = "Deny storage accounts with public network access (ksi-mock)"
  description  = "Denies create/update of storage accounts whose publicNetworkAccess is Enabled."

  metadata = jsonencode({
    category = "Storage"
    source   = "ksi-mock"
  })

  policy_rule = jsonencode({
    if = {
      allOf = [
        { field = "type", equals = "Microsoft.Storage/storageAccounts" },
        { field = "Microsoft.Storage/storageAccounts/publicNetworkAccess", equals = "Enabled" }
      ]
    }
    then = {
      effect = "deny"
    }
  })
}

resource "azurerm_resource_group_policy_assignment" "deny_storage_public_network" {
  name                 = "${var.name_prefix}-deny-storage-pna"
  display_name         = "Deny storage public network access (ksi-mock)"
  resource_group_id    = var.resource_group_id
  policy_definition_id = azurerm_policy_definition.deny_storage_public_network.id

  # The single intentional enforcement point. Existing storage complies, so
  # nothing is blocked today; a future public-access storage account would be denied.
  enforce = true
}

# Broad posture monitoring: the built-in FedRAMP High initiative, audit-only.
# enforce = false (DoNotEnforce) evaluates every policy but applies no effect -
# full compliance signal, zero deploy/deny side effects. A system-assigned
# identity is attached because Azure requires one when a set contains
# DeployIfNotExists/Modify policies, even though DoNotEnforce never remediates.
resource "azurerm_resource_group_policy_assignment" "fedramp_high" {
  name                 = "${var.name_prefix}-fedramp-high"
  display_name         = "FedRAMP High (audit-only, ksi-mock)"
  resource_group_id    = var.resource_group_id
  policy_definition_id = data.azurerm_policy_set_definition.fedramp_high.id
  location             = var.location
  enforce              = false

  identity {
    type = "SystemAssigned"
  }
}
