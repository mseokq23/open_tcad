"""Keep the four role agents busy: dispatch Claude Code background sessions for ready work.

Level 2 of docs/agent-workflow.md. Run it from the repository root (a trusted workspace):

    uv run python scripts/orchestrate.py --status              # sessions and queue, then exit
    uv run python scripts/orchestrate.py --dry-run --once      # what would be dispatched now
    uv run python scripts/orchestrate.py                       # loop: re-check every 120 s
    uv run python scripts/orchestrate.py --next verify         # next item for one role (used by the skills)

Each dispatch runs ``claude --bg --name <prefix>-<role>-<item>-<k> "/role-<role> <item>"``.
Background sessions move into their own git worktree under .claude/worktrees/ before editing.
Session states are read from ``claude agents --json --all`` (working, blocked, done, failed,
stopped). Local state lives in .orchestrator/state.json (git-ignored). GitHub is accessed
through the REST API with the gh CLI.

Safety: agents never merge. ``--auto-merge`` lets *this script* squash-merge PRs that the
verifier labeled ``review:approved`` once every CI check passed; ``review:human`` PRs and phase
gates stay manual.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from agentlib import (
    REPO_ROOT,
    ROLES,
    GhError,
    Snapshot,
    WorkItem,
    add_labels,
    comment,
    gh_api,
    label_names,
    remove_label,
    select_next,
)

STATE_FILE = REPO_ROOT / ".orchestrator" / "state.json"
TERMINAL_STATES = {"done", "failed", "stopped"}
GRACE_SECONDS = 300  # a new session may take a moment to appear in `claude agents --json`
OK_CONCLUSIONS = {"success", "neutral", "skipped"}


def now() -> float:
    return time.time()


def stamp(t: float | None = None) -> str:
    return datetime.fromtimestamp(t or now(), tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")


def log(message: str) -> None:
    print(f"[{stamp()}] {message}", flush=True)


# ── state ──────────────────────────────────────────────────────────────────────────────────
def load_state(path: Path = STATE_FILE) -> dict:
    state = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    state.setdefault("dispatches", [])
    state.setdefault("failures", {})
    return state


def save_state(state: dict, path: Path = STATE_FILE) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")


def open_dispatches(state: dict) -> list[dict]:
    return [d for d in state["dispatches"] if not d.get("finished")]


def excluded_items(state: dict, max_retries: int) -> set[str]:
    excluded = {d["item"] for d in open_dispatches(state)}
    excluded |= {item for item, n in state["failures"].items() if n >= max_retries}
    return excluded


# ── Claude Code ────────────────────────────────────────────────────────────────────────────
def claude_sessions() -> dict[str, dict]:
    """Background sessions started under this repository, keyed by session name."""
    if shutil.which("claude") is None:
        raise RuntimeError("Claude Code CLI `claude` not found on PATH")
    result = subprocess.run(
        ["claude", "agents", "--json", "--all", "--cwd", str(REPO_ROOT)],
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    if result.returncode != 0:
        raise RuntimeError(
            "`claude agents --json --all` failed (update Claude Code if the option is unknown): "
            + (result.stderr.strip() or result.stdout.strip())
        )
    sessions: dict[str, dict] = {}
    for entry in json.loads(result.stdout or "[]"):
        name = entry.get("name")
        if not name or entry.get("kind", "background") != "background":
            continue
        # keep the most recently started session for a name
        if name not in sessions or entry.get("startedAt", 0) >= sessions[name].get("startedAt", 0):
            sessions[name] = entry
    return sessions


def session_name(state: dict, prefix: str, work: WorkItem) -> str:
    base = f"{prefix}-{work.role}-{work.session_suffix}"
    previous = sum(1 for d in state["dispatches"] if d["name"].startswith(base + "-"))
    return f"{base}-{previous + 1}"


def dispatch_command(work: WorkItem, name: str, args: argparse.Namespace) -> list[str]:
    cmd = ["claude", "--bg", "--name", name]
    if args.permission_mode:
        cmd += ["--permission-mode", args.permission_mode]
    if args.model:
        cmd += ["--model", args.model]
    cmd.append(f"/role-{work.role} {work.item}")
    return cmd


# ── GitHub side effects ────────────────────────────────────────────────────────────────────
def flag_for_human(slug: str, number: int, message: str, labels: set[str], dry_run: bool) -> None:
    log(f"needs-human #{number}: {message}")
    if dry_run:
        return
    body = f"orchestrator: {message}\n\nLabeled `status:needs-human` (docs/agent-workflow.md §6)."
    try:
        comment(slug, number, body)
        add_labels(slug, number, ["status:needs-human"])
        if "status:in-progress" in labels:
            remove_label(slug, number, "status:in-progress")
    except GhError as exc:
        log(f"warning: could not flag #{number}: {exc}")


def pr_mentions_issue(pr: dict, number: int) -> bool:
    """True when the PR body references #<number> (not #<number>0…) or its branch is <role>/<number>-…."""
    in_body = re.search(rf"#{number}(?!\d)", pr.get("body") or "") is not None
    return in_body or f"/{number}-" in pr.get("headRefName", "")


