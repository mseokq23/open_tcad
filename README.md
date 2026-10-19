# open_tcad

[![CI](https://github.com/mseokq23/open_tcad/actions/workflows/ci.yml/badge.svg)](https://github.com/mseokq23/open_tcad/actions/workflows/ci.yml)

**Open TCAD** is an open-source semiconductor device simulator with a GUI, built on the
[DEVSIM](https://devsim.org) TCAD engine. Its rule is simple: every equation and every material
parameter traces to a source someone actually read, and a second, independent reader confirmed it.

Development follows an issue-driven workflow with four roles (research, implementation,
verification, design), coordinated through GitHub issues and pull requests; every change is
reviewed before it is merged. See [docs/agent-workflow.md](docs/agent-workflow.md).

## Status
Phase 0 (scaffold) is complete — see [docs/roadmap.md](docs/roadmap.md).

* 1D drift-diffusion: Poisson with Boltzmann statistics, Scharfetter-Gummel currents, SRH
  recombination, ideal ohmic contacts, step doping, bias sweeps with step control.
* Verified against closed-form PN-junction limits (VER-PN-001) with two direct solvers
  (MKL PARDISO and UMFPACK).
* Material database with provenance and status gates (`needs-source`, `extracted`, `checked`,
  `conflict`); CODATA 2022 constants; bibliography with Crossref-checked DOIs.
* GUI skeleton (PySide6) following the generic TCAD workflow.

Next: 2D structures with Gmsh, MOS capacitors, project files, a worker-process runner and GUI
editors/viewers (phase 1); mobility, recombination, statistics, impact ionization, tunneling,
Schottky contacts, convergence automation, AC/transient and parameter sweeps (phase 2).

## Quick start
Requires [uv](https://docs.astral.sh/uv/) and Python 3.10–3.13 (3.12 recommended). Linux x86-64
or Windows x86-64 get BLAS/PARDISO from the `mkl` package; elsewhere see
[docs/known-issues.md](docs/known-issues.md) (KI-002).

```bash
uv sync --extra dev                    # create .venv with DEVSIM, MKL and dev tools
uv run opentcad info                   # versions, active solver, material status
uv run opentcad demo-diode --vmax 0.6  # 1D PN diode I-V
uv run pytest -q -m "not gui"          # unit + verification tests (~30 s)
OPENTCAD_SOLVER=umfpack uv run pytest -q -m verification   # same physics, other solver

uv sync --extra dev --extra gui        # GUI dependencies
uv run opentcad gui
```

## Repository layout
```
src/opentcad/         simulator package (DEVSIM wrapper, physics, materials, solver, GUI)
  data/               references.yaml, constants.yaml, materials/*.yaml  (provenance + status)
specs/                model, material and verification specs (the contract between roles)
tests/                unit/, verification/, gui/
reports/verification/ verification and phase-gate reports
literature/           reading notes (tracked) and source PDFs (local only, git-ignored)
docs/                 architecture, policies, roadmap, ADRs, design guide, getting started
scripts/              orchestrator, GitHub bootstrap, citation checker, DOI lookup, snapshots
.claude/              role procedures, helper definitions and tool permissions
.github/              CI, issue/PR templates, backlog (phase1.yaml, phase2.yaml)
```

## Working on it
* Project rules: [CLAUDE.md](CLAUDE.md).
* Policies: [literature](docs/literature-policy.md), [verification](docs/verification-policy.md),
  [design](docs/design-guide.md), [architecture](docs/architecture.md), [ADRs](docs/adr/).
* Getting started (Korean): [docs/getting-started.ko.md](docs/getting-started.ko.md).

## License and notices
Apache License 2.0 — see [LICENSE](LICENSE).

* DEVSIM is a separate project (Apache-2.0) used as a dependency. Open TCAD is not affiliated
  with or endorsed by DEVSIM LLC; "DEVSIM" is used only to describe that dependency.
* Gmsh (GPL) is an optional tool that Open TCAD runs as a separate process; it is never linked
  into this code base ([ADR-0004](docs/adr/0004-gmsh-separate-process.md)).
* No code, text, parameter files or documentation from commercial TCAD products or GPL
  simulators is used. Models are implemented from the original publications, cited in
  `src/opentcad/data/references.yaml`.
