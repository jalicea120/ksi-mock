# Trust Center hosting

Publishes the AGS KSI Trust Center as a public static website in Azure Government so
assessors can open it with just a URL.

## Why this is separate from `infra/`

The Trust Center is the public assurance surface and is meant to be shared.
`infra/` is the locked-down private workload (`ksi-mock-rg`), where the
`ksimock-deny-storage-pna` policy assignment and the `CNA-MAT` "no public exposure"
collector are both scoped to `ksi-mock-rg`.
Hosting a public site there would either be denied by our own policy or flip
`CNA-MAT` to fail.

So this root deploys into its own resource group (`ksi-trustcenter-rg`) that no
policy assignment touches.
It is applied by the operator, not by the CI service principal - the SP is
Contributor on `ksi-mock-rg` only and cannot create resources elsewhere.
Because the workflow directories (`ci.yml`, `deploy.yml`) are pinned to `infra/`,
this directory is never touched by the pipeline.

## What it creates

- Resource group `ksi-trustcenter-rg` (standard 8-tag set, `App = ksi-trustcenter`).
- A `StorageV2` account with `$web` static hosting, TLS 1.2 floor, HTTPS-only.
- One blob: `index.html`, the self-contained Trust Center page.

The data is fully synthetic and the repo is already public, so anonymous public
access is acceptable here.

## Publish / refresh

Regenerate the page from the CI-authoritative SDR, then apply:

```bash
# 1. Pull the CI SDR (19/31) + trend from the sdr-history branch
git show origin/sdr-history:latest.json   > out/_ci_latest.json
git show origin/sdr-history:summary.jsonl > out/_ci_summary.jsonl

# 2. Render the self-contained page
python trustcenter/generate.py \
  --from-sdr out/_ci_latest.json \
  --history  out/_ci_summary.jsonl \
  --out out/trustcenter/index.html

# 3. Publish (run from hosting/, authenticated to AzureUSGovernment via az login)
cd hosting
terraform init
terraform apply
```

`terraform output primary_web_endpoint` prints the URL to share.

## Teardown

```bash
cd hosting
terraform destroy
```

This removes only the hosting resource group; the `ksi-mock-rg` workload is untouched.
