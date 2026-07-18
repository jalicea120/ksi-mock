output "container_app_name" {
  description = "Name of the mock container app."
  value       = azurerm_container_app.main.name
}

output "environment_id" {
  description = "Resource ID of the Container Apps environment."
  value       = azurerm_container_app_environment.main.id
}

output "environment_default_domain" {
  description = "Internal default domain of the Container Apps environment."
  value       = azurerm_container_app_environment.main.default_domain
}
