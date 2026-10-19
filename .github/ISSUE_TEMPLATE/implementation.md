---
name: Implementation (implementer)
about: Implement a reviewed spec in code with unit tests
title: "[implement] "
labels: ["role:implement", "type:feature", "status:ready"]
---
Backlog-ID:
Depends on:
Spec: MOD-XXX-000

## Goal
<!-- What to build. Physics work requires the spec to be `reviewed` on main. -->

## Acceptance criteria
- [ ] Code follows the spec term by term; model registered with spec id and sources
- [ ] Unit tests in `tests/unit/`; verification tests for the model run (not skip) and pass on both solvers
- [ ] Spec front matter `implemented_in` / `status: implemented` updated
