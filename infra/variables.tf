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
