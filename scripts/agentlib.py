"""Shared logic for the agent tooling (bootstrap_github.py, orchestrate.py).

Pure functions here are unit-tested in tests/unit/test_agentlib.py; everything that talks to
GitHub goes through :func:`gh`, so the selection logic can be tested with plain dicts.
Protocol: docs/agent-workflow.md.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import urllib.parse
from dataclasses import dataclass, field
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKLOG_DIR = REPO_ROOT / ".github" / "backlog"
ROLES = ("research", "implement", "verify", "design")
#: Labels that take an issue out of the queue even if it still says status:ready.
NOT_READY = ("status:in-progress", "status:review", "status:blocked", "status:needs-human")
ID_PATTERN = re.compile(r"^P\d+-[A-Z0-9]+(-[A-Z0-9]+)*$")


# ── backlog files ──────────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class BacklogItem:
    id: str
    title: str
    role: str
    area: str
    type: str
    phase: int
    milestone: str
    depends: tuple[str, ...] = ()
    depends_on_phase: int | None = None
    priority: str | None = None
    spec: str | None = None
    notes: str = ""
    acceptance: tuple[str, ...] = ()

    def labels(self) -> list[str]:
        labels = [
            f"role:{self.role}",
            "status:ready",
            f"phase:{self.phase}",
            f"area:{self.area}",
            f"type:{self.type}",
        ]
        if self.priority == "high":
            labels.append("priority:high")
        return labels


def load_backlog(paths: list[Path] | None = None) -> list[BacklogItem]:
    """Read every ``phase*.yaml`` backlog file (sorted by name) into items."""
    files = paths if paths is not None else sorted(BACKLOG_DIR.glob("phase*.yaml"))
    items: list[BacklogItem] = []
    for file in files:
        raw = yaml.safe_load(Path(file).read_text(encoding="utf-8"))
        phase = int(raw["phase"])
        milestone = str(raw.get("milestone") or f"Phase {phase}")
        for entry in raw.get("items") or []:
            items.append(
                BacklogItem(
                    id=str(entry["id"]),
                    title=str(entry["title"]),
                    role=str(entry["role"]),
                    area=str(entry["area"]),
                    type=str(entry["type"]),
                    phase=phase,
                    milestone=milestone,
                    depends=tuple(str(d) for d in (entry.get("depends") or [])),
                    depends_on_phase=entry.get("depends_on_phase"),
                    priority=entry.get("priority"),
                    spec=entry.get("spec"),
                    notes=" ".join(str(entry.get("notes") or "").split()),
                    acceptance=tuple(str(a) for a in (entry.get("acceptance") or [])),
                )
            )
    return items


def load_label_config(path: Path | None = None) -> dict:
    return yaml.safe_load((path or BACKLOG_DIR / "labels.yaml").read_text(encoding="utf-8"))


def expand_dependencies(items: list[BacklogItem]) -> dict[str, list[str]]:
    """Explicit dependencies plus ``depends_on_phase`` (= every other item of that phase)."""
    by_phase: dict[int, list[str]] = {}
    for item in items:
        by_phase.setdefault(item.phase, []).append(item.id)
    deps: dict[str, list[str]] = {}
    for item in items:
        expanded = list(item.depends)
        if item.depends_on_phase is not None:
            expanded += [i for i in by_phase.get(int(item.depends_on_phase), []) if i != item.id]
        deps[item.id] = list(dict.fromkeys(expanded))  # dedupe, keep order
    return deps


def validate_backlog(items: list[BacklogItem], label_config: dict) -> list[str]:
    """Return problems: duplicate ids, unknown roles/labels, missing dependencies, cycles."""
    problems: list[str] = []
    known_labels = {entry["name"] for entry in label_config.get("labels", [])}
    seen: set[str] = set()
    for item in items:
        if item.id in seen:
            problems.append(f"duplicate backlog id {item.id}")
        seen.add(item.id)
        if not ID_PATTERN.match(item.id):
            problems.append(f"{item.id}: id must look like P<phase>-<AREA>-<NNN>")
        if not item.id.startswith(f"P{item.phase}-"):
            problems.append(f"{item.id}: id prefix does not match phase {item.phase}")
        if item.role not in ROLES:
            problems.append(f"{item.id}: unknown role {item.role!r}")
        for label in item.labels():
            if label not in known_labels:
                problems.append(f"{item.id}: label {label!r} is not defined in labels.yaml")
        if not item.acceptance:
            problems.append(f"{item.id}: needs at least one acceptance criterion")
    deps = expand_dependencies(items)
    for item_id, item_deps in deps.items():
        for dep in item_deps:
            if dep == item_id:
                problems.append(f"{item_id}: depends on itself")
            elif dep not in seen:
                problems.append(f"{item_id}: unknown dependency {dep}")
    try:
        topological_order(items, deps)
    except ValueError as exc:
        problems.append(str(exc))
    return problems


def topological_order(items: list[BacklogItem], deps: dict[str, list[str]]) -> list[str]:
    """Item ids ordered so that every dependency comes first (stable w.r.t. file order)."""
    order: list[str] = []
    state: dict[str, int] = {}  # 1 = visiting, 2 = done
    known = {item.id for item in items}

    def visit(node: str, path: list[str]) -> None:
        if state.get(node) == 2:
            return
        if state.get(node) == 1:
            cycle = " -> ".join(path[path.index(node) :] + [node])
            raise ValueError(f"dependency cycle: {cycle}")
        state[node] = 1
        for dep in deps.get(node, []):
            if dep in known:
                visit(dep, path + [node])
        state[node] = 2
        order.append(node)

    for item in items:
        visit(item.id, [])
    return order


# ── issue bodies ───────────────────────────────────────────────────────────────────────────
_META_LINE = re.compile(r"^\s*(Backlog-ID|Depends on|Spec)\s*:\s*(.*?)\s*$", re.MULTILINE)


def parse_issue_meta(body: str | None) -> dict:
    """Parse the ``Backlog-ID:``, ``Depends on:`` and ``Spec:`` lines of an issue body."""
    meta: dict = {"backlog_id": None, "depends_on": [], "spec": None}
    for key, value in _META_LINE.findall(body or ""):
        value = value.strip()
        if key == "Backlog-ID":
            meta["backlog_id"] = value or None
        elif key == "Depends on":
            meta["depends_on"] = [int(n) for n in re.findall(r"#(\d+)", value)]
        elif key == "Spec":
            meta["spec"] = value if value and value.lower() != "none" else None
    return meta


def render_issue_body(item: BacklogItem, dep_numbers: list[int], source_file: str) -> str:
    depends = ", ".join(f"#{n}" for n in dep_numbers) if dep_numbers else "none"
    lines = [
        f"Backlog-ID: {item.id}",
        f"Depends on: {depends}",
        f"Spec: {item.spec or 'none'}",
        "",
        "## Goal",
        item.title,
    ]
    if item.notes:
        lines += ["", item.notes]
    lines += ["", "## Acceptance criteria"]
    lines += [f"- [ ] {criterion}" for criterion in item.acceptance]
    lines += [
        "",
        "---",
        f"Created from `{source_file}` by `scripts/bootstrap_github.py`. "
        f"Agent procedure: `/role-{item.role} <this issue number>` (docs/agent-workflow.md).",
    ]
    return "\n".join(lines) + "\n"


# ── work selection (pure) ──────────────────────────────────────────────────────────────────
def label_names(entity: dict) -> set[str]:
    return {
        label["name"] if isinstance(label, dict) else str(label)
        for label in entity.get("labels") or []
    }


def role_of_branch(head_ref: str) -> str | None:
    prefix = head_ref.split("/", 1)[0]
    return prefix if prefix in ROLES and "/" in head_ref else None


def issue_phase(issue: dict) -> int:
    for name in label_names(issue):
        if name.startswith("phase:") and name[6:].isdigit():
            return int(name[6:])
    return 99


@dataclass(frozen=True)
class WorkItem:
    role: str
    item: str  # "14" or "pr:21"
    reason: str

    @property
    def session_suffix(self) -> str:
        return self.item.replace("pr:", "pr")


def select_next(
    role: str,
    issues: list[dict],
    prs: list[dict],
    *,
    max_phase: int = 99,
    exclude: set[str] | frozenset[str] = frozenset(),
) -> WorkItem | None:
    """Next work item for ``role``: own PRs with review:changes, then (verifier) PRs waiting for
    review, then ready issues whose dependencies are closed (priority:high, lower phase first)."""
    open_prs = sorted(
        (p for p in prs if not p.get("isDraft") and "status:needs-human" not in label_names(p)),
        key=lambda p: p["number"],
    )
    for pr in open_prs:
        if role_of_branch(pr.get("headRefName", "")) == role and "review:changes" in label_names(
            pr
        ):
            item = f"pr:{pr['number']}"
            if item not in exclude:
                return WorkItem(role, item, "review:changes on own PR")
    if role == "verify":
        for pr in open_prs:
            author = role_of_branch(pr.get("headRefName", ""))
            if author not in (None, "verify") and "review:verify" in label_names(pr):
                item = f"pr:{pr['number']}"
                if item not in exclude:
                    return WorkItem(role, item, f"review:verify on {author} PR")
    state_of = {i["number"]: str(i.get("state", "")).upper() for i in issues}
    candidates = []
    for issue in issues:
        labels = label_names(issue)
        if str(issue.get("state", "")).upper() != "OPEN":
            continue
        if f"role:{role}" not in labels or "status:ready" not in labels:
            continue
        if labels & set(NOT_READY):
            continue
        if issue_phase(issue) > max_phase:
            continue
        deps = parse_issue_meta(issue.get("body")).get("depends_on", [])
        if any(state_of.get(dep) != "CLOSED" for dep in deps):
            continue
        if str(issue["number"]) in exclude:
            continue
        candidates.append(issue)
    if not candidates:
        return None
    candidates.sort(
        key=lambda i: ("priority:high" not in label_names(i), issue_phase(i), i["number"])
    )
    best = candidates[0]
    return WorkItem(role, str(best["number"]), f"ready issue: {best.get('title', '')}")


# ── GitHub (REST through the gh CLI) ───────────────────────────────────────────────────────
# Only REST endpoints are used (`gh api`), never GraphQL, so the tooling also works where the
# GraphQL API is unavailable. Authentication comes from `gh auth login`.
class GhError(RuntimeError):
    pass


def gh(*args: str, parse_json: bool = False, input_text: str | None = None, cwd: Path = REPO_ROOT):
    """Run ``gh`` and return stdout (parsed as JSON when ``parse_json``)."""
    if shutil.which("gh") is None:
        raise GhError("GitHub CLI `gh` not found; install it and run `gh auth login`")
    result = subprocess.run(
        ["gh", *args], cwd=cwd, capture_output=True, text=True, input=input_text, check=False
    )
    if result.returncode != 0:
        raise GhError(
            f"gh {' '.join(args)} failed: {result.stderr.strip() or result.stdout.strip()}"
        )
    return json.loads(result.stdout or "null") if parse_json else result.stdout


def parse_json_stream(text: str) -> list:
    """Parse concatenated JSON documents (``gh api --paginate`` prints one array per page)."""
    decoder, pos, out = json.JSONDecoder(), 0, []
    while pos < len(text):
        while pos < len(text) and text[pos].isspace():
            pos += 1
        if pos >= len(text):
            break
        value, pos = decoder.raw_decode(text, pos)
        out.extend(value if isinstance(value, list) else [value])
    return out


_REMOTE = re.compile(r"github\.com[:/](?P<slug>[^/\s]+/[^/\s]+?)(?:\.git)?/?$")


def repo_slug(explicit: str | None = None) -> str:
    """OWNER/NAME from ``explicit``, ``$GH_REPO`` or the ``origin`` remote of this checkout."""
    if explicit:
        return explicit
    if os.environ.get("GH_REPO"):
        return os.environ["GH_REPO"]
    url = subprocess.run(
        ["git", "remote", "get-url", "origin"], cwd=REPO_ROOT, capture_output=True, text=True
    ).stdout.strip()
    match = _REMOTE.search(url)
    if not match:
        raise GhError(
            f"cannot derive OWNER/NAME from origin remote {url!r}; pass --repo or set GH_REPO"
        )
    return match.group("slug")


def gh_api(path: str, method: str = "GET", payload: dict | None = None, paginate: bool = False):
    """Call a REST endpoint; JSON payload goes through stdin."""
    args = ["api", path, "-X", method, "-H", "Accept: application/vnd.github+json"]
    if paginate:
        args.append("--paginate")
    if payload is not None:
        args += ["--input", "-"]
    out = gh(*args, input_text=json.dumps(payload) if payload is not None else None)
    if paginate:
        return parse_json_stream(out)
    return json.loads(out) if out.strip() else None


def _labels(raw: list) -> list[dict]:
    return [{"name": label["name"]} for label in raw or []]


def normalize_issue(raw: dict) -> dict:
    return {
        "number": raw["number"],
        "title": raw.get("title", ""),
        "state": str(raw.get("state", "")).upper(),
        "labels": _labels(raw.get("labels")),
        "body": raw.get("body") or "",
    }


def normalize_pr(raw: dict) -> dict:
    return {
        "number": raw["number"],
        "title": raw.get("title", ""),
        "headRefName": (raw.get("head") or {}).get("ref", ""),
        "headSha": (raw.get("head") or {}).get("sha", ""),
        "labels": _labels(raw.get("labels")),
        "isDraft": bool(raw.get("draft")),
        "body": raw.get("body") or "",
    }


def fetch_issues(slug: str) -> list[dict]:
    """All issues (open and closed), without pull requests."""
    raw = gh_api(f"repos/{slug}/issues?state=all&per_page=100", paginate=True)
    return [normalize_issue(i) for i in raw if "pull_request" not in i]


def fetch_prs(slug: str) -> list[dict]:
    raw = gh_api(f"repos/{slug}/pulls?state=open&per_page=100", paginate=True)
    return [normalize_pr(p) for p in raw]


def comment(slug: str, number: int, body: str) -> None:
    """Comment on an issue or pull request."""
    gh_api(f"repos/{slug}/issues/{number}/comments", "POST", {"body": body})


def add_labels(slug: str, number: int, labels: list[str]) -> None:
    gh_api(f"repos/{slug}/issues/{number}/labels", "POST", {"labels": labels})


def remove_label(slug: str, number: int, label: str) -> None:
    try:
        gh_api(
            f"repos/{slug}/issues/{number}/labels/{urllib.parse.quote(label, safe='')}", "DELETE"
        )
    except GhError as exc:
        if "404" not in str(exc) and "Label does not exist" not in str(exc):
            raise


@dataclass
class Snapshot:
    """GitHub state used for one round of decisions."""

    slug: str = ""
    issues: list[dict] = field(default_factory=list)
    prs: list[dict] = field(default_factory=list)

    @classmethod
    def fetch(cls, slug: str | None = None) -> Snapshot:
        slug = repo_slug(slug)
        return cls(slug=slug, issues=fetch_issues(slug), prs=fetch_prs(slug))
