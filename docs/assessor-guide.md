# FedRAMP 20x KSI Assessment Guide

## A Simulated Assessment and Training Walkthrough - KSI Evidence Mock

**Audience:** an assessor (technical or non-technical) who will validate this environment as a stand-in for a FedRAMP 20x assessment, and who wants to train their eye for real client engagements.

**Companion document:** *How the KSI Trust Center Works* (the architecture and determination logic behind everything described here).

**What this environment is:** a training and demonstration "evidence mock" that implements the FedRAMP 20x approach against a live Azure Government subscription with a synthetic workload.
It tracks the FedRAMP Consolidated Rules preview, version `2026.07.06.01`.
It is not an authorized system.
Its purpose is to let you practice the mechanics of a continuous, evidence-based assessment in a safe setting.

---

## 1. What FedRAMP 20x asks you to do differently

Traditional FedRAMP assessment is narrative-first and point-in-time.
A provider writes how a control is met, an assessor reviews a document and a screenshot, and the evidence ages the moment it is captured.

FedRAMP 20x is evidence-first and continuous.
The unit of assessment is the **Key Security Indicator (KSI)**: a specific, testable statement about the system that should be provable from live machine evidence, repeatedly, with minimal human interpretation.

The shift in your job as an assessor:

| Traditional | FedRAMP 20x |
| --- | --- |
| Read a control narrative. | Read a KSI's pass criterion and the evidence behind it. |
| Trust a point-in-time screenshot. | Confirm the evidence is fresh, timestamped, and reproducible. |
| Interview for intent. | Confirm a machine check encodes the intent, and inspect its logic. |
| Sample once a year. | Confirm the check runs continuously and drift is detected. |
| Accept "we do this". | Require "here is the live evidence, and here is what judged it". |

Your core question changes from *"Do you have a policy for this?"* to *"Show me the evidence, show me the rule that judged it, and show me that it ran today and will run tomorrow."*

---

## 2. The KSI model you are assessing

This environment implements **46 KSIs** across **10 families**.

| Family | Name | Count |
| --- | --- | --- |
| KSI-PIY | Policy and Inventory | 5 |
| KSI-CNA | Cloud Native Architecture | 8 |
| KSI-SVC | Service Configuration | 8 |
| KSI-IAM | Identity and Access Management | 6 |
| KSI-MLA | Monitoring, Logging and Auditing | 5 |
| KSI-CMT | Change Management | 4 |
| KSI-RPL | Recovery Planning | 4 |
| KSI-SCR | Supply Chain Risk | 2 |
| KSI-INR | Incident Response | 3 |
| KSI-CED | Cybersecurity Education | 1 |

Each KSI is assessed in one of three **modes**, and the mode tells you how to validate it:

| Mode | Count | How it is proven | How you validate it |
| --- | --- | --- | --- |
| **Auto** | 31 | A live machine check against cloud or pipeline evidence. | Inspect the evidence and the rule; confirm freshness and reproducibility. |
| **Hybrid** | 10 | Automated evidence for part, plus a human attestation for the rest. | Validate the automated leg as above, then review the attestation. |
| **Manual** | 5 | A human attestation supported by organizational records. | Review the attestation document and its supporting evidence. |

A KSI is only counted as **Verified** when it is Auto mode and its check passes.
Hybrid and Manual KSIs are shown as **Review** or **Manual** and require your sign-off; they are never counted as automatically verified.
This is intentional, and it is one of the first things you should confirm the environment gets right.

---

## 3. What "validated" means, by mode

**Auto.**
There is fresh evidence, and an explicit rule that the evidence satisfies.
Example: `KSI-SVC-SIN` (securing information in transit) passes only when every storage account reports TLS 1.2 minimum and HTTPS-only.
You validate it by reading the evidence rows and confirming they meet the stated criterion.

