# Roadmap

Phases are milestones on GitHub; their work items live in `.github/backlog/phase<k>.yaml` and
become issues through `scripts/bootstrap_github.py`. A phase ends when its gate issue
(`P<k>-GATE`) is closed by the human after reviewing the verifier's gate report.

Durations are indicative for one person with four agents and daily review/merging; the
verifier and the human merge step set the pace.

## Phase 0 — scaffold (done, 2026-10-19)
* DEVSIM core wrapper with solver selection (MKL PARDISO / UMFPACK), process-global reset.
* Drift-diffusion (Poisson + Scharfetter-Gummel continuity), SRH, ideal ohmic contacts, step
  doping, 1D mesh, bias sweeps with step control.
* Material database with provenance and status gates; bibliography; CODATA 2022 constants.
* VER-PN-001: 1D PN junction against closed-form limits on both solvers. It exposed KI-006
  (double precision misses small currents); extended precision is now the default (ADR-0006).
* GUI skeleton (PySide6) with off-screen snapshots; agent roles, skills, orchestrator, CI.
* Known debt, tracked in phase 1: `bootstrap: true` specs (locators and independent review
  pending), silicon permittivity `needs-source`, all values `extracted` (none `checked`).

## Phase 1 — MVP: 2D devices end-to-end (≈ 1.5–3 months)
Goal: a user draws a 2D PN diode or MOS capacitor in the GUI (or writes the project file),
meshes it, runs I-V / C-V sweeps and inspects fields, and every number is traceable.

| Workstream | Items |
|---|---|
| Debt from phase 0 | P1-SPEC-001 (locators), P1-VER-001 (independent review), P1-VER-002 (two-key check of constants and Si data), P1-MAT-001 (Si permittivity), P1-MAT-002 (primary Si sources) |
| Project schema and runner | P1-SCHEMA-001 → P1-IO-001 → P1-RUN-001 → P1-SWEEP-001; P1-SOLVER-001 (diagnostics) |
| 2D structures | P1-SPEC-003 → P1-MESH-001 (Gmsh, separate process) → P1-DD-002 (regions, insulators, interfaces) |
| Doping | P1-SPEC-002 → P1-DOP-001 (Gaussian/erfc, profile import) |
| MOS | P1-SPEC-004, P1-MAT-003 (SiO2) → P1-MOS-001 (MOS capacitor, quasi-static C-V) |
| Verification | P1-VER-003 (VER-RG-001), P1-VER-004 (VER-PN-002, 2D vs 1D), P1-VER-005 (VER-MOS-001), P1-VER-006 (VER-MESH-001) |
| GUI and docs | P1-DES-001 (theme, badges) → P1-DES-002 (structure editor), P1-DES-003 (results viewer), P1-DES-004 (run panel), P1-DES-005 (model/material browser) → P1-DOC-001 (tutorial) |

**Exit criteria (P1-GATE)**
1. VER-PN-001 (independently re-checked), VER-PN-002, VER-RG-001, VER-MOS-001 and VER-MESH-001
   pass in CI with MKL PARDISO and UMFPACK.
2. `scripts/check_citations.py --strict` passes: no `bootstrap: true`, no `TBD` in non-draft
   specs, every material value and constant in use `checked`, every registered model `verified`
   (MOD-RG-001 via VER-RG-001).
3. The tutorial `docs/tutorials/2d-pn-diode.md` works from the GUI and from
   `opentcad run <project>.yaml`, producing identical `runs/<id>/` results.
4. The GUI never imports DEVSIM; a crashing simulation does not take the window down.

## Phase 2 — model library and robustness (≈ 3–5 months)
Goal: the physics and numerics a device engineer expects for silicon MOS and power/diode
work, each model traceable to its primary source and verified.

| Workstream | Items |
|---|---|
| Mobility | P2-SPEC-001/002/003 → P2-MOB-001 (doping), P2-MOB-002 (high field), P2-MOB-003 (surface) |
| Recombination and generation | P2-SPEC-004 → P2-RG-001 (Auger, lifetimes); P2-SPEC-007 → P2-II-001 (impact ionization); P2-SPEC-008 → P2-BTBT-001 |
| Statistics and band structure | P2-SPEC-005 → P2-STAT-001 (Fermi-Dirac, incomplete ionization); P2-SPEC-006 → P2-BGN-001; P2-SPEC-013 (density-gradient scoping, human decision) |
| Contacts | P2-SPEC-009 → P2-CON-001 (Schottky) |
| Materials | P2-MAT-001 (Ge, GaAs), P2-MAT-002 (4H-SiC), P2-MAT-003 (insulators), P2-MATDB-001 (T-dependent parameters, user overrides) |
| Numerics and analyses | P2-SPEC-010 → P2-CONV-001 (convergence strategies); P2-SPEC-011 → P2-AC-001; P2-SPEC-012 → P2-TRAN-001; P2-DOE-001 (parallel parameter sweeps) |
| Devices | P2-DEV-001 (2D MOSFET template, Id-Vg / Id-Vd) |
| Verification | P2-VER-001 … P2-VER-013 (one per model family), P2-VER-010 (convergence benchmark), P2-VER-014 (L3 cross-code comparison) |
| GUI and docs | P2-SCHEMA-001 (schema v2) → P2-DES-001 (physics panel), P2-DES-002 (material editor), P2-DES-003 (convergence assistant), P2-DES-004 (AC/transient views), P2-DES-005 (DOE manager), P2-DES-006 (MOSFET tutorial, examples) |

**Exit criteria (P2-GATE)**
1. Every phase-2 verification spec passes on both solvers; L3 comparison report written.
2. Convergence benchmark (`benchmarks/convergence/`, ≥ 20 hard cases) succeeds in ≥ 95 % of cases.
3. `scripts/check_citations.py --strict` passes.
4. MOSFET tutorial reproducible from GUI and CLI; DOE sweeps run in parallel workers.

## Critical paths
```
P1-SCHEMA-001 ─► P1-IO-001 ─► P1-RUN-001 ─► P1-SWEEP-001 ─► P1-DES-003/004 ─► P1-DOC-001 ─► P1-GATE
P1-SPEC-003 ─► P1-MESH-001 ─► P1-DD-002 ─► P1-MOS-001 ──────────────────────────────────────┘
P2-SPEC-010 ─► P2-CONV-001 ─► P2-VER-010 (benchmark ≥ 95 %) ─► P2-GATE
P2-SPEC-001..003 ─► P2-MOB-001..003 ─► P2-DEV-001 (MOSFET) ─► P2-DES-006 ─► P2-GATE
```
Researchers can work ahead on phase-2 specs while phase-1 code is built; the orchestrator
always prefers lower-phase work (`--max-phase 1` forbids working ahead).

## Later (not in the backlog yet)
3D structures; lattice heating (thermodynamic model); energy balance / hydrodynamic transport;
optical generation; trap dynamics and interface charge; process emulation (implant/diffusion
profiles); a stable Python API and installers. The designer proposes these as backlog items
in a planning issue when phase 2 nears its gate.

## Tracking progress
* `uv run python scripts/orchestrate.py --status` — sessions, next items, PR review queue,
  items waiting for you.
* GitHub milestones "Phase 1" / "Phase 2" — open vs closed issues.
* `reports/verification/` — per-spec reports and gate reports.
