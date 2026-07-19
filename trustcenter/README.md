# Trust Center

A self-contained HTML "live assurance console" that renders current KSI status
from real collector evidence - the FedRAMP 20x Trust Center surface for this mock.

## How it works

```
engine/map.yaml  ─┐
out/evidence/*    ─┼─► trustcenter/generate.py ─► out/trustcenter/index.html
engine/checks.py ─┘        (renders trustcenter/template.html)
```

- `engine/checks.py` computes each indicator's pass/fail from its evidence. It is
  the **single source of truth** for pass logic, shared with the assertion engine
  so the dashboard and the SDR never disagree.
- Indicators with no automated check yet render as **Pending** (staged), never as
  a fake pass.
- Every card carries the collector's `collected_at` timestamp, so "continuous" is
  provable, and re-running refreshes it.

## Run it

```bash
# 1. collect fresh evidence (read-only)
export AZURE_SUBSCRIPTION_ID=<sub>
python collectors/arg/runner.py --out out/evidence

# 2. render the Trust Center
python trustcenter/generate.py            # -> out/trustcenter/index.html
```

Open `out/trustcenter/index.html` in a browser. The generated file is a build
artifact (gitignored); only the generator and template are versioned.

## Phase 6

The scheduled `assertions.yml` workflow runs the collectors, then this generator,
and publishes the result - so the Trust Center updates on every cycle and, with
run history, shows change over time.
