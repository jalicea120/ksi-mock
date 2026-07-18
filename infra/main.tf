# KSI mock workload - Phase 1 foundation.
#
# This file wires the resource group + the "safe" foundation modules (no PIM/CA).
# Governance/posture, compute, and the gated identity (PIM + Conditional Access)
# resources land in later, separately reviewed changes. See plan sections 5-6.
#
# Every module receives the Log Analytics workspace id and emits its own
# diagnostic settings there, so telemetry coverage is uniform (KSI-MLA-LET).

locals {
  tags = var.tags

  # Short, deterministic suffix keeps globally-unique names (storage, key vault)
  # stable across applies without hand-set values.
  suffix = random_string.suffix.result
}

resource "random_string" "suffix" {
  length  = 6
  lower   = true
  upper   = false
  numeric = true
  special = false
}

resource "azurerm_resource_group" "main" {
  name     = var.resource_group_name
  location = var.location
  tags     = local.tags
}

# One-time reconciliation of resources that exist in Azure but not in state, so
# apply adopts them instead of failing on "already exists". Both are idempotent
# (a no-op once the resource is in state) and are removed after a clean apply.
#   - ksi-mock-rg: created out-of-band before this remote state existed.
#   - storage account: created by the previous apply, which then failed its
#     post-create data-plane poll, so it exists in Azure but never reached state.
data "azurerm_subscription" "current" {}

import {
  to = azurerm_resource_group.main
  id = "${data.azurerm_subscription.current.id}/resourceGroups/${var.resource_group_name}"
}

import {
  to = module.data.azurerm_storage_account.main
  id = "${data.azurerm_subscription.current.id}/resourceGroups/${var.resource_group_name}/providers/Microsoft.Storage/storageAccounts/${var.name_prefix}st${local.suffix}"
}

module "logging" {
  source = "./modules/logging"

  name_prefix         = var.name_prefix
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  log_retention_days  = var.log_retention_days
  tags                = local.tags
}

module "network" {
  source = "./modules/network"

  name_prefix                = var.name_prefix
  resource_group_name        = azurerm_resource_group.main.name
  location                   = azurerm_resource_group.main.location
  vnet_address_space         = var.vnet_address_space
  log_analytics_workspace_id = module.logging.workspace_id
  tags                       = local.tags
}

module "data" {
  source = "./modules/data"

  name_prefix                = var.name_prefix
  suffix                     = local.suffix
  resource_group_name        = azurerm_resource_group.main.name
  location                   = azurerm_resource_group.main.location
  vnet_id                    = module.network.vnet_id
  private_endpoint_subnet_id = module.network.private_endpoint_subnet_id
  log_analytics_workspace_id = module.logging.workspace_id
  tags                       = local.tags
}

module "secrets" {
  source = "./modules/secrets"

  name_prefix                = var.name_prefix
  suffix                     = local.suffix
  resource_group_name        = azurerm_resource_group.main.name
  location                   = azurerm_resource_group.main.location
  vnet_id                    = module.network.vnet_id
  private_endpoint_subnet_id = module.network.private_endpoint_subnet_id
  log_analytics_workspace_id = module.logging.workspace_id
  tags                       = local.tags
}

module "identity" {
  source = "./modules/identity"

  name_prefix         = var.name_prefix
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  tags                = local.tags
}

module "recovery" {
  source = "./modules/recovery"

  name_prefix                = var.name_prefix
  resource_group_name        = azurerm_resource_group.main.name
  location                   = azurerm_resource_group.main.location
  log_analytics_workspace_id = module.logging.workspace_id
  tags                       = local.tags
}
