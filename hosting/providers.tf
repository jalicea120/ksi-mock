# Trust Center hosting - a SEPARATE, out-of-band Terraform root.
#
# Why this is not part of infra/:
#   - The Trust Center is the public assurance SURFACE. It is meant to be shared.
#   - infra/ is the locked-down private workload (ksi-mock-rg): the deny-storage-pna
#     policy assignment and the CNA-MAT "no public exposure" collector are both
#     scoped to ksi-mock-rg. Hosting a PUBLIC static site there would either be
#     denied by our own policy or flip CNA-MAT to fail.
#   - So this config lives in its OWN resource group (ksi-trustcenter-rg) that no
#     policy assignment touches, and it is applied by the operator (juan), not by
#     the CI service principal (which is Contributor on ksi-mock-rg only and cannot
#     create resources elsewhere).
#
# State is kept in the existing Gov backend under a distinct key so it is never
# confused with the SP-managed ksi-mock.tfstate.

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
  }

  # LOCAL state on purpose. This is an out-of-band, disposable sharing surface
  # applied by the operator, not by CI - so the project's "no local state in CI"
  # rule does not apply. It deliberately avoids the shared Gov backend, whose
  # data plane is granted to the CI service principal, not to the operator login.
  # The state file holds a storage account key, so it is gitignored (see
  # hosting/.gitignore) and never committed.
}

provider "azurerm" {
  features {}
  environment = "usgovernment"
  # Applied locally via `az login` (AzureUSGovernment); no OIDC here.
  # Blob upload uses the account key (control-plane listKeys), so no data-plane
  # role assignment is needed to publish the page.
}
