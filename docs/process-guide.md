# How the KSI Trust Center Works

## Architecture and Determination Logic - FedRAMP 20x Evidence Mock

**Audience:** the engineer or assessment lead who needs to explain, in plain terms, how this environment decides that a Key Security Indicator (KSI) is met, what scripts produce and judge the evidence, and how the Trust Center dashboard is assembled.

**Companion document:** *FedRAMP 20x KSI Assessment Guide* (for the assessor performing the validation).

**Status of this system:** a training and demonstration environment ("evidence mock").
It tracks the FedRAMP Consolidated Rules preview, version `2026.07.06.01`.
The data is real (it queries a live Azure Government subscription) but the workload is synthetic and disposable.
This is not an authorized system; it exists to teach the mechanics of continuous, evidence-based assurance.

---

## 1. The idea in one paragraph

Traditional compliance answers "is this control met?" with a written narrative and a screenshot taken once a year.
FedRAMP 20x reframes the question as "can a machine continuously prove this Key Security Indicator is true, from live evidence, right now?"
This environment does exactly that for 46 KSIs.
Small read-only collectors pull live evidence from the cloud and the pipeline, a shared rulebook decides pass or fail from that evidence, an assertion engine records the result as a structured report, and a Trust Center renders the current posture for a human to read.
Nothing is asserted as passing unless there is fresh evidence and an explicit rule that the evidence satisfies.

---

## 2. The pipeline at a glance

```
  engine/map.yaml
  the catalog: 46 KSIs, each with id, family, mode,
  one or more collectors, and a written pass criterion
        |
        v
  COLLECTORS  (read-only; they observe, they never judge)
    collectors/arg/       Azure Resource Graph  (.kql)
    collectors/graph/     Microsoft Graph + ARM (.json)
    collectors/github/    GitHub REST via gh    (.json)
    collectors/sentinel/  Log Analytics / KQL   (.kql)
    collectors/manual/    human attestations    (docs/manual/*.md)
        |
        |   each writes timestamped evidence JSON
        v
    out/evidence/<ksi>.json           (automated evidence)
    out/evidence/manual/<ksi>.json    (attestation evidence)
        |
        v
  engine/checks.py     one boolean rule per automated KSI (the rulebook)
  engine/results.py    evidence + catalog -> status per KSI (pass/fail/pending)
        |
        v
  engine/assert.py     runs collectors, applies rules, writes the report
        |
        +--> out/sdr/<run>.json + latest.json   the Security Data Report (SDR)
        |        validated against engine/schema/ksi-sdr.schema.json
        |
        +--> engine/drift.py   compares this run to the previous run;
        |                       opens a GitHub issue if a passing KSI regressed
        |
        +--> out/history/summary.jsonl   one compact line per run (the trend)
        |
        v
  trustcenter/generate.py + trustcenter/template.html
        |
        v
  out/trustcenter/index.html    the Trust Center dashboard (what people read)
```

The single most important design rule runs through every layer: **collectors observe, the rulebook judges, and neither one is allowed to invent a pass.**

---

## 3. The catalog: `engine/map.yaml`

Everything starts from one file.
`engine/map.yaml` lists all 46 KSIs.
Each entry declares:

| Field | Meaning |
| --- | --- |
| `id` | The KSI identifier, for example `KSI-SVC-SIN`. |
| `name` | The human name, for example "Securing Information in Transit". |
| `family` | One of the 10 KSI families (see the Assessment Guide). |
| `mode` | `Auto`, `Hybrid`, or `Manual` (how the KSI is proven). |
| `collectors` | One or more evidence sources: a `tool` and a `ref` (the query or doc). |
| `pass` | The written criterion a reader can hold the evidence against. |
| `review_required` | `true` when a human sign-off is required (all Hybrid and Manual). |

This file is the contract.
The collectors, the rulebook, and the dashboard all read it, so there is exactly one place where a KSI, its evidence source, and its pass criterion are defined together.

