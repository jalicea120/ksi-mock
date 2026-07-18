variable "name_prefix" {
  type = string
}

variable "resource_group_name" {
  type = string
}

variable "location" {
  type = string
}

variable "log_analytics_workspace_id" {
  type = string
}

variable "container_apps_subnet_id" {
  description = "Delegated subnet for the Container Apps environment."
  type        = string
}

variable "workload_identity_id" {
  description = "Resource ID of the user-assigned managed identity the app runs as."
  type        = string
}

variable "tags" {
  type = map(string)
}
