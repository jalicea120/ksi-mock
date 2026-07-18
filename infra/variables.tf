variable "location" {
  description = "Azure Government region."
  type        = string
  default     = "usgovvirginia"

  validation {
    condition     = contains(["usgovvirginia", "usgovtexas", "usgovarizona"], var.location)
    error_message = "location must be an Azure Government region."
  }
}

variable "name_prefix" {
  description = "Short prefix for resource names."
  type        = string
  default     = "ksimock"
}

variable "resource_group_name" {
  description = "Resource group for the mock workload."
  type        = string
  default     = "ksi-mock-rg"
}

variable "log_retention_days" {
  description = "Retention for the Log Analytics workspace (days)."
  type        = number
  default     = 30

  validation {
    condition     = var.log_retention_days >= 30
    error_message = "log_retention_days must be at least 30."
  }
}

variable "vnet_address_space" {
  description = "Address space for the mock VNet."
  type        = list(string)
  default     = ["10.42.0.0/16"]
}

# Key Vault uses RBAC + a private endpoint (public access off). A PE-only vault
# cannot be seeded from an external CI runner, so the rotating key + synthetic
# secret (and the deployer's data-plane role grant) are gated behind this flag.
# Leave false for pipeline applies; set true only when deploying from inside the
# VNet (self-hosted runner / VPN) with a principal that can grant KV data-plane RBAC.
variable "seed_kv_objects" {
  description = "Create the Key Vault key + secret + data-plane role grant. Requires in-network access."
  type        = bool
  default     = false
}

# Standard tag set - every resource created in Phase 1 merges these in via local.tags.
variable "tags" {
  description = "Standard tag set applied to every resource."
  type        = map(string)
  default = {
    App         = "ksi-mock"
    Environment = "dev"
    GBU         = "internal"
    ITSM        = "none"
    JobWBS      = "learning"
    Owner       = "juan.rodriguez@sbprojectlab.onmicrosoft.us"
    DeployedBy  = "Juan Alicea"
    Project     = "FR20X"
  }
}
