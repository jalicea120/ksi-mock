output "workspace_id" {
  description = "Resource ID of the Log Analytics workspace (diagnostics sink)."
  value       = azurerm_log_analytics_workspace.main.id
}

output "workspace_name" {
  value = azurerm_log_analytics_workspace.main.name
}