def post_check(dispatch: dict, snap: Snapshot, dry_run: bool) -> None:
    """After a session ends, make sure it left its item in a hand-off state."""
    item, role, final = dispatch["item"], dispatch["role"], dispatch.get("final_state")
    if item.startswith("pr:"):
        number = int(item[3:])
        pr = next((p for p in snap.prs if p["number"] == number), None)
        if pr is None:
            return  # merged or closed meanwhile
        labels = label_names(pr)
        reviewing = role == "verify" and not pr["headRefName"].startswith("verify/")
        waiting = "review:verify" if reviewing else "review:changes"
        if waiting in labels and "status:needs-human" not in labels:
            flag_for_human(
                snap.slug,
                number,
                f"session `{dispatch['name']}` ended ({final}) but the PR still has `{waiting}`.",
                labels,
                dry_run,
            )
        return
    number = int(item)
    issue = next((i for i in snap.issues if i["number"] == number), None)
    if issue is None or issue["state"] != "OPEN":
        return
    labels = label_names(issue)
    if labels & {"status:review", "status:needs-human", "status:blocked"}:
        return
    if any(pr_mentions_issue(pr, number) for pr in snap.prs):
        return
    if "status:in-progress" in labels or final != "done":
        flag_for_human(
            snap.slug,
            number,
            f"session `{dispatch['name']}` ended ({final}) without opening a PR or recording a "
            "blocker. Inspect it with `claude attach <id>` or `claude logs <id>`.",
            labels,
            dry_run,
        )


def merge_readiness(slug: str, pr: dict) -> tuple[bool, str]:
    """(ready, reason) for an approved PR: mergeable, no conflicts, all check runs green."""
    info = gh_api(f"repos/{slug}/pulls/{pr['number']}")
    if info.get("draft"):
        return False, "draft"
    state = info.get("mergeable_state")
    if state == "dirty":
        return False, "conflict"
    if info.get("mergeable") is not True or state not in ("clean", "unstable", "has_hooks"):
        return False, f"mergeable={info.get('mergeable')} state={state}"
    sha = info["head"]["sha"]
    runs = gh_api(f"repos/{slug}/commits/{sha}/check-runs?per_page=100").get("check_runs", [])
    if not runs:
        return False, "no CI check runs reported"
    for run in runs:
        if run.get("status") != "completed":
            return False, f"check {run.get('name')}: {run.get('status')}"
        if (run.get("conclusion") or "") not in OK_CONCLUSIONS:
            return False, f"check {run.get('name')}: {run.get('conclusion')}"
    return True, "green"


def auto_merge(snap: Snapshot, dry_run: bool) -> None:
    for pr in sorted(snap.prs, key=lambda p: p["number"]):
        labels = label_names(pr)
        if "review:approved" not in labels or labels & {"review:human", "status:needs-human"}:
            continue
        try:
            ready, why = merge_readiness(snap.slug, pr)
        except GhError as exc:
            log(f"warning: cannot inspect PR #{pr['number']}: {exc}")
            continue
        if why == "conflict":
            log(f"PR #{pr['number']} conflicts with main -> review:changes")
            if not dry_run:
                comment(
                    snap.slug,
                    pr["number"],
                    "orchestrator: approved but conflicts with `main`. Author: "
                    "`git merge origin/main`, resolve, re-run the checks, push, then hand back "
                    "with `review:verify`.",
                )
                add_labels(snap.slug, pr["number"], ["review:changes"])
                remove_label(snap.slug, pr["number"], "review:approved")
            continue
        if not ready:
            log(f"PR #{pr['number']} approved, not merged yet: {why}")
            continue
        log(f"merge PR #{pr['number']} {pr.get('title', '')}")
        if not dry_run:
            gh_api(
                f"repos/{snap.slug}/pulls/{pr['number']}/merge",
                "PUT",
                {"merge_method": "squash", "sha": pr["headSha"]},
            )


