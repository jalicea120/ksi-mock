output "primary_web_endpoint" {
  description = "Public HTTPS URL of the hosted Trust Center."
  value       = azurerm_storage_account.tc.primary_web_endpoint
}

output "storage_account_name" {
  description = "Name of the hosting storage account."
  value       = azurerm_storage_account.tc.name
}

output "resource_group_name" {
  description = "Resource group holding the hosting surface."
  value       = azurerm_resource_group.tc.name
}
