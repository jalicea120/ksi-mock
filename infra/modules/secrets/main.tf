# Secrets -> SVC-ASM (automating secret management).
# Key Vault with soft-delete + purge protection, holding one key with an
# automated rotation policy and one synthetic secret. Access-policy mode is used
# (not RBAC) so the deploying principal - which holds Contributor, a control-plane
# role - can create the key/secret without a separate data-plane role grant.
# A production offering would use RBAC + a scoped data-plane role instead.

data "azurerm_client_config" "current" {}

resource "azurerm_key_vault" "main" {
  name                = "${var.name_prefix}kv${var.suffix}"
  resource_group_name = var.resource_group_name
  location            = var.location
  tenant_id           = data.azurerm_client_config.current.tenant_id

  sku_name                   = "standard"
  purge_protection_enabled   = true
  soft_delete_retention_days = 7

  # Reachable from the deploy runner for data-plane key/secret creation; a real
  # offering would place this behind a private endpoint and default-deny ACLs.
  public_network_access_enabled = true

  network_acls {
    default_action = "Allow"
    bypass         = "AzureServices"
  }

  access_policy {
    tenant_id = data.azurerm_client_config.current.tenant_id
    object_id = data.azurerm_client_config.current.object_id

    key_permissions = [
      "Get", "List", "Create", "Update", "GetRotationPolicy", "SetRotationPolicy",
    ]
    secret_permissions = [
      "Get", "List", "Set", "Delete",
    ]
  }

  tags = var.tags
}

# Key with an automated rotation policy (the SVC-ASM signal).
resource "azurerm_key_vault_key" "rotating" {
  name         = "${var.name_prefix}-signing-key"
  key_vault_id = azurerm_key_vault.main.id
  key_type     = "RSA"
  key_size     = 2048
  key_opts     = ["sign", "verify"]

  rotation_policy {
    automatic {
      time_before_expiry = "P30D"
    }
    expire_after         = "P90D"
    notify_before_expiry = "P29D"
  }
}

# Synthetic secret - placeholder value only, never real credentials.
resource "azurerm_key_vault_secret" "synthetic" {
  name         = "synthetic-example"
  key_vault_id = azurerm_key_vault.main.id
  value        = "placeholder-not-a-real-secret"
}

resource "azurerm_monitor_diagnostic_setting" "kv" {
  name                       = "to-law"
  target_resource_id         = azurerm_key_vault.main.id
  log_analytics_workspace_id = var.log_analytics_workspace_id

  enabled_log {
    category = "AuditEvent"
  }
  enabled_metric {
    category = "AllMetrics"
  }
}