# ── one round ──────────────────────────────────────────────────────────────────────────────
def reconcile(state: dict, sessions: dict[str, dict], snap: Snapshot, args) -> None:
    for d in open_dispatches(state):
        entry = sessions.get(d["name"])
        if entry is None:
            if now() - d["started"] > GRACE_SECONDS:
                d.update(finished=now(), final_state="lost")
                log(f"{d['name']}: no longer listed by `claude agents` -> lost")
                state["failures"][d["item"]] = state["failures"].get(d["item"], 0) + 1
            continue
        d["session_id"] = entry.get("id", d.get("session_id"))
        d["last_state"] = entry.get("state")
        if entry.get("state") not in TERMINAL_STATES:
            continue
        d.update(finished=now(), final_state=entry["state"])
        log(f"{d['name']}: {entry['state']} after {int((now() - d['started']) / 60)} min")
        if entry["state"] != "done":
            state["failures"][d["item"]] = state["failures"].get(d["item"], 0) + 1
        post_check(d, snap, args.dry_run)
        if args.cleanup and entry["state"] == "done" and d.get("session_id") and not args.dry_run:
            subprocess.run(["claude", "rm", d["session_id"]], check=False, timeout=120)


def run_round(state: dict, args: argparse.Namespace) -> None:
    sessions = claude_sessions()
    snap = Snapshot.fetch(args.repo)
    reconcile(state, sessions, snap, args)
    active = open_dispatches(state)
    for d in active:
        entry = sessions.get(d["name"], {})
        if entry.get("state") == "blocked":
            log(
                f"⚠ {d['name']} is waiting for you ({entry.get('waitingFor', 'input')}): "
                f"`claude attach {entry.get('id', '?')}` or open `claude agents`"
            )
    if args.auto_merge:
        auto_merge(snap, args.dry_run)
    busy = {d["role"] for d in active}
    exclude = excluded_items(state, args.max_retries)
    for role in args.roles:
        if role in busy:
            continue
        if len(active) >= args.max_sessions:
            break
        work = select_next(role, snap.issues, snap.prs, max_phase=args.max_phase, exclude=exclude)
        if work is None:
            log(f"{role}: idle (nothing ready)")
            continue
        name = session_name(state, args.prefix, work)
        cmd = dispatch_command(work, name, args)
        if args.dry_run:
            log(f"{role}: would dispatch {work.item} ({work.reason}): {' '.join(cmd)}")
            continue
        result = subprocess.run(
            cmd, cwd=REPO_ROOT, capture_output=True, text=True, check=False, timeout=180
        )
        if result.returncode != 0:
            message = (result.stderr or result.stdout).strip()
            log(f"{role}: dispatch failed: {message}")
            if "trust" in message.lower():
                log("hint: run `claude` once in the repository root and accept the trust dialog")
            continue
        record = {
            "name": name,
            "role": role,
            "item": work.item,
            "reason": work.reason,
            "started": now(),
            "started_at": stamp(),
            "output": result.stdout.strip()[:500],
        }
        state["dispatches"].append(record)
        active.append(record)
        exclude.add(work.item)
        log(f"{role}: dispatched {name} -> /role-{role} {work.item} ({work.reason})")
    if not args.dry_run:
        save_state(state)


