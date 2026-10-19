"""Agent tooling: backlog consistency, issue metadata, and the orchestrator's work selection."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import agentlib  # noqa: E402
from agentlib import (  # noqa: E402
    BacklogItem,
    expand_dependencies,
    load_backlog,
    load_label_config,
    parse_issue_meta,
    render_issue_body,
    role_of_branch,
    select_next,
    topological_order,
    validate_backlog,
)


def test_backlog_files_are_consistent():
    items = load_backlog()
    assert validate_backlog(items, load_label_config()) == []
    assert {item.phase for item in items} == {1, 2}
    assert {item.role for item in items} == set(agentlib.ROLES)


def test_every_role_has_dependency_free_work_on_day_one():
    items = load_backlog()
    deps = expand_dependencies(items)
    free = {item.role for item in items if item.phase == 1 and not deps[item.id]}
    assert free == set(agentlib.ROLES)


def test_gates_depend_on_their_whole_phase():
    items = load_backlog()
    deps = expand_dependencies(items)
    for phase in (1, 2):
        others = {i.id for i in items if i.phase == phase and i.id != f"P{phase}-GATE"}
        assert others <= set(deps[f"P{phase}-GATE"])


def test_topological_order_puts_dependencies_first():
    items = load_backlog()
    deps = expand_dependencies(items)
    position = {item_id: n for n, item_id in enumerate(topological_order(items, deps))}
    for item_id, item_deps in deps.items():
        assert all(position[d] < position[item_id] for d in item_deps)


def _item(item_id: str, depends: tuple[str, ...] = ()) -> BacklogItem:
    return BacklogItem(
        id=item_id, title=item_id, role="research", area="physics", type="spec", phase=1,
        milestone="Phase 1", depends=depends, acceptance=("done",),
    )  # fmt: skip


def test_cycles_and_unknown_dependencies_are_reported():
    items = [
        _item("P1-A-001", ("P1-B-001",)),
        _item("P1-B-001", ("P1-A-001",)),
        _item("P1-C-001", ("P1-X-999",)),
    ]
    problems = validate_backlog(items, load_label_config())
    assert any("cycle" in p for p in problems)
    assert any("unknown dependency P1-X-999" in p for p in problems)


def test_issue_body_round_trip():
    item = _item("P1-SPEC-777")
    body = render_issue_body(item, [12, 15], ".github/backlog/phase1.yaml")
    meta = parse_issue_meta(body)
    assert meta == {"backlog_id": "P1-SPEC-777", "depends_on": [12, 15], "spec": None}
    assert parse_issue_meta("Depends on: none\nSpec: MOD-MOB-001")["depends_on"] == []
    assert parse_issue_meta(None)["backlog_id"] is None


def test_role_of_branch():
    assert role_of_branch("implement/14-masetti") == "implement"
    assert role_of_branch("worktree-implement-14") is None
    assert role_of_branch("main") is None


def _issue(number, role, *extra, deps=(), state="OPEN", phase=1):
    labels = [{"name": f"role:{role}"}, {"name": "status:ready"}, {"name": f"phase:{phase}"}]
    labels += [{"name": label} for label in extra]
    body = "Depends on: " + (", ".join(f"#{d}" for d in deps) or "none")
    return {
        "number": number,
        "title": f"issue {number}",
        "state": state,
        "labels": labels,
        "body": body,
    }


def _pr(number, head, *labels):
    return {
        "number": number,
        "headRefName": head,
        "labels": [{"name": n} for n in labels],
        "isDraft": False,
    }


def test_selection_order_changes_then_reviews_then_issues():
    issues = [_issue(1, "verify"), _issue(2, "implement")]
    prs = [_pr(10, "implement/2-x", "review:verify"), _pr(11, "verify/1-y", "review:changes")]
    assert select_next("verify", issues, prs).item == "pr:11"  # own PR with changes requested
    prs = prs[:1]
    assert select_next("verify", issues, prs).item == "pr:10"  # then reviews
    assert select_next("verify", issues, []).item == "1"  # then issues
    assert select_next("implement", issues, prs).item == "2"  # only the verifier reviews


def test_selection_respects_dependencies_priority_phase_and_exclusions():
    issues = [
        _issue(1, "research", deps=(9,)),  # blocked: #9 open
        _issue(2, "research", phase=2),
        _issue(3, "research", "priority:high", phase=2),
        _issue(4, "research"),
        _issue(5, "research", "status:needs-human"),
        _issue(9, "design"),
        _issue(8, "research", state="CLOSED"),
    ]
    assert select_next("research", issues, []).item == "3"  # priority beats phase
    assert select_next("research", issues, [], max_phase=1).item == "4"
    assert select_next("research", issues, [], exclude={"3", "4"}).item == "2"
    issues[5]["state"] = "CLOSED"
    assert select_next("research", issues, [], max_phase=1).item == "1"  # dependency closed now
    assert select_next("research", issues, [], exclude={"1", "2", "3", "4"}) is None


@pytest.mark.parametrize("label", ["status:in-progress", "status:review", "status:blocked"])
def test_claimed_or_blocked_issues_are_skipped(label):
    assert select_next("design", [_issue(7, "design", label)], []) is None


def test_prs_flagged_for_the_human_are_not_dispatched():
    prs = [_pr(12, "research/3-z", "review:verify", "status:needs-human")]
    assert select_next("verify", [], prs) is None


def test_required_checks_match_the_ci_workflow():
    import bootstrap_github

    workflow = __import__("yaml").safe_load(
        (Path(__file__).resolve().parents[2] / ".github/workflows/ci.yml").read_text()
    )
    names = set()
    for job_id, job in workflow["jobs"].items():
        if "matrix" in job.get("strategy", {}):
            for solver in job["strategy"]["matrix"]["solver"]:
                names.add(job["name"].replace("${{ matrix.solver }}", solver))
        else:
            names.add(job.get("name", job_id))
    assert set(bootstrap_github.REQUIRED_CHECKS) <= names
