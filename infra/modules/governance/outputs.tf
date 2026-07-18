output "fedramp_high_assignment_id" {
  description = "Resource ID of the FedRAMP High (audit-only) assignment."
  value       = azurerm_resource_group_policy_assignment.fedramp_high.id
}

output "deny_storage_policy_definition_id" {
  description = "Resource ID of the custom deny policy definition."
  value       = azurerm_policy_definition.deny_storage_public_network.id
}
