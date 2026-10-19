# Agent workflow

Four Claude Code sessions run in parallel, one per role, each in its own git worktree. GitHub
issues are the shared task queue; pull requests are the hand-off; the human (or the
human-run orchestrator) merges.

```
           ┌──────────── GitHub issues (role:*, status:*) ────────────┐
           │                                                          │
   researcher ──spec PR──► verifier (two-key review) ──► merge ───────┤
                                                                      ├─► impl issue + verification issue become ready
   implementer ◄──────────────────────────────────────────────────────┤        (run in parallel)
   implementer ──code PR──► verifier (spec conformance + tests) ──► merge
   designer ──GUI/ADR/docs PR──► verifier (CI, scope) ──► merge
   verifier ──VER spec/tests PR──► human ──► merge
```

## 1. Labels (created by `scripts/bootstrap_github.py`)
| Group | Labels |
|---|---|
| role | `role:research`, `role:implement`, `role:verify`, `role:design` |
| status | `status:ready`, `status:in-progress`, `status:review`, `status:blocked`, `status:needs-human` |
| review (PRs) | `review:verify`, `review:changes`, `review:approved`, `review:human` |
| phase | `phase:1`, `phase:2` |
| area | `area:physics`, `area:materials`, `area:mesh`, `area:solver`, `area:gui`, `area:verification`, `area:infra`, `area:docs` |
| type | `type:spec`, `type:feature`, `type:verification`, `type:design`, `type:bug`, `type:planning` |
| priority | `priority:high` (dispatched first) |

Issue bodies start with these lines, which the orchestrator and the skills parse:
```
Backlog-ID: P2-MOB-001
Depends on: #12, #15
Spec: MOD-MOB-001
```
An issue is workable when it is open, has `role:<role>` + `status:ready`, none of
`status:in-progress|review|blocked|needs-human`, and every `Depends on:` issue is closed.

## 2. Lifecycle of one feature (example: Masetti mobility)
1. `P2-SPEC-001` (role:research) → researcher completes `specs/models/MOD-MOB-001.md` and the
   material values (`extracted`) → PR labeled `review:verify`.
2. Verifier (PR mode): re-reads every equation and value **without seeing the claimed values**
   (the `source-checker` subagent gets only source, locator and quantity) → marks values
   `checked`, spec `reviewed` → `review:approved` → merge → the SPEC issue closes.
3. Two issues that depended on the SPEC issue become ready at the same time:
   * `P2-MOB-001` (role:implement): code + unit tests, PR labeled `review:verify`.
   * `P2-VER-001` (role:verify): verification spec + tests written from the spec and paper only;
     tests skip until the model is registered (`@pytest.mark.requires_model("<model id>")`,
     handled in `tests/conftest.py`). Merged first.
4. Verifier reviews the IMPL PR: equations term by term against the spec, the independent
   verification tests now run and must pass on both solvers → `review:approved` → merge.
5. Designer exposes the model in the GUI (model browser shows citations and status).

## 3. Claiming and branches
* Claim: `gh issue edit <n> --add-label status:in-progress --remove-label status:ready` and a
  comment `Claimed by <role> session.`
* Branch from fresh `origin/main`: `research/<n>-<slug>`, `implement/<n>-<slug>`,
  `verify/<n>-<slug>`, `design/<n>-<slug>`. The prefix tells the orchestrator who wrote a PR.
* Working on a PR branch (review fixes, status edits): never `gh pr checkout` (the author's
  worktree may still hold the branch). Use
  `git fetch origin pull/<pr>/head:pr-<pr> && git switch pr-<pr>` and push with
  `git push origin HEAD:<headRefName>`. Update a pushed branch with `git merge origin/main`
  (force pushes are denied, so never rebase a pushed branch).
* Commits: Conventional Commits (`spec:`, `data:`, `feat:`, `fix:`, `test:`, `docs:`, `ci:`),
  made with the owner's git identity and without attribution lines (CLAUDE.md rule 7;
  `attribution` is switched off in `.claude/settings.json`).
* PR title `[<role>] #<issue> <summary>`; body from `.github/pull_request_template.md` with
  `Closes #<issue>`, so merging closes the issue and unblocks its dependents.

## 4. Review routing
All agents act through one GitHub account, and GitHub does not let an account approve its own
PR. Review decisions are therefore **PR comments + labels**, never GitHub review states.

| PR author (branch prefix) | Label on open | Reviewer | After approval |
|---|---|---|---|
| `research/` | `review:verify` | verifier (two-key) | `review:approved` → merge |
| `implement/` | `review:verify` | verifier (conformance + tests) | `review:approved` → merge |
| `design/` | `review:verify` | verifier (CI, scope, docs accuracy) | `review:approved` → merge |
| `verify/` | `review:human` | human (CI must be green) | human merges |

