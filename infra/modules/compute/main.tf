# Compute -> CNA (cloud-native workload) + CMT (change via revisions).
# An internal-only Azure Container Apps environment (no public ingress),
# VNet-integrated on a delegated subnet, running the mock app under the workload
# user-assigned managed identity (secretless). Console/system logs flow to the
# Log Analytics workspace through the environment (KSI-MLA-LET). The Consumption
# workload profile scales to zero, so idle cost is ~0.

resource "azurerm_container_app_environment" "main" {
  name                = "${var.name_prefix}-aca-env"
  resource_group_name = var.resource_group_name
  location            = var.location

  log_analytics_workspace_id     = var.log_analytics_workspace_id
  infrastructure_subnet_id       = var.container_apps_subnet_id
  internal_load_balancer_enabled = true

  workload_profile {
    name                  = "Consumption"
    workload_profile_type = "Consumption"
    maximum_count         = 1
    minimum_count         = 0
  }

  tags = var.tags
}

resource "azurerm_container_app" "main" {
  name                         = "${var.name_prefix}-app"
  resource_group_name          = var.resource_group_name
  container_app_environment_id = azurerm_container_app_environment.main.id
  revision_mode                = "Single"
  workload_profile_name        = "Consumption"
  tags                         = var.tags

  identity {
    type         = "UserAssigned"
    identity_ids = [var.workload_identity_id]
  }

  template {
    min_replicas = 0
    max_replicas = 1

    container {
      name   = "app"
      image  = "mcr.microsoft.com/k8se/quickstart:latest"
      cpu    = 0.25
      memory = "0.5Gi"
    }
  }

  # Internal ingress only: reachable within the VNet, never from the internet
  # (KSI-CNA-MAT minimal attack surface).
  ingress {
    external_enabled = false
    target_port      = 80
    transport        = "auto"

    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }
}
