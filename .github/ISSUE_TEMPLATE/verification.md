---
name: Verification (verifier)
about: Independent verification spec and tests, a two-key check, or a gate report
title: "[verify] "
labels: ["role:verify", "type:verification", "status:ready"]
---
Backlog-ID:
Depends on:
Spec: VER-XXX-000

## Goal
<!-- What is verified, against which reference (closed form, source figure/table, other code). -->

## Acceptance criteria
- [ ] Verification spec in `specs/verification/` with tolerance rationale
- [ ] Tests in `tests/verification/`, written from the model spec and source only (`@pytest.mark.requires_model(...)` until implemented)
- [ ] Report in `reports/verification/` once the tests run