---

## 4. Collectors: how evidence is gathered

A collector is a small program that runs one query per KSI and writes the raw result to a JSON file.
Collectors are strictly read-only.
They never decide pass or fail; they only record what they observed and when.

Every collector emits the same evidence shape:

```json
{
  "indicator":   "KSI-SVC-SIN",
  "tool":        "arg",
  "query_ref":   "collectors/arg/ksi-svc-sin.kql",
  "collected_at":"2026-07-19T22:13:26Z",
  "row_count":   1,
  "rows":        [ { "name": "ksimockstih6428", "minimum_tls_version": "TLS1_2", "https_only": true } ]
}
```

If a collector cannot read its source (a missing permission, a disabled feature, an absent table) it records an `error` field with `rows: []` instead of failing the whole run.
That distinction matters: an error means "not measured", which the engine later treats as **Pending**, never as a failure and never as a pass.

The five collector types:

| Tool | Source | Endpoint (Azure Government) | Example KSIs |
| --- | --- | --- | --- |
| `arg` | Azure Resource Graph | `management.usgovcloudapi.net` | inventory, storage TLS, public exposure, NSG, backups, RBAC, Defender scores |
| `graph` | Microsoft Graph + ARM | `graph.microsoft.us` | Conditional Access (MFA), risk policies, PIM eligibility |
| `github` | GitHub REST (via `gh`) | `api.github.com` | pipeline test runs, Dependabot, code scanning |
| `sentinel` | Log Analytics query API | `api.loganalytics.us` | change/audit logging, security incidents |
| `manual` | Attestation documents | `docs/manual/*.md` frontmatter | human sign-off for Hybrid and Manual KSIs |

Two engineering details worth knowing when you explain this:

- **Scope discipline.** Every Azure query is scoped to the workload resource group (`ksi-mock-rg`).
  The subscription is shared, so an unscoped query would pull unrelated resources and produce a false reading.
  This is a deliberate, verifiable guardrail.
- **Manual evidence is separated.** Attestations are written to a `manual/` subfolder so they never overwrite a Hybrid KSI's automated evidence.
  A Hybrid KSI therefore carries both an automated reading and a human attestation at the same time.

---

## 5. The determination: `engine/checks.py` and `engine/results.py`

This is the heart of "how it decides a KSI is valid."

**`engine/checks.py` is the rulebook.**
It holds one small boolean function per automated KSI.
Each function receives the evidence rows and returns `True` (met) or `False` (not met).
The pass logic lives in exactly one place, so the dashboard and the report can never disagree about what "met" means.

A few real examples, in plain language:

| KSI | What the rule checks |
| --- | --- |
| `KSI-SVC-SIN` (Information in transit) | Every storage account reports TLS 1.2 minimum and HTTPS-only. |
| `KSI-CNA-MAT` (Minimize attack surface) | Zero publicly exposed resources were found. |
| `KSI-IAM-APM` (Passwordless / strong MFA) | At least one enabled Conditional Access policy requires MFA or a phishing-resistant strength. |
| `KSI-IAM-ELP` (Least privilege) | No role assignment grants Owner at the resource group. |
| `KSI-CMT-LMC` (Logging changes) | At least one change/audit log category is actively arriving in Log Analytics. |
| `KSI-SCR-MON` (Supply chain monitoring) | Dependabot is active and no open alert is High or Critical. |

**`engine/results.py` turns evidence into status.**
For each KSI in the catalog it does three things:

1. Find the evidence for that KSI (if any).
2. If the evidence errored or is missing, the result is `null`.
3. Otherwise it applies the matching rule from `checks.py`.

The result maps to one of three states:

| Result of the rule | Status | Meaning |
| --- | --- | --- |
| `True` | **pass** | Evidence exists and satisfies the criterion. |
| `False` | **fail** | Evidence exists and does not satisfy the criterion. |
| `null` (errored, missing, or no rule yet) | **pending** | Not measured. Never counted as pass or fail. |

