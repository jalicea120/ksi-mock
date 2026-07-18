# Secrets -> SVC-ASM (automating secret management).
# Key Vault with RBAC authorization, purge protection, public access OFF, reached
# only through a private endpoint (KSI-IAM least privilege + KSI-CNA minimal
# attack surface). Holds one key with an automated rotation policy and one
# synthetic secret.
#
# The key + secret are created through the ARM CONTROL PLANE (azapi), not the
# vault data plane. That is what lets a private-endpoint-only vault be seeded
# from an external CI runner holding only control-plane Contributor: ARM is not
# blocked by the vault firewall and needs no data-plane RBAC. Runtime data-plane
# access (workload managed identity + Key Vault Secrets User over the private
# endpoint) is granted alongside the compute workload in a later change.

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

# Key with an automated rotation policy (the SVC-ASM signal), created via the
# ARM control plane. Key material is generated in the vault - never exposed here.
resource "azapi_resource" "signing_key" {
  type      = "Microsoft.KeyVault/vaults/keys@2023-07-01"
  name      = "${var.name_prefix}-signing-key"
  parent_id = azurerm_key_vault.main.id

  body = {
    properties = {
      kty     = "RSA"
      keySize = 2048
      keyOps  = ["sign", "verify"]
      rotationPolicy = {
        lifetimeActions = [
          {
            action  = { type = "rotate" }
            trigger = { timeBeforeExpiry = "P30D" }
          },
          {
            action  = { type = "notify" }
            trigger = { timeBeforeExpiry = "P29D" }
          },
        ]
        attributes = {
          expiryTime = "P90D"
        }
      }
    }
  }

  # azapi only accepts lowercase action types (rotate/notify), but Azure returns
  # them capitalized (Rotate/Notify) - a perpetual no-op plan diff. The rotation
  # policy is static, so ignore server-side casing drift on it.
  lifecycle {
    ignore_changes = [body.properties.rotationPolicy]
  }
}

# Synthetic secret - placeholder value only, never real credentials. The value is
# a non-sensitive placeholder, so it lives in body; a real secret would never be
# committed to IaC (it would be seeded out-of-band or via a write-only attribute).
resource "azapi_resource" "synthetic_secret" {
  type      = "Microsoft.KeyVault/vaults/secrets@2023-07-01"
  name      = "synthetic-example"
  parent_id = azurerm_key_vault.main.id

  body = {
    properties = {
      value = "placeholder-not-a-real-secret"
    }
  }
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
