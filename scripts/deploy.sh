#!/usr/bin/env bash
# Local convenience wrapper. The pipeline (deploy.yml) is the source of truth.
set -euo pipefail

az cloud set --name AzureUSGovernment

cd "$(dirname "$0")/../infra"
terraform init -input=false
terraform fmt -check -recursive
terraform validate
terraform apply -input=false
