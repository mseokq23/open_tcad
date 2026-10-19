# Verification policy

## 1. Levels
| Level | Question | Example | Where |
|---|---|---|---|
| L0 | Does the code do what it says? | registry, DB gating, formula helpers | `tests/unit/` |
| L1 | Does the simulator reproduce closed-form limits? | short-base diode current, peak field | `tests/verification/` |
| L2 | Does a model reproduce its own source? | mobility vs doping at the paper's tabulated points | `tests/verification/` |
| L3 | Does it agree with another independent code? | same structure in another open-source simulator | `reports/verification/` |
| L4 | Does it agree with measurements? | published measured I-V / C-V | `reports/verification/` |

A model reaches `verified` when every check in its spec's verification plan passes in CI (at
least one L1 or L2 check per model).

## 2. Independence
* Verification specs and tests are written by the verifier from the model spec and the source,
  without reading the implementation.
* The implementer never edits `tests/verification/` or `specs/verification/`. If a verification
  test looks wrong, comment with evidence on the issue; the verifier decides.
* Closed-form references live in `src/opentcad/verification/analytic.py` and never import DEVSIM.

## 3. Tolerances
* Every tolerance has a written rationale in the verification spec (what approximation the
  reference makes, measured discretization error, published uncertainty).
* Record the error observed when the test was written. A tolerance far above the observed error
  hides regressions: keep it within ~5x of the observed error unless the reference itself is
  approximate.
* Tolerances may be tightened freely. Loosening needs a justification in the PR, a review-log
  entry in the spec, and verifier approval.

## 4. Numerical hygiene checked in every verification spec
* Mesh convergence: halve the spacing; the quantity must change less than the tolerance.
* Solver independence: CI runs the verification suite with MKL PARDISO and with UMFPACK.
* Conservation: terminal currents sum to zero; charge neutrality far from junctions.
* Units: state units for every input and output; prefer SI-derived cm-based units.

## 5. Convergence benchmark (phase 2)
`benchmarks/convergence/` will hold a fixed list of hard cases (high doping, high reverse bias,
low current, MOS inversion). CI reports the success rate; regressions block merges.

## 6. Reports
For each verification spec the verifier keeps `reports/verification/<VER-ID>.md`: inputs,
results table, observed errors, plots if useful, and the commit hash.