**Hybrid.**
The machine proves what it can; a human attests to the rest.
Example: `KSI-PIY-RSD` (reviewing security in the SDLC) has an automated leg (code scanning is running) and a required human attestation that security review is genuinely built into the development lifecycle.
You validate the automated leg, then review the attestation of record.

**Manual.**
There is no automated signal; the KSI rests on organizational record and human sign-off.
Example: `KSI-CED-RAT` (reviewing all training) is established by a training review record and an attestation.
You validate the attestation and the artifacts it references.

The critical discipline: a Hybrid or Manual KSI is not "done" just because its automated leg is green or its document exists.
It is done when a named reviewer has signed the attestation and the supporting evidence holds up.

---

## 4. The five-step assessment walkthrough

Perform these steps in order. They mirror how a real 20x review should flow.

### Step 1 - Read the Trust Center

Open the Trust Center dashboard (the shared HTML page).
Orient yourself:

- The headline count of automated indicators verified.
- The posture bar: Verified, Pending, Review (Hybrid), Manual.
- The "Attestations signed" tile.
- The per-KSI cards, grouped by family.

At this stage you are only forming expectations.
Do not accept the headline number; your job is to confirm the evidence behind it.

### Step 2 - Pull the machine record (the SDR)

Every run produces a Security Data Report (SDR): `out/sdr/latest.json`, also kept on the `sdr-history` branch.
This is the authoritative machine record.
Confirm the Trust Center's numbers match the SDR totals exactly.
If a dashboard and its underlying report disagree, that is a finding on its own.

### Step 3 - Validate each Auto KSI

For each Auto-mode KSI, confirm all five of these:

1. **Criterion.** Read the written pass criterion. Is it a meaningful test of the KSI's intent, or a weak proxy?
2. **Evidence.** Open the evidence sample. Do the rows actually support a pass under that criterion?
3. **Freshness.** Check the `collected_at` timestamp. Is the evidence recent enough to be meaningful?
4. **Honesty.** Confirm that missing or unreadable evidence is shown as Pending, not passed. Look for any pass that lacks evidence.
5. **Reproducibility.** Confirm you (or the pipeline) can re-run the collector and get the same result. Evidence you cannot reproduce is not evidence.

### Step 4 - Validate each Hybrid and Manual KSI

For each `review_required` KSI:

1. Open its attestation document in `docs/manual/`.
2. Confirm the control statement is met by current practice.
3. Confirm the attestation is actually signed: a named reviewer, a role, a date, and a decision.
4. For Hybrid, confirm the automated leg agrees with the attestation (the human should not be attesting the opposite of what the machine shows).
5. Confirm the review cadence is set and the next review is scheduled.

An unsigned attestation is **awaiting attestation**, which is honest and expected in this mock (currently 0 of 15 are signed).
In a real assessment, an unsigned attestation for an in-scope KSI is a gap, not a pass.

### Step 5 - Confirm it is continuous, not a snapshot

FedRAMP 20x is about ongoing assurance.
Confirm:

- A scheduled job runs the collectors and regenerates the report on a cadence (here, daily).
- Run-over-run drift is detected, and a regression (a KSI that was passing and no longer is) raises a tracked issue.
- Historical runs are retained so a trend can be shown.

A beautiful dashboard that only ran once is not continuous assurance.

---

## 5. The assessor's checklist

Use this as your sign-off sheet.

**Per Auto KSI**
- [ ] The pass criterion is a meaningful test of the KSI.
- [ ] The evidence rows support a pass under that criterion.
- [ ] The evidence is timestamped and fresh.
- [ ] The collector is read-only and its query is scoped correctly.
- [ ] The result is reproducible.
- [ ] Any missing or errored evidence is Pending, not passed.

**Per Hybrid / Manual KSI**
- [ ] An attestation document exists for the KSI.
- [ ] The attestation is signed by a named, appropriate reviewer.
- [ ] The supporting evidence referenced by the attestation holds up.
- [ ] For Hybrid, the automated leg and the attestation agree.
- [ ] A review cadence and next-review date are set.

