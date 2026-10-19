# Architecture

## Layers
```
 GUI (PySide6, gui/)            CLI (cli.py)            scripts/, CI
        │  project file (YAML, core schema — P1-SCHEMA-001)  │
        ▼                                                    ▼
 Runner (worker process — P1-RUN-001): one simulation per process, streams progress, writes runs/<id>/
        │
        ▼
 devices/  ─ builds structure + mesh + doping + physics from a project description
 mesh/     ─ 1D: DEVSIM mesher · 2D/3D: Gmsh as a separate process (ADR-0004)
 physics/  ─ model builders (one module per family) + registry (spec id, sources)
 solver/   ─ equilibrium → drift-diffusion → bias sweeps; convergence strategies (phase 2)
 materials/ + data/ ─ parameters with provenance and status gates
 units.py, literature.py ─ CODATA constants, bibliography
        │
        ▼
 _devsim.py ─ the only DEVSIM import; solver + precision selection survive reset_devsim()
```

## Key constraints
* **DEVSIM state is process-global.** One simulation per process. The GUI never imports DEVSIM;
  it talks to a worker (P1-RUN-001). Tests call `opentcad._devsim.reset()` before building a device.
* **Derivatives are explicit.** DEVSIM builds the Jacobian from `<model>:<var>` models; a missing
  one is silently zero. Declare models through `physics._dsmodel.Region` with `wrt=[...]`.
* **Numeric literals** in expressions go through `num()` (KI-003).
* **Units:** cm, s, V, K, cm^-3, A/cm^2 inside DEVSIM. Convert at the boundary (`units.py`).
* **Provenance travels with data.** Material values are read through `MaterialDB.value()`, which
  enforces status policies; models register their spec id and sources.

## Module ownership (who edits what)
| Path | Owner role |
|---|---|
| `src/opentcad/physics`, `solver`, `devices`, `mesh`, `materials/db.py` | implementer |
| `src/opentcad/data/` (references, materials, constants) | researcher (status fields: verifier) |
| `src/opentcad/verification/`, `tests/verification/`, `specs/verification/`, `reports/` | verifier |
| `src/opentcad/gui/`, `src/opentcad/project/` (schema), `examples/`, `tests/gui/`, `docs/`, `docs/adr/`, `.github/backlog/` | designer |
| `specs/models/`, `specs/materials/` | researcher (review log: verifier; `implemented_in`: implementer) |
| `scripts/`, `.github/workflows/`, `.claude/`, `pyproject.toml` | designer (architecture) with human approval |

## Data formats
* Project file (phase 1): YAML validated by a pydantic schema; JSON Schema exported for the GUI
  property editor and for agents.
* Results: `runs/<id>/` with `run.yaml` (inputs + versions + git hash), `iv.csv`, `fields/*.vtu`
  (DEVSIM `write_devices(type="vtk")`), `log.txt`.

## Planned extensions (see roadmap)
Gmsh 2D meshing, insulator regions and gate contacts, worker runner, schema, GUI editors and
viewers (phase 1); statistics, mobility, recombination, BGN, impact ionization, BTBT, Schottky
contacts, density gradient, AC/transient, DOE, convergence strategies (phase 2).
