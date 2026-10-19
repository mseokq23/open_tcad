---
id: MOD-MOB-001
title: Doping-dependent low-field mobility in silicon (Masetti et al. 1983)
kind: model
status: draft
sources: [masetti-1983]
implemented_in: []
verified_by: []
issue: null
---

# Masetti doping-dependent mobility — STUB (example of a researcher task)

This stub shows what the researcher receives. The researcher replaces every `TBD` from the
primary source, records exact locators, and never fills a value from memory or from a
secondary table without saying so.

## Purpose
Low-field electron and hole mobility in silicon versus ionized impurity concentration, for
arsenic-, phosphorus- and boron-doped material.

## Equations
| # | Equation | Source | Locator |
|---|---|---|---|
| (1) | TBD — transcribe the mobility expression exactly as published | masetti-1983 | TBD |

## Parameters
| Material | Parameter | Symbol | Value | Unit | Source | Locator | Notes |
|---|---|---|---|---|---|---|---|
| Si (As-doped, electrons) | TBD | | TBD | | masetti-1983 | TBD | |
| Si (P-doped, electrons) | TBD | | TBD | | masetti-1983 | TBD | |
| Si (B-doped, holes) | TBD | | TBD | | masetti-1983 | TBD | |

## Validity range
TBD (doping and temperature range of the fitted data).

## DEVSIM implementation notes
Edge model `ElectronMobility`/`HoleMobility` evaluated from node doping (arithmetic or geometric
edge average: state which and why), passed to `transport.setup_currents(r, mu_n="ElectronMobility", ...)`.

## Verification plan
| Level | Check | Reference | Tolerance | Rationale |
|---|---|---|---|---|
| L2 | Reproduce the published mobility-vs-doping curves at the paper's tabulated points | masetti-1983 | TBD | TBD |
| L1 | Limits: N→0 gives the lattice mobility; N→∞ gives the minimum mobility | masetti-1983 | 1e-6 rel | closed form |

## Open questions / conflicts
Which dopant species to use when the device has mixed doping (paper fits per species).