**System-wide**
- [ ] The Trust Center totals match the SDR totals.
- [ ] No KSI is marked pass without evidence.
- [ ] Hybrid and Manual KSIs are not counted as automatically verified.
- [ ] Collection is read-only and least-privilege.
- [ ] All cloud and identity calls use the correct (Government) endpoints.
- [ ] The assessment runs continuously and detects drift.
- [ ] The published number reflects what the automated identity can actually prove.

---

## 6. Red flags: training your eye

These are the patterns to scrutinize here, and the same ones you will hunt for with real clients.

| Red flag | Why it matters | How to catch it |
| --- | --- | --- |
| **A pass with no evidence** | The most serious failure: a fabricated claim. | Open the evidence for every pass; confirm rows exist and are relevant. |
| **Stale evidence** | A control that passed months ago may be broken now. | Check `collected_at`; treat old timestamps as suspect. |
| **A weak criterion** | "At least one policy exists" can pass while the real control is absent. | Read the criterion critically; ask whether it truly proves intent. |
| **Over-broad scope** | An unscoped query can pull unrelated resources and inflate a pass. | Confirm queries are bound to the in-scope resource group or boundary. |
| **Error hidden as a pass** | A permission error dressed up as success. | Confirm errored collectors are Pending, never pass. |
| **Self-attestation without evidence** | A signed document that references nothing. | Require the attestation to point at real, checkable artifacts. |
| **Dashboard-report mismatch** | The pretty number does not match the machine record. | Reconcile the Trust Center against the SDR. |
| **A snapshot posing as continuous** | Assurance that ran once and never again. | Confirm the schedule, the history, and drift detection. |
| **Over-privileged collection** | Reading with more rights than the running system has inflates the claim. | Confirm the pipeline identity is least-privilege and matches production. |

The last one deserves emphasis because this environment demonstrates it honestly.
The pipeline verifies **19 of 31** automated KSIs using a least-privilege identity.
A human with broader credentials could show 22 of 31, but the environment publishes the lower, continuously provable number.
When you assess a real client, always ask: *is this number what the system can prove on its own, every day, or only what a privileged operator can show once?*

---

## 7. Reproduce it yourself

You do not have to take the dashboard's word for anything.
From a checkout of the repository, with read access to the environment, you can regenerate the evidence and the report:

```bash
# Run every collector and produce a fresh, schema-validated report
python engine/assert.py --out out/sdr

# Or validate the wiring and report shape without touching the cloud
python engine/assert.py --dry-run

# Compare this run to the previous one (drift)
python engine/drift.py --current out/sdr/latest.json --previous <previous-sdr>

# Rebuild the Trust Center from a report
python trustcenter/generate.py --from-sdr out/sdr/latest.json
```

Reproducing the result yourself is the strongest form of validation, and it is exactly what FedRAMP 20x is meant to enable.

---

## 8. Carrying the lens to real client assessments

What you practice here transfers directly.
When you assess a real 20x package, work the same questions:

- **Is each KSI backed by live evidence, or by a narrative?** Push for evidence.
- **Is there a single, inspectable rule that judges each KSI?** Ask to see the logic, not just the result.
- **Is missing evidence handled honestly?** Confirm gaps show as unmet or pending, never as silent passes.
- **Is the scope correct?** Confirm evidence comes from the authorization boundary, not from adjacent or shared resources.
- **Is it continuous?** Confirm the checks run on a schedule and that regressions are detected and tracked.
- **Does the reported posture match what the system can prove with its own least-privilege identity?** Distrust numbers that only hold with elevated access.
- **For human-review items, is there a real, signed attestation pointing at real evidence?** A document is not a control.

A strong 20x provider will welcome these questions because their system can answer them.
A weak one will offer narratives where evidence belongs.
Your job is to tell the difference, and this environment is a safe place to learn where that line sits.

---

## 9. Appendix: KSI catalog for this assessment

