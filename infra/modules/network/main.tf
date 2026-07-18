# Network -> CNA-RNT / CNA-ULN / CNA-RVP.
# Logical segmentation (VNet + subnets), a default-deny NSG on the workload
# subnet, and a dedicated subnet for private endpoints. NSG diagnostics ship to
# Log Analytics so rule-hit evidence is queryable.

resource "azurerm_virtual_network" "main" {
  name                = "${var.name_prefix}-vnet"
  resource_group_name = var.resource_group_name
  location            = var.location
  address_space       = var.vnet_address_space
  tags                = var.tags
}

resource "azurerm_subnet" "workload" {
  name                 = "workload"
  resource_group_name  = var.resource_group_name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = [cidrsubnet(var.vnet_address_space[0], 8, 1)]
}

resource "azurerm_subnet" "private_endpoints" {
  name                 = "private-endpoints"
  resource_group_name  = var.resource_group_name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = [cidrsubnet(var.vnet_address_space[0], 8, 2)]

  private_endpoint_network_policies = "Disabled"
}

# Default-deny inbound on the workload subnet. Azure's implicit rules already
# deny arbitrary inbound, but an explicit lowest-priority deny makes the posture
# assertable (KSI-CNA-RNT) rather than implicit.
resource "azurerm_network_security_group" "workload" {
  name                = "${var.name_prefix}-workload-nsg"
  resource_group_name = var.resource_group_name
  location            = var.location
  tags                = var.tags

  security_rule {
    name                       = "deny-all-inbound"
    priority                   = 4096
    direction                  = "Inbound"
    access                     = "Deny"
    protocol                   = "*"
    source_port_range          = "*"
    destination_port_range     = "*"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }
}

resource "azurerm_subnet_network_security_group_association" "workload" {
  subnet_id                 = azurerm_subnet.workload.id
  network_security_group_id = azurerm_network_security_group.workload.id
}

resource "azurerm_monitor_diagnostic_setting" "nsg" {
  name                       = "to-law"
  target_resource_id         = azurerm_network_security_group.workload.id
  log_analytics_workspace_id = var.log_analytics_workspace_id

  enabled_log {
    category = "NetworkSecurityGroupEvent"
  }

  enabled_log {
    category = "NetworkSecurityGroupRuleCounter"
  }
}
