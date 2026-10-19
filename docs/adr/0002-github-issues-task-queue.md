# 0002 — GitHub issues and pull requests are the agents' task queue

Status: accepted (2026-10-19)

## Context
Four agents work in separate git worktrees on different branches. A task board stored in the
repository would diverge between branches. The human needs to follow progress from a phone.

## Decision
* Work items are GitHub issues with `role:*`, `status:*`, `phase:*` labels and
  `Backlog-ID` / `Depends on` lines (docs/agent-workflow.md).
* Hand-offs are pull requests with `review:*` labels. The human merges.
* `.github/backlog/*.yaml` is the source for creating issues (`scripts/bootstrap_github.py`),
  so the plan itself is versioned and reviewable.
* `scripts/orchestrate.py` dispatches Claude Code background sessions from the queue.

## Consequences
* Agents need an authenticated `gh` CLI.
* The queue survives restarts and is visible in the GitHub app.
