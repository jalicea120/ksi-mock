#!/usr/bin/env bash
# Disposable: remove everything the mock deployed.
set -euo pipefail

az cloud set --name AzureUSGovernment

cd "$(dirname "$0")/../infra"
terraform init -input=false
terraform destroy -input=false
