---
id: MOD-DOP-001
title: Abrupt (step) junction doping
kind: model
status: implemented
sources: [sze-ng-2007]
implemented_in: [src/opentcad/physics/doping.py]
verified_by: [VER-PN-001]
issue: null
bootstrap: true          # written with the scaffold; locators + review pending (P1-SPEC-001, P1-VER-001)
---

# Abrupt junction doping

## Purpose
Idealized doping used for analytic verification: uniform acceptors for $x < x_j$, uniform donors
for $x > x_j$.

## Equations
$N_A(x) = N_A\,\Theta(x_j - x)$, $N_D(x) = N_D\,\Theta(x - x_j)$, NetDoping $= N_D - N_A$,
with $\Theta$ = DEVSIM `step()` ($\Theta(0) = 0.5$).

## DEVSIM implementation notes
Numeric literals are formatted with `physics._dsmodel.num()`: SYMDIFF reads digit-only literals as
32-bit integers, which once turned 1e16 into 1.87e9 (docs/known-issues.md, KI-003; regression test
`test_doping_reaches_the_device_exactly`). Phase 1 adds Gaussian/erfc profiles and 1D profile
import (backlog P1-DOP-001).

## Review log
| Date | Role | Result | Notes |
|---|---|---|---|
| 2026-10-19 | bootstrap | implemented | |
