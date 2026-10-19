# VER-PN-001 report — 1D abrupt PN junction

Spec: [specs/verification/VER-PN-001.md](../../specs/verification/VER-PN-001.md) · tests:
`tests/verification/test_pn_junction_1d.py` · produced 2026-10-19 with the phase-0 scaffold
(first commit after `9123486`). Status: bootstrap — to be re-checked independently in P1-VER-001.

## Environment
* DEVSIM 2.11.1, Intel MKL 2025.3 (pip `mkl`), Python 3.12, Linux x86-64
* Inputs: the `PARAMS` of the test module (N_A = N_D = 1e16 cm⁻³, 10 µm sides, ε_r = 11.7,
  n_i = 1e10 cm⁻³, μ_n = 1000, μ_p = 400 cm²/(V s), τ = 1 s, T = 300 K) — synthetic test inputs.

## Results (observed error; sign: simulation minus reference)
| Check | Tolerance | MKL PARDISO, extended | UMFPACK, extended | MKL PARDISO, double (KI-006) |
|---|---|---|---|---|
| Built-in potential, rel. error | 1e-9 | 7.2e-14 | 7.2e-14 | 7.2e-14 |
| Peak field (tail-corrected), rel. error | 1 % | 0.44 % | 0.44 % | 0.44 % |
| Equilibrium current | 1e-15 A/cm² | 3.9e-30 | 3.9e-30 | 0.0e+00 |
| Forward current 0.1 V vs short base | 1 % | -0.087 % | -0.087 % | -0.095 % |
| Forward current 0.2 V vs short base | 1 % | -0.096 % | -0.096 % | -0.100 % |
| Forward current 0.3 V vs short base | 1 % | -0.108 % | -0.108 % | -0.108 % |
| Forward current 0.4 V vs short base | 1 % | -0.126 % | -0.126 % | -0.126 % |
| Forward current 0.5 V vs short base | 1 % | -0.205 % | -0.205 % | -0.205 % |
| Ideality factor (0.2–0.4 V) | 1 ± 0.005 | 1.0005 | 1.0005 | 1.0005 |
| Kirchhoff, max over 0.1/0.3/0.5 V | 1e-12 rel | 1.3e-15 | 1.3e-16 | 5.2e-03 |
| Reverse current −0.1 V vs short base | 0.5 % | -0.070 % | -0.070 % | +4.084 % |
| Reverse current −0.3 V vs short base | 0.5 % | -0.055 % | -0.055 % | +3.319 % |
| Mesh convergence at 0.4 V | 1e-4 rel | -7.1e-06 | -7.1e-06 | -7.1e-06 |

## Findings
* With extended precision (default since ADR-0006) both direct solvers agree to the digits shown,
  apart from round-off-level Kirchhoff residuals.
* Double precision fails two checks: terminal currents do not balance at low forward and at
  reverse bias (up to ~40 % in reverse), and reverse currents sit 3–4 % above theory. This was
  hidden by the original 5 % reverse-current tolerance and a Kirchhoff check at +0.3 V only (KI-006).
* The remaining forward-bias deviation (−0.09 … −0.21 %) is consistent with the depletion-edge
  approximation in the short-base reference; it is mesh-converged (7e-6).
