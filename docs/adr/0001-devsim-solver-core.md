# 0001 — DEVSIM is the PDE engine; one simulation per process

Status: accepted (2026-10-19)

## Context
We need a finite-volume semiconductor PDE engine with a Python API, user-defined models,
DC/AC/noise/transient analyses and an Apache-compatible licence. DEVSIM (Apache-2.0) provides
these, with symbolic derivatives (SYMDIFF) and 1D/2D/3D support. Its state is process-global.

## Decision
* DEVSIM is the only PDE engine. All access goes through `src/opentcad/_devsim.py`.
* One simulation per process: the GUI runs simulations in a worker process; tests reset DEVSIM
  before each device.
* Physics is written as DEVSIM model expressions in `physics/`, one module per model family.

## Consequences
* Parallel sweeps use multiple processes, not threads.
* Large 3D problems are limited by DEVSIM's shared-memory direct solvers; MPI-scale work would
  need another engine (out of scope for phases 1–2).
* We track DEVSIM releases and pin dependencies that break it (KI-001).
