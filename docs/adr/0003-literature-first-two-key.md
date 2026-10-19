# 0003 — Literature-first specs and the two-key rule

Status: accepted (2026-10-19)

## Context
Language-model agents can produce plausible but wrong equations and parameter values. A device
simulator with wrong constants is worse than no simulator.

## Decision
* Physics enters the code base only through specs with source ids and locators.
* Every extracted value or equation is confirmed by an independent, blind second reading
  (verifier + `source-checker` subagent) before it is `checked`/`reviewed`.
* The material database enforces statuses at runtime (`dev` vs `strict` policy), and
  `scripts/check_citations.py` enforces them in CI (`--strict` at phase gates).

## Consequences
* Slower than writing code from memory; paywalled sources need the human.
* Every number shown in the GUI can display its source and status.
