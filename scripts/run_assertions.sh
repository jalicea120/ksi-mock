#!/usr/bin/env bash
# Run collectors + compute assertions, write SDR to out/sdr/.
set -euo pipefail

az cloud set --name AzureUSGovernment

cd "$(dirname "$0")/.."
python engine/assert.py --out out/sdr
