terraform {
  required_version = ">= 1.6"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
  }

  # Remote state in Azure Government Storage. Bootstrap the backend once (see scripts/
  # and CLAUDE.md / plan section 12.9), then replace storage_account_name below.
  # For local validation without the backend: terraform init -backend=false
  backend "azurerm" {
    resource_group_name  = "tfstate-rg"
    storage_account_name = "REPLACE_WITH_STATE_SA" # unique, lowercase, 3-24 chars
    container_name       = "tfstate"
    key                  = "ksi-mock.tfstate"
    environment          = "usgovernment"
    use_oidc             = true # OIDC for the backend too, in CI
    use_azuread_auth     = true # AAD/RBAC to the blob - no storage account keys
  }
}

provider "azurerm" {
  features {}
  environment = "usgovernment"
  use_oidc    = true # OIDC in CI; harmless locally when using az login
}
