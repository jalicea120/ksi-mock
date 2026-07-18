variable "name_prefix" {
  type = string
}

variable "resource_group_id" {
  description = "Resource ID of the workload resource group (assignment scope)."
  type        = string
}

variable "location" {
  description = "Region for the policy assignment's managed identity."
  type        = string
}

variable "fedramp_initiative_display_name" {
  description = "Display name of the built-in FedRAMP initiative to assign."
  type        = string
  default     = "FedRAMP High"
}
