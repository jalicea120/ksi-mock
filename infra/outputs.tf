output "location" {
  description = "Azure Government region the workload targets."
  value       = var.location
}

output "resource_group_name" {
  description = "Resource group name for the mock workload."
  value       = azurerm_resource_group.main.name
}

output "log_analytics_workspace_id" {
  description = "Diagnostics sink every module ships to."
  value       = module.logging.workspace_id
}

output "storage_account_name" {
  description = "Mock storage account (globally-unique name)."
  value       = module.data.storage_account_name
}

output "key_vault_name" {
  description = "Mock Key Vault (globally-unique name)."
  value       = module.secrets.key_vault_name
}

output "workload_identity_client_id" {
  description = "Client id of the workload managed identity."
  value       = module.identity.workload_identity_client_id
}
