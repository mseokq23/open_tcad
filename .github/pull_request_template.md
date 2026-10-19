<!-- Title: [<role>] #<issue> <summary> -->
Closes #

## Role and scope
- Role: research | implement | verify | design
- Files stay inside the role's write area (CLAUDE.md): yes / no (explain)

## What changed
-

## Specs, ADRs and sources
<!-- Spec/ADR ids. For every value or equation added: source id + locator + status. -->
| Item | Source | Locator | Status |
|---|---|---|---|

## Checks run
- [ ] `uv run ruff check . && uv run ruff format --check .`
- [ ] `uv run pytest -q -m "not gui"`
- [ ] `OPENTCAD_SOLVER=umfpack uv run pytest -q -m verification` (physics/solver changes)
- [ ] `uv run python scripts/check_citations.py`
- [ ] GUI: `uv run pytest -q -m gui` and snapshot attached

## Verification impact
<!-- Which verification tests now run, observed errors vs tolerances, anything skipped. -->

## Notes for the reviewer
<!-- Open questions, risky spots, where to look first. -->
