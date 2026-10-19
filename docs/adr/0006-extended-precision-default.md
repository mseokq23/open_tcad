# 0006 — Extended precision is the default arithmetic

Status: accepted (2026-10-19)

## Context
VER-PN-001 showed that in double precision the drift-diffusion solution does not resolve
minority-carrier densities: reverse-bias terminal currents violated Kirchhoff's law by ~40 %,
depended on the sweep path, and sat 3–4 % above short-base theory (KI-006). DEVSIM's global
update norms accept these solutions, and tighter tolerances hit the round-off floor. DEVSIM
offers extended-precision model evaluation, equation assembly and linear solves.

## Decision
* `opentcad._devsim` sets `extended_solver`, `extended_model` and `extended_equation` to true
  after every reset, unless `OPENTCAD_PRECISION=double`.
* Verification tests run in the default (extended) mode and check terminal-current balance at
  every bias point, so a silent loss of accuracy fails CI.

## Consequences
* About 3x slower solves in 1D; the 2D cost is measured in P1-SOLVER-001, which may introduce a
  per-run choice (e.g. double precision plus a current-balance check) in the project schema.
* Results no longer depend on the sweep path at low current; small-signal and leakage work in
  phase 2 starts from a trustworthy baseline.
