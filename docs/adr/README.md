# Architecture decision records

One file per decision that constrains other roles: `NNNN-short-title.md` with Context, Decision,
Consequences, Status (proposed | accepted | superseded by NNNN). The designer role writes them;
the human accepts them by merging.

| ADR | Decision | Status |
|---|---|---|
| [0001](0001-devsim-solver-core.md) | DEVSIM is the PDE engine; one simulation per process | accepted |
| [0002](0002-github-issues-task-queue.md) | GitHub issues/PRs are the agents' task queue | accepted |
| [0003](0003-literature-first-two-key.md) | Literature-first specs and the two-key rule | accepted |
| [0004](0004-gmsh-separate-process.md) | Gmsh runs as a separate process | accepted |
| [0005](0005-roles-as-skills.md) | Agent roles are skills, not custom system prompts | accepted |
| [0006](0006-extended-precision-default.md) | Extended precision is the default arithmetic (KI-006) | accepted |
