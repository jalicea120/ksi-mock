# Logging -> MLA family.
# Log Analytics workspace is the single sink every other module ships diagnostics
# to; Sentinel onboarding makes it the SIEM (KSI-MLA-OSM).

resource "azurerm_log_analytics_workspace" "main" {
  name                = "${var.name_prefix}-law"
  resource_group_name = var.resource_group_name
  location            = var.location
  sku                 = "PerGB2018"
  retention_in_days   = var.log_retention_days
  tags                = var.tags
}

resource "azurerm_sentinel_log_analytics_workspace_onboarding" "main" {
  workspace_id = azurerm_log_analytics_workspace.main.id
}
