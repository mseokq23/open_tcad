---
id: MOD-MOB-000
title: Constant mobility (user input)
kind: model
status: implemented
sources: [selberherr-1984]
implemented_in: [src/opentcad/physics/transport.py]
verified_by: [VER-PN-001]
issue: null
bootstrap: true          # written with the scaffold; locators + review pending (P1-SPEC-001, P1-VER-001)
---

# Constant mobility

## Purpose
Placeholder transport model: $\mu_n$, $\mu_p$ are constants supplied by the user. Used by the
phase-0 verification case, where analytic limits assume constant mobility.

## Equations
$\mu_n = \text{const},\ \mu_p = \text{const}$; diffusivities follow Einstein, $D = \mu V_t$ (MOD-DD-001 Eq. 3).

## Parameters
None in the material database. Values are explicit inputs (`DiodeParams.mu_n_cm2_Vs`, `mu_p_cm2_Vs`).
Real material mobility models (doping, field and surface dependence) are phase-2 specs:
MOD-MOB-001 (Masetti), MOD-MOB-002 (high field), MOD-MOB-003 (surface).

## DEVSIM implementation notes
DEVSIM parameters `mu_n`, `mu_p`. `transport.setup_currents(r, mu_n=..., mu_p=...)` accepts the
name of an edge model instead, which is how doping/field-dependent models plug in.

## Review log
| Date | Role | Result | Notes |
|---|---|---|---|
| 2026-10-19 | bootstrap | implemented | |
