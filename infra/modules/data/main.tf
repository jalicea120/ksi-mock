# Data -> SVC-SIN (securing information) + CNA-MAT/RNT (minimal attack surface).
# Storage account: TLS 1.2 only, infrastructure (double) encryption, no shared
# keys, public network access off, reached only through a private endpoint.

resource "azurerm_storage_account" "main" {
  name                = "${var.name_prefix}st${var.suffix}"
  resource_group_name = var.resource_group_name
  location            = var.location

  account_tier             = "Standard"
  account_replication_type = "LRS"
  account_kind             = "StorageV2"

  min_tls_version                   = "TLS1_2"
  https_traffic_only_enabled        = true
  infrastructure_encryption_enabled = true
  shared_access_key_enabled         = false
  public_network_access_enabled     = false
  allow_nested_items_to_be_public   = false

  tags = var.tags
}

# Blob-service diagnostics (read/write/delete) -> Log Analytics (KSI-MLA-LET).
resource "azurerm_monitor_diagnostic_setting" "blob" {
  name                       = "to-law"
  target_resource_id         = "${azurerm_storage_account.main.id}/blobServices/default"
  log_analytics_workspace_id = var.log_analytics_workspace_id

  enabled_log {
    category = "StorageRead"
  }
  enabled_log {
    category = "StorageWrite"
  }
  enabled_log {
    category = "StorageDelete"
  }
  enabled_metric {
    category = "Transaction"
  }
}

# Private DNS + endpoint for the blob service (Azure Government suffix).
resource "azurerm_private_dns_zone" "blob" {
  name                = "privatelink.blob.core.usgovcloudapi.net"
  resource_group_name = var.resource_group_name
  tags                = var.tags
}

resource "azurerm_private_dns_zone_virtual_network_link" "blob" {
  name                  = "${var.name_prefix}-blob-link"
  resource_group_name   = var.resource_group_name
  private_dns_zone_name = azurerm_private_dns_zone.blob.name
  virtual_network_id    = var.vnet_id
  tags                  = var.tags
}

resource "azurerm_private_endpoint" "blob" {
  name                = "${var.name_prefix}-st-blob-pe"
  resource_group_name = var.resource_group_name
  location            = var.location
  subnet_id           = var.private_endpoint_subnet_id
  tags                = var.tags

  private_service_connection {
    name                           = "blob"
    private_connection_resource_id = azurerm_storage_account.main.id
    subresource_names              = ["blob"]
    is_manual_connection           = false
  }

  private_dns_zone_group {
    name                 = "blob"
    private_dns_zone_ids = [azurerm_private_dns_zone.blob.id]
  }
}
