output "location" {
  description = "Azure Government region the workload targets."
  value       = var.location
}

output "resource_group_name" {
  description = "Resource group name for the mock workload."
  value       = var.resource_group_name
}
