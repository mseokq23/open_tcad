---
id: MOD-RG-001
title: Shockley-Read-Hall recombination (single trap level, constant lifetimes)
kind: model
status: implemented
sources: [shockley-read-1952, hall-1952]
implemented_in: [src/opentcad/physics/recombination.py]
verified_by: []
issue: null
bootstrap: true          # written with the scaffold; locators + review pending (P1-SPEC-001, P1-VER-001)
---

# Shockley-Read-Hall recombination

## Purpose
Recombination through a single deep trap level. Dominant in indirect-gap silicon at low and
moderate injection; produces the n = 2 region of forward diode characteristics and the
generation current under reverse bias.

## Equations
| # | Equation | Source | Locator |
|---|---|---|---|
| (1) | $U = \dfrac{np - n_i^2}{\tau_p\,(n+n_1) + \tau_n\,(p+p_1)}$ | shockley-read-1952 | TBD |
| (2) | $n_1 = n_i e^{(E_t-E_i)/k_BT},\quad p_1 = n_i e^{(E_i-E_t)/k_BT}$ | shockley-read-1952 | TBD |
| (3) | Same rate expression, independent derivation | hall-1952 | TBD |

Phase 0 sets $E_t = E_i$, so $n_1 = p_1 = n_i$. Doping-dependent lifetimes (Scharfetter
relation) and Auger recombination are a separate model (MOD-RG-002, backlog P2-SPEC-004).

| Symbol | Meaning | Unit |
|---|---|---|
| $U$ | net recombination rate (DEVSIM `USRH`) | cm^-3 s^-1 |
| $\tau_n, \tau_p$ | lifetimes (`taun`, `taup`) | s |
| $n_1, p_1$ | trap-level densities (`n1`, `p1`) | cm^-3 |

## Parameters
Lifetimes are process-dependent device inputs, not material constants. They are not stored in
the material database unless a spec for a specific doping-dependent model provides them.

## Validity range
Non-degenerate statistics, single trap level, trap density small compared with carrier densities.

## DEVSIM implementation notes
`ElectronGeneration = -q*USRH`, `HoleGeneration = +q*USRH` as node models of the continuity
equations (sign convention of MOD-DD-001). Derivatives w.r.t. Electrons and Holes.

## Verification plan
| Level | Check | Reference | Tolerance | Rationale |
|---|---|---|---|---|
| L1 | Reverse generation current of a long junction ~ q n_i W/(2 tau) | sze-ng-2007 | 10 % | depletion-region generation; VER-RG-001 (backlog P1-VER-003) |
| L1 | Forward ideality factor approaches 2 at low bias when tau is short | sze-ng-2007 | trend | VER-RG-001 (backlog P1-VER-003) |

## Review log
| Date | Role | Result | Notes |
|---|---|---|---|
| 2026-10-19 | bootstrap | implemented | Needs locators (P1-SPEC-001), independent review (P1-VER-001) and VER-RG-001 (P1-VER-003). |
