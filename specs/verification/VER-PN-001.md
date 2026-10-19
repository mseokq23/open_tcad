---
id: VER-PN-001
title: 1D abrupt silicon-like PN junction versus closed-form limits
kind: verification
status: verified
sources: [sze-ng-2007, selberherr-1984]
implemented_in: [tests/verification/test_pn_junction_1d.py]
covers: [MOD-DD-001, MOD-MOB-000, MOD-DOP-001]
issue: null
bootstrap: true          # written with the scaffold by the same author as the code; independent re-check in P1-VER-001
---

# VER-PN-001: 1D abrupt PN junction

## Device and inputs (synthetic test inputs, not material claims)
| Input | Value | Why |
|---|---|---|
| $N_A = N_D$ | 1e16 cm^-3 | non-degenerate, low injection up to 0.5 V |
| side lengths | 10 µm each | short base: much shorter than diffusion length at tau = 1 s |
| $\varepsilon_r$ | 11.7 | explicit input (silicon value is `needs-source`, P1-MAT-001) |
| $n_i$ | 1e10 cm^-3 | explicit input |
| $\mu_n, \mu_p$ | 1000, 400 cm^2/(V s) | constant mobility (MOD-MOB-000) |
| $\tau_n=\tau_p$ | 1 s | makes recombination negligible, as the short-base limit assumes |
| mesh | 2 µm-scale at contacts, 2e-7 cm at junction | junction resolves the Debye length (~41 nm) |

## Checks, tolerances and rationale
Observed values: DEVSIM 2.11.1, extended precision (KI-006), identical with MKL PARDISO and
UMFPACK to the digits shown.

| Check | Reference formula | Tolerance | Observed | Rationale |
|---|---|---|---|---|
| NetDoping at contacts | input | 1e-12 rel | exact | regression for KI-003 |
| $\psi_{cathode}-\psi_{anode}$ | $V_t\ln(N_AN_D/n_i^2)$ | 1e-9 rel | 7e-14 | set by ohmic boundary conditions |
| peak field | depletion approximation with $V_{bi}-2V_t$ majority-tail correction (sze-ng-2007, ch. 2) | 1 % | 0.44 % | the uncorrected formula is 4.1 % high |
| equilibrium current | 0 | 1e-15 A/cm^2 | 4e-30 | detailed balance |
| forward current 0.1–0.5 V | short-base diode, quasi-neutral widths from depletion edges | 1 % | 0.09–0.21 % (sim. low) | low injection, no recombination; depletion-edge approximation |
| ideality factor 0.2–0.4 V | 1 | ±0.005 | 1.0005 | diffusion current only |
| Kirchhoff, every bias ≠ 0 | $J_{anode}+J_{cathode}=0$ | 1e-12 rel | ≤ 1.3e-15 | round-off; double precision gave up to 40 % (KI-006) |
| reverse current at −0.1/−0.2/−0.3 V | short-base saturation current | 0.5 % | 0.055–0.07 % | depletion-edge approximation of the reference |
| saturation growth $J(-0.3)/J(-0.1)$ | same ratio from the short-base formula (≈ 1.024) | 0.1 % | 0.02 % | quasi-neutral widths shrink as the depletion region widens |
| mesh convergence at 0.4 V | halve both spacings | 1e-4 rel | 7e-6 | discretization error |

Tolerances may only be tightened, or loosened with a written justification reviewed by the
verifier (docs/verification-policy.md).

## Review log
| Date | Role | Result | Notes |
|---|---|---|---|
| 2026-10-19 | bootstrap | verified | All 13 test cases pass with MKL PARDISO and with UMFPACK. |
| 2026-10-19 | bootstrap | tightened | Found KI-006 (double precision: reverse currents off by 3–4 %, Kirchhoff off by 40 %). Extended precision on by default; Kirchhoff now checked at every bias (1e-12), reverse current 5 % → 0.5 %, saturation ratio compared with theory instead of 1, mesh convergence 0.2 % → 1e-4. |
