# 0005 — Agent roles are skills, not custom system prompts

Status: accepted (2026-10-19)

## Context
Claude Code can run a session as a custom agent (`--agent <name>`), but a custom agent's prompt
replaces Claude Code's default system prompt. Our roles need the default coding behaviour plus
a role procedure.

## Decision
* Each role is a project skill invoked explicitly: `/role-research`, `/role-implement`,
  `/role-verify`, `/role-design` (`.claude/skills/role-*/SKILL.md`, with
  `disable-model-invocation: true` so they never trigger on their own).
* Narrow helpers that benefit from isolation are subagents: `source-checker` (blind two-key
  re-reading of sources) and `gui-critic` (screenshot critique), in `.claude/agents/`.
* Shared rules live in `CLAUDE.md`, which every session loads.

## Consequences
* A background session is started with the skill as its first prompt:
  `claude --bg "/role-implement 14"`.
* Role procedures are versioned with the code and reviewed like code.
