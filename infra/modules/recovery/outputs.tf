output "recovery_vault_id" {
  value = azurerm_recovery_services_vault.main.id
}

output "backup_policy_id" {
  value = azurerm_backup_policy_vm.daily.id
}