Status reflects the least-privilege pipeline run: 19 of 31 automated indicators verified, 0 of 15 attestations signed.
`Pending` means not yet measured (missing collector, gated permission, or honest not-applicable), never a failure.

| KSI | Family | Mode | Status | What it asserts (short) |
| --- | --- | --- | --- | --- |
| KSI-PIY-GIV | PIY | Auto | pass | An authoritative inventory returns resources on demand. |
| KSI-PIY-RSD | PIY | Hybrid | pass (auto) | Security is built into the SDLC; static analysis runs. |
| KSI-PIY-RES / RIS / RVD | PIY | Manual | pending | Executive support, security investment, and disclosure review. |
| KSI-CNA-MAT | CNA | Auto | pass | No publicly exposed attack surface. |
| KSI-CNA-RNT | CNA | Auto | pass | Network segmentation with explicit deny rules. |
| KSI-CNA-ULN / DFP / EIS / IBP | CNA | Auto | pass | Segmentation, policy governance, enforcement, best-practice posture. |
| KSI-CNA-OFA / RVP | CNA | Auto | pending | High availability and DDoS/WAF (not deployed in the mock). |
| KSI-SVC-SIN | SVC | Auto | pass | Information in transit is encrypted (TLS 1.2, HTTPS-only). |
| KSI-SVC-ASM | SVC | Auto | pass | Secrets store hardened (purge protection, no public access). |
| KSI-SVC-EIS / VCM | SVC | Auto | pass | Improvement loop and private service-to-service connectivity. |
| KSI-SVC-ACM / VRI | SVC | Auto | pending | Config management and image signing (not deployed). |
| KSI-SVC-PRR / RUD | SVC | Hybrid | pending | Residual risk and data removal (await attestation). |
| KSI-IAM-ELP | IAM | Auto | pass | Least privilege: no Owner at the resource group. |
| KSI-IAM-JIT | IAM | Auto | pass | Just-in-time access via PIM eligibility. |
| KSI-IAM-SNU | IAM | Auto | pass | Secretless workload identity available. |
| KSI-IAM-APM / SUS | IAM | Auto | pending (gated) | MFA and risk policies (readable only with elevated identity). |
| KSI-IAM-AAM | IAM | Auto | pending | Access reviews (permission-gated). |
| KSI-MLA-OSM | MLA | Auto | pass | Monitoring onboarded (Sentinel workspace present). |
| KSI-MLA-RVL | MLA | Hybrid | pending | Log review (await attestation). |
| KSI-MLA-ALA / EVC / LET | MLA | Auto | pending | Workspace RBAC, compliance evidence, log coverage. |
| KSI-CMT-LMC | CMT | Auto | pass | Change/audit logging shipped to Log Analytics. |
| KSI-CMT-RMV | CMT | Auto | pass | Changes via version-controlled redeployment. |
| KSI-CMT-VTD | CMT | Auto | pass | Automated validation gates every deployment. |
| KSI-CMT-RVP | CMT | Hybrid | pending | Change procedure review (await attestation). |
| KSI-RPL-ABO | RPL | Auto | pass | Backups aligned to objectives. |
| KSI-RPL-ARP / RRO | RPL | Hybrid | pending | Recovery plan and objectives (await attestation). |
| KSI-RPL-TRC | RPL | Auto | pending | Recovery testing cadence. |
| KSI-SCR-MON | SCR | Auto | pending (gated) | Supply-chain monitoring (Dependabot, gated token). |
| KSI-SCR-MIT | SCR | Hybrid | pending | Supply-chain mitigation (await attestation). |
| KSI-INR-RPI / AAR | INR | Hybrid | pending | Incident review and after-action reports (await attestation). |
| KSI-INR-RIR | INR | Manual | pending | Incident response procedure review. |
| KSI-CED-RAT | CED | Manual | pending | Security training review. |

*Prepared by Securitybricks (powered by Aprio). Training and demonstration material; not an authorized assessment.*