Changes requested → `review:changes`; the orchestrator re-dispatches the author role with
`pr:<n>` before it takes new work. The author fixes, pushes and sets `review:verify` again.

## 5. Running the agents
Prerequisites (once): `uv`, `gh auth login`, Claude Code, run `claude` once in the repository
root and accept the workspace-trust dialog, then `uv run python scripts/bootstrap_github.py`.
See `docs/getting-started.ko.md` for the full first-day walkthrough.

### Level 1 — manual (start here, days 1–3)
In four terminals at the repository root:
```bash
claude --worktree research-12      # then type: /role-research 12
claude --worktree implement-14     # then type: /role-implement 14
claude --worktree verify-13        # then type: /role-verify 13     (or /role-verify pr:21)
claude --worktree design-20        # then type: /role-design 20
```
A role skill without an argument picks the next item itself (`scripts/orchestrate.py --next`).
Or dispatch background sessions you can watch in one screen:
```bash
claude --bg --name research-12 "/role-research 12"
claude agents                       # agent view: peek, reply, attach
```
Background sessions move into their own worktree under `.claude/worktrees/` before editing.

### Level 2 — orchestrated (after the pipeline has worked a few times)
```bash
uv run python scripts/orchestrate.py --status           # who is doing what, what is next
uv run python scripts/orchestrate.py --dry-run --once   # what would be dispatched now
uv run python scripts/orchestrate.py                    # loop every 120 s: keep 4 roles busy
```
The orchestrator keeps at most one session per role and picks work in this order: the role's
PRs with `review:changes`; then (verifier only) PRs with `review:verify`; then workable issues
(`priority:high` first, then lower phase, then lower number). It dispatches
`claude --bg --name otcad-<role>-<item>-<k> "/role-<role> <item>"` and polls
`claude agents --json --all`. Sessions waiting on you (`blocked`) are reported with the
`claude attach` command. When a session ends without a PR or a recorded blocker, the item is
labeled `status:needs-human`; an item whose sessions failed twice is not re-dispatched.

Useful options: `--max-phase 1` (finish phase 1 first), `--roles verify,implement`,
`--permission-mode auto` (if your plan offers auto mode), `--cleanup` (remove finished
sessions and their clean worktrees).

### Level 3 — auto-merge (optional, once you trust the verifier)
`uv run python scripts/orchestrate.py --auto-merge` squash-merges PRs labeled
`review:approved` when GitHub reports them mergeable and every CI check passed. Approved PRs
that conflict with `main` go back to the author as `review:changes`. `review:human` PRs
(verifier work, gate reports) always stay manual.

## 6. Human checkpoints
1. **Daily:** merge `review:approved` / `review:human` PRs with green CI (unless Level 3).
2. **On notification:** issues/PRs labeled `status:needs-human`: paywalled paper → put the PDF
   in `literature/pdfs/<reference-id>.pdf` (see `literature/README.md`); source conflict →
   decide and comment; design trade-off → decide; stalled session → `claude attach`/`claude logs`.
   Then remove `status:needs-human` and set `status:ready` (or the right review label).
3. **Backlog changes:** after a designer PR changes `.github/backlog/*.yaml`, run
   `uv run python scripts/bootstrap_github.py` again (idempotent).
4. **Phase gate:** the verifier's gate issue (`P1-GATE`, `P2-GATE`) produces
   `reports/verification/phase-<k>.md`; `uv run python scripts/check_citations.py --strict` and
   the full suite pass on both solvers; you sign off and close the milestone.

## 7. Cost and safety notes
* Four sessions use subscription quota about four times as fast as one; the verifier is the
  natural bottleneck, so review PRs promptly.
* `.claude/settings.json` pre-approves routine commands (uv, git without force, gh issue/pr,
  web research) and denies force pushes, pushes to `main`, merges, repo/release/secret changes
  and `rm -rf`. Allowing `uv run python …` lets agents run arbitrary Python in the project
  environment: run agents on a machine and account without secrets you cannot afford to expose.
* The real guard is **branch protection on `main`**, applied by
  `uv run python scripts/bootstrap_github.py --protect --labels-only`: pull request required,
  CI checks `lint`, `provenance`, `test (mkl_pardiso)`, `test (umfpack)` required, enforced for
  admins too (agents act through the owner's account), no force pushes or deletion, no required
  approvals (one shared account cannot approve its own PRs), merged branches deleted.
* Run the agents on your own computer with your own `gh` login. GitHub shows a "via" marker
  on issues, PRs and comments created through a cloud session's GitHub app connection.
* Simulations run on your CPU. The project settings set `MKL_NUM_THREADS=2` for agent sessions;
  lower it to 1 on machines with few cores.
