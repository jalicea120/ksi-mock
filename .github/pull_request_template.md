## What & why

<!-- One logical change. Link the phase/indicator issue this advances. -->

## Type

- [ ] feat
- [ ] fix
- [ ] chore
- [ ] docs
- [ ] ci

## Checklist

- [ ] Branch is short-lived (`feat/…` `fix/…` `chore/…`), conventional commit messages.
- [ ] No secrets, client secrets, or connection strings added (OIDC only).
- [ ] `ruff check .` clean; `terraform fmt`/`validate` pass.
- [ ] `python engine/assert.py --dry-run` passes.
- [ ] Collectors stay read-only; assertions computed, never hard-coded.
- [ ] Azure Government endpoints/regions only.
