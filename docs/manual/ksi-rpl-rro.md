---
indicator: KSI-RPL-RRO
name: Reviewing Recovery Objectives
family: KSI-RPL
mode: Hybrid
review_required: true
attested: false
attestor: ""
role: ""
attested_date: ""
review_cadence: annual
next_review_due: ""
automated_support: []
evidence_refs: []
---

# KSI-RPL-RRO - Reviewing Recovery Objectives

**Family.** KSI-RPL (Recovery Planning)

**Control statement.** RTO/RPO defined and persistently reviewed against business needs and capability.

**Attestation of record.** This indicator is **Hybrid**: automated collectors provide partial, continuous evidence, and a designated reviewer attests to the parts that cannot be proven by machine. This document is the attestation of record. A designated
reviewer completes the sections below, then sets `attested: true` with their name, role, and
date in the frontmatter. Until then the KSI surfaces this indicator as *awaiting attestation* -
it is never counted as automatically verified.

## What is attested
- The control statement above is met by current practice.
- Responsibilities and cadence for sustaining it are assigned and understood.
- Any gaps are tracked with an owner and target date (record them under Notes).

## Evidence reviewed
The automated leg (see `automated_support`) supplies continuous signal; the reviewer confirms it reflects reality and covers what automation cannot.
- Enumerate concrete artifacts in `evidence_refs` (paths, URLs, ticket ids).

## Review procedure
1. Gather the evidence named above for the current review period.
2. Confirm the control statement holds; note exceptions.
3. Record the decision and sign off below; update the frontmatter.
4. Schedule the next review per `review_cadence` and set `next_review_due`.

## Sign-off
- Reviewer:
- Role:
- Date:
- Decision: ( ) Attested  ( ) Attested with exceptions  ( ) Not attested
- Notes:
