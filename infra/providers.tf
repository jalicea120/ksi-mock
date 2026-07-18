terraform {
  required_version = ">= 1.6"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
    # azapi lets us create Key Vault keys/secrets through the ARM control plane,
    # so a private-endpoint-only vault can still be seeded from CI (no data-plane
    # reachability or data-plane RBAC needed - just control-plane Contributor).
    azapi = {
      source  = "Azure/azapi"
      version = "~> 2.0"
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

  # Storage data-plane operations authenticate with Entra ID, not account keys
  # (shared keys are disabled on the mock storage account). The deploy principal
  # needs a Storage Blob Data role on the RG for this to succeed.
  storage_use_azuread = true
}

provider "azapi" {
  environment = "usgovernment"
  use_oidc    = true
}
