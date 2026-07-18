terraform {
  required_version = ">= 1.6"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
  }

  # Remote state in Azure Government Storage (bootstrapped in tfstate-rg).
  # For local validation without the backend: terraform init -backend=false
  backend "azurerm" {
    resource_group_name  = "tfstate-rg"
    storage_account_name = "ksimocktf11f0ed46"
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
