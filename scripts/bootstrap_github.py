"""Create labels, milestones and backlog issues on GitHub from .github/backlog/*.yaml.

Idempotent: an issue whose body has ``Backlog-ID: <id>`` is never created twice. Issues are
created in dependency order so each body can reference its dependencies as ``#<number>``,
which is what the orchestrator and the role skills read.

    uv run python scripts/bootstrap_github.py --dry-run          # show the plan
    uv run python scripts/bootstrap_github.py                    # labels + milestones + all issues
    uv run python scripts/bootstrap_github.py --phase 1          # only phase-1 issues
    uv run python scripts/bootstrap_github.py --update           # also refresh bodies of existing issues
    uv run python scripts/bootstrap_github.py --protect --labels-only   # repo settings + main protection

Requires the GitHub CLI (``gh auth login``) with write access to the repository. Uses only the
REST API. The repository comes from --repo, $GH_REPO or the ``origin`` remote.
"""

from __future__ import annotations

import argparse
import sys
import time
import urllib.parse

from agentlib import (
    BACKLOG_DIR,
    REPO_ROOT,
    GhError,
    expand_dependencies,
    fetch_issues,
    gh_api,
    load_backlog,
    load_label_config,
    parse_issue_meta,
    render_issue_body,
    repo_slug,
    topological_order,
    validate_backlog,
)


def create_with_retry(path: str, payload: dict, attempts: int = 4) -> dict:
    """POST with back-off: GitHub limits content creation (secondary rate limit)."""
    for attempt in range(1, attempts + 1):
        try:
            return gh_api(path, "POST", payload)
        except GhError as exc:
            if "rate limit" not in str(exc).lower() or attempt == attempts:
                raise
            wait = 60 * attempt
            print(f"rate limited; waiting {wait} s before retrying", flush=True)
            time.sleep(wait)
    raise AssertionError("unreachable")


#: CI jobs that must pass before anything merges into main (.github/workflows/ci.yml).
REQUIRED_CHECKS = ("lint", "provenance", "test (mkl_pardiso)", "test (umfpack)")


def protect_main(slug: str, dry_run: bool) -> None:
    """Delete merged branches; protect main: PR + green CI, also for admins (agents use the
    owner's account), no force pushes or deletion, no required approvals (one shared account
    cannot approve its own PRs; review decisions are labels, docs/agent-workflow.md §4)."""
    protection = {
        "required_status_checks": {"strict": False, "contexts": list(REQUIRED_CHECKS)},
        "enforce_admins": True,
        "required_pull_request_reviews": {
            "required_approving_review_count": 0,
            "dismiss_stale_reviews": False,
            "require_code_owner_reviews": False,
        },
        "restrictions": None,
        "allow_force_pushes": False,
        "allow_deletions": False,
    }
    print("repo    delete_branch_on_merge=true")
    print(f"protect main: PR required, checks {', '.join(REQUIRED_CHECKS)}, admins included")
    if dry_run:
        return
    try:
        gh_api(f"repos/{slug}", "PATCH", {"delete_branch_on_merge": True})
        gh_api(f"repos/{slug}/branches/main/protection", "PUT", protection)
    except GhError as exc:
        # e.g. a token without admin rights, or a proxy that forbids settings writes
        print(
            f"WARNING: could not change repository settings ({exc}).\n"
            "  Run this command with an admin `gh auth login`, or set it by hand:\n"
            "  Settings > Branches > main (see docs/getting-started.ko.md §4).",
            file=sys.stderr,
        )
        return
    print("protect main: done")


def ensure_labels(slug: str, label_config: dict, dry_run: bool, offline: bool) -> None:
    existing = set()
    if not offline:
        existing = {
            lab["name"] for lab in gh_api(f"repos/{slug}/labels?per_page=100", paginate=True)
        }
    for label in label_config.get("labels", []):
        payload = {"color": label["color"], "description": label.get("description", "")}
        action = "update" if label["name"] in existing else "create"
        print(f"label   {label['name']} ({action})")
        if dry_run:
            continue
        if action == "create":
            create_with_retry(f"repos/{slug}/labels", {"name": label["name"], **payload})
        else:
            name = urllib.parse.quote(label["name"], safe="")
            gh_api(f"repos/{slug}/labels/{name}", "PATCH", payload)


