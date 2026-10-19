# open_tcad — instructions for every agent

Open TCAD is a semiconductor device simulator with a GUI, built on DEVSIM. Four agent roles
develop it in parallel: **research → implement ∥ verify → design**. Accuracy beats speed:
every physical number must trace to a source you actually read.

## Golden rules
1. **Literature first.** No physics code without a merged spec in `specs/`. Every equation and
   parameter carries `source` (id in `src/opentcad/data/references.yaml`) + `locator`
   (equation/table/page). Never write a value from memory. Details: `docs/literature-policy.md`.
2. **Two keys.** A value or equation extracted by one role is confirmed independently by the
   verifier before it counts as `checked`/`reviewed`. The extractor never checks its own work.
3. **Verification is independent.** Verification tests are written from the spec and source,
   not from the implementation. Never loosen a tolerance to make a test pass. Details:
   `docs/verification-policy.md`.
4. **Clean room.** Never copy code from GPL projects (e.g. Genius-TCAD-Open) into this
   Apache-2.0 repository, never reverse-engineer commercial TCAD tools or reuse their manuals'
   text. Implement from the original papers.
5. **Stay in your lane.** Each role edits only its own areas (table below). Need something
   elsewhere? Open an issue for the owning role instead of editing.
6. **Small PRs, one issue each.** Never push to `main`, never force-push, never merge. The human
   merges after CI and verifier approval (or the human-run orchestrator with `--auto-merge`).
7. **No attribution lines.** Commits, PRs, issues and comments carry no `Co-Authored-By`
   trailers, "Generated with" footers, session links or 🤖 markers (the tool's own attribution
   is off in `.claude/settings.json`). Commits use the owner's local git identity; never change
   `user.name` or `user.email`.

## Roles, skills and write scope
| Role | Skill | May edit | Typical output |
|---|---|---|---|
| researcher | `/role-research <issue>` or `pr:<n>` | `specs/`, `src/opentcad/data/`, `literature/` notes | spec drafts, references, material values (`extracted`) |
| implementer | `/role-implement <issue>` or `pr:<n>` | `src/opentcad/` (not `data/`, `gui/`, `project/`, `verification/`), `tests/unit/`, spec front matter `implemented_in`/`status` | model code + unit tests |
| verifier | `/role-verify <issue>` or `pr:<n>` | `tests/verification/`, `specs/verification/`, `src/opentcad/verification/`, `reports/`, status/`checked_by`/review-log fields | verification specs/tests, PR reviews, two-key checks |
| designer | `/role-design <issue>` or `pr:<n>` | `src/opentcad/gui/`, `src/opentcad/project/` (schema), `examples/`, `tests/gui/`, `docs/`, `.github/backlog/` | GUI, ADRs, schema, docs, backlog grooming |

Work queue = GitHub issues labeled `role:<role>` + `status:ready` whose `Depends on:` issues are
closed; `uv run python scripts/orchestrate.py --next <role>` prints the next item. Full protocol:
`docs/agent-workflow.md`. Shared tooling (`scripts/`, `.github/workflows/`, `.claude/`,
`pyproject.toml`) changes only through a designer PR that the human approves.

## Commands
```bash
uv sync --extra dev                         # first thing in every new worktree
uv run pytest -q -m "not gui"               # unit + verification (~30 s)
uv run pytest -q -m verification            # physics verification only
OPENTCAD_SOLVER=umfpack uv run pytest -q    # same, without MKL PARDISO
uv run ruff check . && uv run ruff format --check .
uv run python scripts/check_citations.py    # provenance of data/specs (--online: Crossref DOI check)
uv run python scripts/doi_lookup.py <doi>   # verified bibliography entry for references.yaml
uv run python scripts/snapshot_gui.py --out docs/design/snapshots/<name>.png   # needs [gui] extra
uv run opentcad info | models | demo-diode
uv run python scripts/orchestrate.py --next <role>   # next work item for a role (status: --status)
```

## Architecture map (details: `docs/architecture.md`)
- `src/opentcad/_devsim.py` — the only place that imports DEVSIM; `reset()` after every device build in tests.
  Solver (`OPENTCAD_SOLVER`) and precision (`OPENTCAD_PRECISION`, default extended: KI-006) survive resets.
- `physics/` — one module per model family (auto-discovered); each registers a `ModelInfo` with spec id + sources.
  Use `physics/_dsmodel.Region` (declares derivatives) and `num()` for numeric literals (KI-003).
- `materials/` + `data/materials/*.yaml` — parameters with status `needs-source|extracted|checked|conflict`.
- `devices/`, `mesh/`, `solver/` — builders and solve orchestration.
- `verification/analytic.py` — closed-form references; never import DEVSIM there. Verification tests
  for models that do not exist yet use `@pytest.mark.requires_model("<model id>")` and skip.
- `gui/` — PySide6; DEVSIM runs in a worker process, never in the GUI process.

## Definition of done (any PR)
- Linked issue; scope within the role's write area; spec/ADR references in the PR body.
- `ruff`, `pytest -m "not gui"` and `check_citations.py` pass locally.
- New numbers: source + locator + status. New models: spec id, registry entry, unit tests.
- Known pitfalls checked: `docs/known-issues.md`.

## When blocked
Comment on the issue with what is missing, add `status:needs-human`, remove `status:in-progress`,
and stop. Inaccessible papers, conflicting sources and design trade-offs are human decisions.
