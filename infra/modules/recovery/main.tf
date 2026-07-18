# Recovery -> RPL-ABO (aligning backups with objectives).
# Geo-redundant Recovery Services vault with soft delete, plus a daily VM backup
# policy that expresses a concrete recovery objective (30-day retention).

resource "azurerm_recovery_services_vault" "main" {
  name                = "${var.name_prefix}-rsv"
  resource_group_name = var.resource_group_name
  location            = var.location
  sku                 = "Standard"
  storage_mode_type   = "GeoRedundant"
  # Soft delete is on by default (Azure secure-by-default); no explicit flag needed.
  tags = var.tags
}

resource "azurerm_backup_policy_vm" "daily" {
  name                = "${var.name_prefix}-vm-daily"
  resource_group_name = var.resource_group_name
  recovery_vault_name = azurerm_recovery_services_vault.main.name

  backup {
    frequency = "Daily"
    time      = "23:00"
  }

  retention_daily {
    count = 30
  }
}

resource "azurerm_monitor_diagnostic_setting" "rsv" {
  name                       = "to-law"
  target_resource_id         = azurerm_recovery_services_vault.main.id
  log_analytics_workspace_id = var.log_analytics_workspace_id

  enabled_log {
    category_group = "allLogs"
  }
  enabled_metric {
    category = "AllMetrics"
  }
}