def print_status(state: dict, args: argparse.Namespace) -> None:
    try:
        sessions = claude_sessions()
    except RuntimeError as exc:
        sessions = {}
        print(f"(sessions unavailable: {exc})")
    snap = Snapshot.fetch(args.repo)
    exclude = excluded_items(state, args.max_retries)
    print(f"repository {snap.slug}: {sum(i['state'] == 'OPEN' for i in snap.issues)} open issues")
    print(f"{'role':10} {'session':34} {'state':9} item / next")
    for role in ROLES:
        running = [d for d in open_dispatches(state) if d["role"] == role]
        if running:
            d = running[-1]
            st = sessions.get(d["name"], {}).get("state", "starting")
            age = int((now() - d["started"]) / 60)
            print(f"{role:10} {d['name']:34} {st:9} {d['item']}  ({age} min)")
            continue
        work = select_next(role, snap.issues, snap.prs, max_phase=args.max_phase, exclude=exclude)
        nxt = f"{work.item} — {work.reason}" if work else "nothing ready"
        print(f"{role:10} {'-':34} {'idle':9} next: {nxt}")
    counts: dict[str, int] = {}
    for pr in snap.prs:
        for label in label_names(pr):
            if label.startswith("review:"):
                counts[label] = counts.get(label, 0) + 1
    unlabeled = sum(
        1 for pr in snap.prs if not any(n.startswith("review:") for n in label_names(pr))
    )
    if unlabeled:
        counts["no review label"] = unlabeled
    summary = ", ".join(f"{k} {v}" for k, v in sorted(counts.items()))
    print(f"PRs: {len(snap.prs)} open" + (f" ({summary})" if summary else ""))
    human = [
        f"#{i['number']}"
        for i in snap.issues
        if i["state"] == "OPEN" and "status:needs-human" in label_names(i)
    ]
    human += [f"PR #{p['number']}" for p in snap.prs if "status:needs-human" in label_names(p)]
    print("needs-human:", ", ".join(human) or "none")
    if state["failures"]:
        print("failures:", ", ".join(f"{k}×{v}" for k, v in sorted(state["failures"].items())))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--once", action="store_true", help="run one round and exit")
    parser.add_argument("--dry-run", action="store_true", help="decide and print, change nothing")
    parser.add_argument("--status", action="store_true", help="print sessions and queue, then exit")
    parser.add_argument("--next", metavar="ROLE", choices=ROLES, help="print ROLE's next item")
    parser.add_argument("--repo", help="OWNER/NAME (default: $GH_REPO or the origin remote)")
    parser.add_argument("--roles", default=",".join(ROLES), help="comma-separated roles")
    parser.add_argument("--max-sessions", type=int, default=4, help="parallel sessions in total")
    parser.add_argument("--max-phase", type=int, default=2, help="ignore issues of later phases")
    parser.add_argument("--interval", type=int, default=120, help="seconds between rounds")
    parser.add_argument(
        "--max-retries", type=int, default=2, help="give up on an item after N failures"
    )
    parser.add_argument("--prefix", default="otcad", help="session name prefix")
    parser.add_argument(
        "--permission-mode", default=None, help="passed to `claude --bg` (e.g. auto)"
    )
    parser.add_argument("--model", default=None, help="passed to `claude --bg --model`")
    parser.add_argument(
        "--auto-merge", action="store_true", help="merge approved PRs with green CI"
    )
    parser.add_argument(
        "--cleanup", action="store_true", help="`claude rm` sessions that ended done"
    )
    args = parser.parse_args(argv)
    args.roles = [r.strip() for r in args.roles.split(",") if r.strip()]
    unknown = [r for r in args.roles if r not in ROLES]
    if unknown:
        parser.error(f"unknown role(s): {unknown}; choose from {ROLES}")

    state = load_state()
    errors = (GhError, RuntimeError, subprocess.TimeoutExpired, json.JSONDecodeError)
    try:
        if args.next:
            snap = Snapshot.fetch(args.repo)
            work = select_next(
                args.next,
                snap.issues,
                snap.prs,
                max_phase=args.max_phase,
                exclude=excluded_items(state, args.max_retries),
            )
            if work:
                print(work.item)
                print(work.reason, file=sys.stderr)
            return 0
        if args.status:
            print_status(state, args)
            return 0
        while True:
            try:
                run_round(state, args)
            except errors as exc:
                if args.once:
                    raise
                log(f"round failed, retrying in {args.interval} s: {exc}")
            if args.once:
                return 0
            time.sleep(args.interval)
    except errors as exc:
        log(f"error: {exc}")
        return 1
    except KeyboardInterrupt:
        if not args.dry_run:
            save_state(state)
        log("stopped; running sessions keep going (see `claude agents`)")
        return 0


if __name__ == "__main__":
    sys.exit(main())