`results.py` is shared by the engine and the dashboard, which is what guarantees the number on the Trust Center equals the number in the machine report.

The honesty rules, stated plainly:

- No evidence, no pass.
- An error is "not measured" (Pending), not a failure.
- A KSI with no rule yet is Pending (staged), not a silent pass.
- Human-review KSIs (Hybrid and Manual) are never counted as automatically verified, even when their automated leg passes.

---

## 6. The record: `engine/assert.py` and the SDR

`engine/assert.py` is the assertion engine that ties it together.
When it runs it:

1. Runs every collector into `out/evidence/`.
2. Loads the evidence and applies the rulebook through `results.py`.
3. Writes a **Security Data Report (SDR)** to `out/sdr/<run-id>.json` and `latest.json`.
4. Validates that SDR against a schema and refuses to write a malformed one.

The SDR is the machine-readable record of one assessment run.
Its shape:

```json
{
  "info": {
    "sdr_version": "ksi-sdr/0.1",
    "run_id": "20260719T221326Z-....",
    "generated": "2026-07-19T22:13:26Z",
    "totals": { "total": 46, "automated_total": 31, "verified": 19,
                "pass": 20, "fail": 0, "pending": 26,
                "attestable_total": 15, "attested": 0 }
  },
  "assertions": [
    { "id": "KSI-SVC-SIN", "mode": "Auto", "result": true, "status": "pass",
      "pass_criteria": "...", "tool": "arg", "collected_at": "...",
      "row_count": 1, "evidence": [ ... ], "attestation": null },
    ...
  ]
}
```

`engine/schema/ksi-sdr.schema.json` is a strict JSON Schema.
It rejects unknown fields, wrong types, and inconsistent records (for example, a status of `pass` with a result of `false`).
Because the CI gate builds and validates an SDR on every change, the report shape cannot silently drift.

**Key totals, defined precisely:**

- `automated_total` = 31 (the Auto-mode KSIs).
- `verified` = the Auto-mode KSIs that pass. This is the headline "19 of 31".
- `attestable_total` = 15 (every KSI that requires human sign-off).
- `attested` = how many of those have been signed. Currently 0.

---

## 7. The dashboard: `trustcenter/generate.py` and `template.html`

The Trust Center is a single self-contained HTML page.
`trustcenter/generate.py` builds a data model (using the same `results.py`, so it agrees with the SDR) and injects it into `trustcenter/template.html`.

It can be built two ways:

- From live local evidence (what an operator sees with their own credentials), or
- From an existing SDR with `--from-sdr` (what the automated pipeline verified).

The published Trust Center is built from the pipeline's SDR, so it shows what the automated, least-privilege identity can prove - not a more privileged local view.

What the page shows:

- A headline count of automated indicators verified (19 of 31).
- A posture bar and legend: Verified, Pending, Review (Hybrid), Manual.
- A key-performance row, including an "Attestations 0 of 15" tile.
- One card per KSI, grouped by family, showing status, the pass criterion, the evidence sample, the source collector, and the collection timestamp.
- For Hybrid and Manual KSIs, an attestation line: "Attested by ..." or "Awaiting attestation".
- A "verified over time" sparkline once there are at least two runs of history.

Because the page is self-contained, it can be shared as a file or published as a private web artifact and handed to a reviewer.

---

## 8. Continuous assurance: the daily loop

A scheduled workflow (`.github/workflows/assertions.yml`) makes this continuous rather than a one-time snapshot.
Each day (and on demand) it:

1. Restores the previous run's report and trend history from a dedicated `sdr-history` branch.
2. Runs the collectors and the assertion engine (as a least-privilege service identity).
3. Runs `engine/drift.py` to compare this run to the previous one.
4. If any Auto-mode KSI that used to pass no longer passes, it files a labelled GitHub issue describing the regression.
5. Regenerates the Trust Center and uploads it, along with the SDR, as build artifacts.
6. Appends this run to the trend history and pushes it back to `sdr-history`.

