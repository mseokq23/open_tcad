---
id: MOD-DD-001
title: Drift-diffusion core (Poisson, Boltzmann statistics, Scharfetter-Gummel currents, ideal ohmic contacts)
kind: model
status: implemented
sources: [selberherr-1984, scharfetter-gummel-1969, sze-ng-2007]
implemented_in:
  - src/opentcad/physics/poisson.py
  - src/opentcad/physics/transport.py
  - src/opentcad/physics/contacts.py
verified_by: [VER-PN-001]
issue: null
bootstrap: true          # written with the scaffold; locators + review pending (P1-SPEC-001, P1-VER-001)
---

# Drift-diffusion core

## Purpose
Steady-state and transient carrier transport in non-degenerate semiconductors at a uniform
lattice temperature. Every later model plugs into this core (mobility, recombination,
statistics, contacts).

## Equations

| # | Equation | Source | Locator |
|---|---|---|---|
| (1) | $\nabla\cdot(\varepsilon\nabla\psi) = -q\,(p - n + N_D - N_A)$ | selberherr-1984 | TBD |
| (2) | $n = n_i\,e^{(\psi-\varphi_n)/V_t},\quad p = n_i\,e^{(\varphi_p-\psi)/V_t}$ | selberherr-1984 | TBD |
| (3) | $\mathbf J_n = q\mu_n n\mathbf E + qD_n\nabla n,\quad \mathbf J_p = q\mu_p p\mathbf E - qD_p\nabla p,\quad D = \mu V_t$ | selberherr-1984 | TBD |
| (4) | $\nabla\cdot\mathbf J_n = q\,(R-G) + q\,\partial_t n,\quad \nabla\cdot\mathbf J_p = -q\,(R-G) - q\,\partial_t p$ | selberherr-1984 | TBD |
| (5) | $J_{n,01} = \frac{q\mu_n V_t}{L}\left[n_1 B(-v) - n_0 B(v)\right],\ v = \frac{\psi_0-\psi_1}{V_t},\ B(x)=\frac{x}{e^x-1}$ | scharfetter-gummel-1969 | TBD |
| (6) | $J_{p,01} = -\frac{q\mu_p V_t}{L}\left[p_1 B(v) - p_0 B(-v)\right]$ | scharfetter-gummel-1969 | TBD |
| (7) | Ohmic contact: $n_0p_0=n_i^2$, $n_0-p_0=N_D-N_A$, $\psi = V + V_t\ln(n_0/n_i)$ | sze-ng-2007 | TBD |

$\psi$ is referenced to the intrinsic level. $E = -\nabla\psi$. $V_t = k_BT/q$ with constants from
CODATA 2022 (`src/opentcad/data/constants.yaml`).

| Symbol | Meaning | Unit |
|---|---|---|
| $\psi$ | electrostatic potential (DEVSIM `Potential`) | V |
| $n, p$ | electron/hole density (`Electrons`, `Holes`) | cm^-3 |
| $N_D, N_A$ | ionized donors/acceptors (`NetDoping = Donors - Acceptors`) | cm^-3 |
| $\varepsilon$ | permittivity (`Permittivity` = eps_r * eps_0) | F/cm |
| $\mu_n, \mu_p$ | mobilities (`mu_n`, `mu_p`) | cm^2/(V s) |
| $J_n, J_p$ | current densities (`ElectronCurrent`, `HoleCurrent`) | A/cm^2 |

## Parameters
No material constants of its own. Reads `Permittivity`, `n_i`, `V_t`, `ElectronCharge`, and the
mobilities provided by a mobility model (MOD-MOB-000 constant mobility for phase 0).

## Validity range
Non-degenerate statistics (Boltzmann), complete ionization, isothermal, no quantum confinement.
Breaks down for doping above ~1e19 cm^-3 (needs Fermi-Dirac and bandgap narrowing: backlog P2).

## DEVSIM implementation notes
* Finite-volume (box) discretization; flux on edges, sources on node volumes.
* Equation (5)/(6) use DEVSIM's `B()` and `dBdx()` and `kahan3()` (compensated sum).
* Bernoulli derivatives are hand-written (as in DEVSIM's own examples); all other derivatives
  come from SYMDIFF `diff()` via `physics/_dsmodel.Region`.
* `variable_update`: `log_damp` for Potential, `positive` for carriers.
* Contact equations replace the bulk equation at contact nodes; currents are recorded through
  `edge_current_model` (sign: positive when current enters the device at that contact).
* Mesh: box method needs Delaunay-quality meshes in 2D/3D (obtuse angles cause negative
  edge couplings). Phase 1 mesh specs must state quality checks.

## Verification plan
| Level | Check | Reference | Tolerance | Rationale |
|---|---|---|---|---|
| L1 | Built-in potential, peak field, short-base I-V, ideality, saturation | VER-PN-001 | per case | see VER-PN-001 |
| L1 | Mesh convergence of forward current | VER-PN-001 | 0.2 % | halving spacing |

## Open questions / conflicts
* Locators are `TBD`: first researcher task fills equation/section numbers (backlog P1-SPEC-001).

## Review log
| Date | Role | Result | Notes |
|---|---|---|---|
| 2026-10-19 | bootstrap | implemented | Written with the phase-0 scaffold; needs independent review (P1-SPEC-001, P1-VER-001). |
