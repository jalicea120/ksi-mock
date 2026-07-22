# Public static-website host for the AGS KSI Trust Center.
# One resource group, one storage account with $web static hosting, one blob.

resource "random_string" "suffix" {
  length  = 8
  special = false
  upper   = false
  numeric = true
}

resource "azurerm_resource_group" "tc" {
  name     = var.resource_group_name
  location = var.location
  tags     = var.tags
}

# Storage account serving the static site over its public web endpoint.
# Deliberately reachable (this is the sharing surface); still hardened where it
# is free to do so: TLS 1.2 floor, HTTPS-only, no anonymous blob-container
# access (the $web endpoint serves the page without public containers).
resource "azurerm_storage_account" "tc" {
  name                = "${var.name_prefix}${random_string.suffix.result}"
  resource_group_name = azurerm_resource_group.tc.name
  location            = var.location

  account_tier             = "Standard"
  account_replication_type = "LRS"
  account_kind             = "StorageV2"

  min_tls_version                 = "TLS1_2"
  https_traffic_only_enabled      = true
  public_network_access_enabled   = true
  shared_access_key_enabled       = true
  allow_nested_items_to_be_public = false

  tags = var.tags
}

# Enable $web static hosting (the inline account block is deprecated in v4).
resource "azurerm_storage_account_static_website" "tc" {
  storage_account_id = azurerm_storage_account.tc.id
  index_document     = "index.html"
  error_404_document = "index.html"
}

# The generated, self-contained Trust Center page. content_md5 ties the blob to
# the file contents so a regenerated page is re-uploaded on the next apply.
resource "azurerm_storage_blob" "index" {
  name                   = "index.html"
  storage_account_name   = azurerm_storage_account.tc.name
  storage_container_name = "$web"
  type                   = "Block"
  content_type           = "text/html; charset=utf-8"
  source                 = var.html_source_path
  content_md5            = filemd5(var.html_source_path)

  # The $web container only exists once static hosting is enabled.
  depends_on = [azurerm_storage_account_static_website.tc]
}