`engine/drift.py` is the watchdog.
It classifies each automated KSI as a **regression** (was passing, now not), a **recovery** (was not passing, now is), or newly verified.
Regressions are the actionable signal; recoveries and steady state are informational.
This is what turns a static report into a living assurance surface with a memory.

---

## 9. Why the headline is 19 of 31 (the identity nuance)

An assessor will ask why some KSIs that clearly could pass are shown as Pending.
The answer is deliberate and worth stating clearly.

The daily pipeline runs as a **least-privilege service identity**.
Three KSIs need evidence that identity is intentionally not granted to read:

| KSI | Evidence source | Why the pipeline identity cannot read it |
| --- | --- | --- |
| `KSI-IAM-APM` | Microsoft Graph (Conditional Access) | No directory read permission granted. |
| `KSI-IAM-SUS` | Microsoft Graph (risk policies) | Same. |
| `KSI-SCR-MON` | GitHub Dependabot alerts | The default pipeline token cannot read alerts. |

A human operator with broader credentials can read all three, and would see 22 of 31.
The environment publishes the **continuously verifiable** number (19 of 31) rather than the more privileged view, because the honest claim is "what the automated system can prove on its own, every day, with least privilege."
The capability to reach 22 is wired and dormant; granting the identity those read permissions would light the three up with no code change.
This is itself a teaching point: the number a Trust Center shows should reflect what it can actually, repeatedly prove.

---

## 10. Security and integrity properties

These are the properties that make the evidence trustworthy, and the ones an assessor should confirm:

- **Read-only collection.** No collector writes to the environment; they only query.
- **Least privilege.** The pipeline identity holds the minimum roles needed to read evidence.
- **Government endpoints only.** All Azure and identity calls use Azure Government URLs.
- **Scoped queries.** Azure queries are bound to the workload resource group.
- **No fabricated results.** Missing or errored evidence is Pending, never pass.
- **Single source of truth.** The dashboard and the report compute status from the same code.
- **Schema-enforced output.** The report cannot change shape without failing the gate.
- **Tamper-evident history.** Every run is recorded on a dedicated branch and diffed against the prior run.
- **No public exposure.** The workload runs on internal networking with no public IPs.

---

## 11. Component reference

| Path | Responsibility |
| --- | --- |
| `engine/map.yaml` | The catalog: 46 KSIs, modes, collectors, pass criteria. |
| `collectors/arg/` | Azure Resource Graph collectors (`.kql` + runner). |
| `collectors/graph/` | Microsoft Graph and ARM collectors (`.json` + runner). |
| `collectors/github/` | GitHub REST collectors (`.json` + runner). |
| `collectors/sentinel/` | Log Analytics / Sentinel collectors (`.kql` + runner). |
| `collectors/manual/` | Attestation collector; reads `docs/manual/*.md`. |
| `docs/manual/*.md` | The 15 human attestation records. |
| `engine/checks.py` | The pass-criteria rulebook (one rule per automated KSI). |
| `engine/results.py` | Evidence plus catalog to per-KSI status; shared source of truth. |
| `engine/assert.py` | Assertion engine: collect, assess, write and validate the SDR. |
| `engine/schema/ksi-sdr.schema.json` | Strict schema for the SDR. |
| `engine/drift.py` | Run-over-run drift detection and issue text. |
| `trustcenter/generate.py` | Builds the Trust Center from the catalog and evidence (or an SDR). |
| `trustcenter/template.html` | The self-contained dashboard template. |
| `.github/workflows/ci.yml` | Change gate: lint, Terraform validate, dry-run assert + schema check. |
| `.github/workflows/assertions.yml` | Daily continuous run: collect, assess, drift, publish, history. |
| `sdr-history` branch | Durable trend history: `latest.json` and `summary.jsonl`. |

---

