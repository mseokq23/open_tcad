---
name: Spec (researcher)
about: A model, material or numerics spec written from primary sources
title: "[spec] "
labels: ["role:research", "type:spec", "status:ready"]
---
Backlog-ID:
Depends on:
Spec: MOD-XXX-000

## Goal
<!-- Which physical effect / material / numerical method, and which devices need it. -->

## Candidate sources
<!-- Leads only (author, title, DOI if known). The researcher verifies them; nothing here is a citation. -->

## Acceptance criteria
- [ ] Spec in `specs/` from `specs/TEMPLATE.md`, every equation and parameter with source id + locator
- [ ] New references created with `scripts/doi_lookup.py`; values in `src/opentcad/data/` as `extracted`
- [ ] Verification plan with at least one L1 or L2 check and tolerance rationale
- [ ] `scripts/check_citations.py` passes
