---
id: MOD-XXX-000            # file name must match
title: Short model name
kind: model                # model | verification | material
status: draft              # draft | reviewed | implemented | verified
sources: [reference-id]    # ids from src/opentcad/data/references.yaml
implemented_in: []         # e.g. [src/opentcad/physics/mobility.py]
verified_by: []            # e.g. [VER-MOB-001]
issue: null                # GitHub issue number that tracks this spec
---

# <Model name>

## Purpose
What physical effect this model describes and which devices/regimes need it.

## Equations
Write each equation in LaTeX, numbered, with its locator in the source.

| # | Equation | Source | Locator |
|---|---|---|---|
| (1) | $\mu = \dots$ | reference-id | Eq. (3), p. 765 |

Variables and units (cm, s, V, K, cm^-3 unless stated):

| Symbol | Meaning | Unit |
|---|---|---|

## Parameters
One row per parameter and material. Values go to `src/opentcad/data/materials/<material>.yaml`
with the same source and locator.

| Material | Parameter | Symbol | Value | Unit | Source | Locator | Notes |
|---|---|---|---|---|---|---|---|

## Validity range
Doping, field, temperature, material ranges stated by the source. What happens outside it.

## DEVSIM implementation notes
* DEVSIM model names and the expression strings (use `num()` for literals, KI-003).
* Solution variables the model depends on (derivatives needed).
* Numerical hazards (overflow, division by zero, discontinuities) and how they are handled.

## Verification plan
| Level | Check | Reference | Tolerance | Rationale |
|---|---|---|---|---|
| L1 | analytic limit … | … | … | … |
| L2 | reproduce Fig./Table … of the source | reference-id | … | … |

## Open questions / conflicts
Disagreements between sources, unit ambiguities, anything needing a human decision.

## Review log
| Date | Role | Result | Notes |
|---|---|---|---|