## 12. Appendix: KSI catalog with current pipeline status

Status column reflects the least-privilege pipeline run (19 of 31 automated verified).
`Pending` means not yet measured by the pipeline (missing collector, gated permission, or honest not-applicable), never a failure.

| KSI | Family | Mode | Status | Evidence source(s) |
| --- | --- | --- | --- | --- |
| KSI-PIY-GIV | PIY | Auto | pass | arg |
| KSI-PIY-RES | PIY | Manual | pending | manual |
| KSI-PIY-RIS | PIY | Manual | pending | manual |
| KSI-PIY-RSD | PIY | Hybrid | pass (auto leg) | github, manual |
| KSI-PIY-RVD | PIY | Manual | pending | manual |
| KSI-CNA-DFP | CNA | Auto | pass | arg |
| KSI-CNA-EIS | CNA | Auto | pass | arg |
| KSI-CNA-IBP | CNA | Auto | pass | arg |
| KSI-CNA-MAT | CNA | Auto | pass | arg |
| KSI-CNA-OFA | CNA | Auto | pending | arg |
| KSI-CNA-RNT | CNA | Auto | pass | arg |
| KSI-CNA-RVP | CNA | Auto | pending | arg |
| KSI-CNA-ULN | CNA | Auto | pass | arg |
| KSI-SVC-ACM | SVC | Auto | pending | defender/policy |
| KSI-SVC-ASM | SVC | Auto | pass | arg, graph |
| KSI-SVC-EIS | SVC | Auto | pass | arg |
| KSI-SVC-PRR | SVC | Hybrid | pending | defender/policy, manual |
| KSI-SVC-RUD | SVC | Hybrid | pending | arg, manual |
| KSI-SVC-SIN | SVC | Auto | pass | arg |
| KSI-SVC-VCM | SVC | Auto | pass | arg |
| KSI-SVC-VRI | SVC | Auto | pending | defender/policy |
| KSI-IAM-AAM | IAM | Auto | pending | graph |
| KSI-IAM-APM | IAM | Auto | pending (gated) | graph |
| KSI-IAM-ELP | IAM | Auto | pass | arg, graph |
| KSI-IAM-JIT | IAM | Auto | pass | graph (ARM PIM) |
| KSI-IAM-SNU | IAM | Auto | pass | arg, graph |
| KSI-IAM-SUS | IAM | Auto | pending (gated) | graph |
| KSI-MLA-ALA | MLA | Auto | pending | arg, graph |
| KSI-MLA-EVC | MLA | Auto | pending | defender/policy |
| KSI-MLA-LET | MLA | Auto | pending | arg |
| KSI-MLA-OSM | MLA | Auto | pass | arg |
| KSI-MLA-RVL | MLA | Hybrid | pending | sentinel, manual |
| KSI-CMT-LMC | CMT | Auto | pass | sentinel |
| KSI-CMT-RMV | CMT | Auto | pass | github, sentinel |
| KSI-CMT-RVP | CMT | Hybrid | pending | github, manual |
| KSI-CMT-VTD | CMT | Auto | pass | github |
| KSI-RPL-ABO | RPL | Auto | pass | arg |
| KSI-RPL-ARP | RPL | Hybrid | pending | arg, manual |
| KSI-RPL-RRO | RPL | Hybrid | pending | manual |
| KSI-RPL-TRC | RPL | Auto | pending | arg |
| KSI-SCR-MIT | SCR | Hybrid | pending | defender/policy, manual |
| KSI-SCR-MON | SCR | Auto | pending (gated) | github |
| KSI-INR-AAR | INR | Hybrid | pending | sentinel, manual |
| KSI-INR-RIR | INR | Manual | pending | manual |
| KSI-INR-RPI | INR | Hybrid | pending | sentinel, manual |
| KSI-CED-RAT | CED | Manual | pending | manual |

*Prepared by Securitybricks (powered by Aprio). Training and demonstration material.*
