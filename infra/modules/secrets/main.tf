# Secrets -> SVC-ASM (automating secret management).
# Key Vault with RBAC authorization, purge protection, public access OFF, reached
# only through a private endpoint (KSI-IAM least privilege + KSI-CNA minimal
# attack surface). Holds one key with an automated rotation policy and one
# synthetic secret.
#
# Because the vault is private-endpoint-only, its data plane is unreachable from
# an external (GitHub-hosted) CI runner, and under RBAC the deploy principal has
# no data-plane rights by default. The key, secret, and the deployer's data-plane
# role grant are therefore gated behind var.seed_kv_objects (default false):
#   - pipeline apply -> seed_kv_objects = false : vault + PE + RBAC only
#   - in-network apply (self-hosted runner / VPN, principal able to grant KV RBAC)
#     -> seed_kv_objects = true : also creates the key + secret

data "azurerm_client_config" "current" {}

resource "azurerm_key_vault" "main" {
  name                = "${var.name_prefix}kv${var.suffix}"
  resource_group_name = var.resource_group_name
  location            = var.location
  tenant_id           = data.azurerm_client_config.current.tenant_id

  sku_name                   = "standard"
  purge_protection_enabled   = true
  soft_delete_retention_days = 7

  rbac_authorization_enabled    = true
  public_network_access_enabled = false

  network_acls {
    default_action = "Deny"
    bypass         = "AzureServices"
  }

  tags = var.tags
}

# Private DNS + endpoint for the vault (Azure Government suffix).
resource "azurerm_private_dns_zone" "kv" {
  name                = "privatelink.vaultcore.usgovcloudapi.net"
  resource_group_name = var.resource_group_name
  tags                = var.tags
}

resource "azurerm_private_dns_zone_virtual_network_link" "kv" {
  name                  = "${var.name_prefix}-kv-link"
  resource_group_name   = var.resource_group_name
  private_dns_zone_name = azurerm_private_dns_zone.kv.name
  virtual_network_id    = var.vnet_id
  tags                  = var.tags
}

resource "azurerm_private_endpoint" "kv" {
  name                = "${var.name_prefix}-kv-pe"
  resource_group_name = var.resource_group_name
  location            = var.location
  subnet_id           = var.private_endpoint_subnet_id
  tags                = var.tags

  private_service_connection {
    name                           = "vault"
    private_connection_resource_id = azurerm_key_vault.main.id
    subresource_names              = ["vault"]
    is_manual_connection           = false
  }

  private_dns_zone_group {
    name                 = "vault"
    private_dns_zone_ids = [azurerm_private_dns_zone.kv.id]
  }
}

# --- Data-plane objects (gated; require in-network access, see header) ---

# Give the deploying principal data-plane access under RBAC so it can create the
# key/secret. Creating this assignment needs roleAssignments/write on the vault,
# so the deploy principal must be elevated beyond plain Contributor when seeding.
resource "azurerm_role_assignment" "deployer_kv_admin" {
  count                = var.seed_kv_objects ? 1 : 0
  scope                = azurerm_key_vault.main.id
  role_definition_name = "Key Vault Administrator"
  principal_id         = data.azurerm_client_config.current.object_id
}

# Key with an automated rotation policy (the SVC-ASM signal).
resource "azurerm_key_vault_key" "rotating" {
  count        = var.seed_kv_objects ? 1 : 0
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

  depends_on = [azurerm_role_assignment.deployer_kv_admin]
}

# Synthetic secret - placeholder value only, never real credentials.
resource "azurerm_key_vault_secret" "synthetic" {
  count        = var.seed_kv_objects ? 1 : 0
  name         = "synthetic-example"
  key_vault_id = azurerm_key_vault.main.id
  value        = "placeholder-not-a-real-secret"

  depends_on = [azurerm_role_assignment.deployer_kv_admin]
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