def ensure_milestones(
    slug: str, label_config: dict, dry_run: bool, offline: bool
) -> dict[str, int]:
    numbers: dict[str, int] = {}
    if not offline:
        for milestone in gh_api(f"repos/{slug}/milestones?state=all&per_page=100", paginate=True):
            numbers[milestone["title"]] = milestone["number"]
    for milestone in label_config.get("milestones", []):
        title = milestone["title"]
        if title in numbers:
            print(f"milestone {title} (exists)")
            continue
        print(f"milestone {title} (create)")
        if not dry_run:
            created = gh_api(
                f"repos/{slug}/milestones",
                "POST",
                {"title": title, "description": milestone.get("description", "")},
            )
            numbers[title] = created["number"]
    return numbers


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--repo", help="OWNER/NAME (default: $GH_REPO or the origin remote)")
    parser.add_argument("--dry-run", action="store_true", help="print the plan, change nothing")
    parser.add_argument("--phase", choices=["1", "2", "all"], default="all")
    parser.add_argument("--labels-only", action="store_true", help="only labels and milestones")
    parser.add_argument("--update", action="store_true", help="rewrite bodies of existing issues")
    parser.add_argument("--limit", type=int, default=None, help="create at most N new issues")
    parser.add_argument("--pace", type=float, default=1.0, help="seconds between new issues")
    parser.add_argument(
        "--protect", action="store_true", help="also set repo settings and protect main"
    )
    args = parser.parse_args(argv)

    items = load_backlog()
    label_config = load_label_config()
    problems = validate_backlog(items, label_config)
    if problems:
        print("Backlog is invalid:\n  " + "\n  ".join(problems), file=sys.stderr)
        return 1
    deps = expand_dependencies(items)
    by_id = {item.id: item for item in items}

    offline = False
    try:
        slug = repo_slug(args.repo)
        gh_api(f"repos/{slug}")  # access check
    except GhError as exc:
        if not args.dry_run:
            print(exc, file=sys.stderr)
            return 1
        slug, offline = args.repo or "<repo>", True
        print(f"(offline dry run: {exc})")

    if args.protect:
        protect_main(slug, args.dry_run or offline)
    ensure_labels(slug, label_config, args.dry_run, offline)
    milestones = ensure_milestones(slug, label_config, args.dry_run, offline)
    if args.labels_only:
        return 0

    existing: dict[str, dict] = {}
    if not offline:
        for issue in fetch_issues(slug):
            backlog_id = parse_issue_meta(issue["body"]).get("backlog_id")
            if backlog_id:
                existing[backlog_id] = issue
    numbers: dict[str, int] = {bid: issue["number"] for bid, issue in existing.items()}
    created = 0
    placeholder = 100000  # fake numbers in dry runs, so dependent bodies still render
    for item_id in topological_order(items, deps):
        item = by_id[item_id]
        if args.phase != "all" and item.phase != int(args.phase):
            continue
        missing = [d for d in deps[item_id] if d not in numbers]
        if missing:
            print(f"skip    {item_id}: dependencies not on GitHub yet: {', '.join(missing)}")
            continue
        body = render_issue_body(
            item, [numbers[d] for d in deps[item_id]], f".github/backlog/phase{item.phase}.yaml"
        )
        title = f"[{item.id}] {item.title}"
        if item_id in existing:
            number = existing[item_id]["number"]
            if args.update and existing[item_id]["body"].strip() != body.strip():
                print(f"update  #{number} {title}")
                if not args.dry_run:
                    gh_api(f"repos/{slug}/issues/{number}", "PATCH", {"body": body})
            continue
        if args.limit is not None and created >= args.limit:
            print(f"limit   reached; not creating {item_id}")
            continue
        if args.dry_run:
            placeholder += 1
            numbers[item_id] = placeholder
            print(
                f"create  {title}  labels={','.join(item.labels())}  depends={deps[item_id] or '-'}"
            )
        else:
            payload = {"title": title, "body": body, "labels": item.labels()}
            if item.milestone in milestones:
                payload["milestone"] = milestones[item.milestone]
            numbers[item_id] = create_with_retry(f"repos/{slug}/issues", payload)["number"]
            print(f"created #{numbers[item_id]} {title}", flush=True)
            time.sleep(args.pace)  # stay well below GitHub's content-creation limits
        created += 1
    verb = "would be created" if args.dry_run else "created"
    print(f"done: {created} issue(s) {verb} from {BACKLOG_DIR.relative_to(REPO_ROOT)}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
