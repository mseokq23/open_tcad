# Known issues and pitfalls

Each entry: symptom, cause, fix, and the test that guards it. Add new entries as you find them.

## KI-001 — MKL 2026.x breaks DEVSIM PARDISO factorization
* **Symptom:** `There was a floating point exception of type "Invalid, Divide-by-zero" during LU
  Factorization` → `Convergence failure!` on the very first solve.
* **Cause:** observed with DEVSIM 2.11.1 + `mkl` 2026.2 (pip). The same scripts converge with
  `mkl` 2025.3 and with the bundled UMFPACK solver (verified 2026-10-19).
* **Fix:** `pyproject.toml` pins `mkl>=2024,<2026`. Fallback: `OPENTCAD_SOLVER=umfpack`.
* **Guard:** CI runs the verification suite with both solvers.

## KI-002 — DEVSIM needs BLAS/LAPACK at import time
* **Symptom:** `Error loading math libraries. Please install a suitable BLAS/LAPACK library and
  set DEVSIM_MATH_LIBS.` on `import devsim`.
* **Fix:** on Linux/Windows x86-64 the `mkl` dependency provides them. Elsewhere install
  OpenBLAS/LAPACK and point `DEVSIM_MATH_LIBS` at the libraries (see DEVSIM's install docs).
  Without MKL, DEVSIM uses its bundled UMFPACK as the direct solver.

## KI-003 — SYMDIFF reads digit-only literals as 32-bit integers
* **Symptom:** doping of `1e16` written as `10000000000000000` in an expression became
  `1.874919424e9` (the value modulo 2^32); the drift-diffusion solve then stalled.
* **Fix:** interpolate numbers with `physics._dsmodel.num()` (float literal with exponent).
* **Guard:** `tests/verification/test_pn_junction_1d.py::test_doping_reaches_the_device_exactly`.

## KI-004 — `reset_devsim()` resets the solver choice
* **Symptom:** after a reset, solves silently use the default solver again.
* **Fix:** always reset through `opentcad._devsim.reset()`, which re-applies `OPENTCAD_SOLVER`.

## KI-005 — Relative-error convergence and potentials near zero
* DEVSIM measures convergence by relative update; carrier densities need the loose absolute
  tolerance (`SolveSettings.absolute_error = 1e10`) and a tight relative one. If a new device
  stalls at a relative error of ~1e-10, check the inputs first (e.g. KI-003) before relaxing
  tolerances.

## KI-006 — Small currents are not converged in double precision
* **Symptom:** in VER-PN-001, anode and cathode currents disagreed by 0.5 % at +0.1 V and by
  ~40 % in reverse bias (−0.1…−0.3 V); the reverse current depended on the sweep path
  (−2.6e-11 vs −6.1e-11 A/cm² at −0.2 V) and sat 3–4 % above short-base theory.
* **Cause:** DEVSIM's convergence test uses global absolute/relative update norms. Minority
  carrier densities (~1e4 cm⁻³ next to 1e16 cm⁻³ majorities) are not resolved by them in double
  precision, and tightening the tolerances makes Newton fail (round-off floor).
* **Fix:** `opentcad._devsim` enables DEVSIM's extended precision (`extended_solver`,
  `extended_model`, `extended_equation`) by default (`OPENTCAD_PRECISION=extended`). Kirchhoff
  then holds to ~1e-15 and reverse currents match theory within 0.07 %. Cost: ~3x run time in
  1D. `OPENTCAD_PRECISION=double` is faster but only safe at high current.
* **Guard:** `test_terminal_currents_are_continuous_at_every_bias` and
  `test_reverse_current_saturates_at_short_base_theory` (both fail in double precision);
  `tests/unit/test_devsim_config.py`. Follow-up: P1-SOLVER-001 (cost on 2D meshes) and
  P2-SPEC-010/P2-CONV-001 (scaling, current-based convergence checks).
