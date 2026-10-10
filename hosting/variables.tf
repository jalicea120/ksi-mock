variable "location" {
  description = "Azure Government region."
  type        = string
  default     = "usgovvirginia"

  validation {
    condition     = contains(["usgovvirginia", "usgovtexas", "usgovarizona"], var.location)
    error_message = "location must be an Azure Government region."
  }
}

variable "resource_group_name" {
  description = "Resource group for the public Trust Center host (kept OUT of ksi-mock-rg)."
  type        = string
  default     = "ksi-trustcenter-rg"
}

variable "name_prefix" {
  description = "Short prefix for the hosting storage account name (a random suffix is appended)."
  type        = string
  default     = "ksitc"
}

variable "html_source_path" {
  description = "Path to the generated, self-contained Trust Center index.html to publish."
  type        = string
  default     = "../out/trustcenter/index.html"
}

# Standard 8-tag set for this project. App is distinguished so the hosting
# surface is easy to tell apart from the ksi-mock workload resources.
variable "tags" {
  description = "Standard tag set applied to every resource."
  type        = map(string)
  default = {
    App         = "ksi-trustcenter"
    Environment = "dev"
    GBU         = "internal"
    ITSM        = "none"
    JobWBS      = "learning"
    Owner       = "juan.rodriguez@sbprojectlab.onmicrosoft.us"
    DeployedBy  = "Juan Alicea"
    Project     = "FR20X"
  }
}
