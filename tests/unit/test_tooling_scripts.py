"""Provenance checker, blind-reader hook, DOI entries and orchestrator helpers (no network)."""

from __future__ import annotations

import json
import subprocess
import sys
from argparse import Namespace
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import check_citations  # noqa: E402
import doi_lookup  # noqa: E402
import orchestrate  # noqa: E402
from agentlib import WorkItem  # noqa: E402

from opentcad.literature import parse_references, validate_reference  # noqa: E402

GUARD = REPO_ROOT / "scripts" / "hooks" / "blind_read_guard.py"


# ── check_citations ────────────────────────────────────────────────────────────────────────
def test_repository_passes_the_standard_check(capsys):
    assert check_citations.main(["--quiet"]) == 0


def test_strict_check_reports_phase_zero_debt(capsys):
    assert check_citations.main(["--quiet", "--strict"]) == 1
    out = capsys.readouterr().out
    assert "bootstrap spec" in out
    assert "must be checked" in out


def test_tables_and_front_matter_parsing():
    text = "---\nid: MOD-ZZ-001\nstatus: draft\n---\n\n| # | Equation | Source | Locator |\n|---|---|---|---|\n"
    text += "| (1) | $\\|E\\| = 1$ | ref-a, ref-b | Eq. (2), p. 3 |\n"
    front, body = check_citations.split_front_matter(text)
    assert front == {"id": "MOD-ZZ-001", "status": "draft"}
    (table,) = check_citations.markdown_tables(body)
    assert table[0] == ["#", "Equation", "Source", "Locator"]
    assert check_citations.source_ids(table[1][2]) == ["ref-a", "ref-b"]
    assert len(table[1]) == 4  # escaped pipe stays inside the cell


def test_tbd_is_an_error_once_a_spec_leaves_draft(tmp_path):
    spec_dir = tmp_path / "models"
    spec_dir.mkdir()
    spec = spec_dir / "MOD-ZZ-001.md"
    spec.write_text(
        "---\nid: MOD-ZZ-001\nkind: model\nstatus: reviewed\nsources: [sze-ng-2007]\n---\n"
        "| # | Equation | Source | Locator |\n|---|---|---|---|\n| (1) | $x$ | sze-ng-2007 | TBD |\n",
        encoding="utf-8",
    )
    report = check_citations.Report()
    refs = check_citations.load_references()
    check_citations.check_spec(spec, refs, report, strict=False, spec_ids={"MOD-ZZ-001"})
    assert any("TBD is only allowed while the spec is draft" in e for e in report.errors)


# ── blind-reader hook ──────────────────────────────────────────────────────────────────────
def run_guard(tool_name: str, tool_input: dict) -> int:
    event = {"tool_name": tool_name, "tool_input": tool_input, "cwd": str(REPO_ROOT)}
    env = {"PATH": "/usr/bin:/bin", "CLAUDE_PROJECT_DIR": str(REPO_ROOT)}
    result = subprocess.run(
        [sys.executable, str(GUARD)],
        input=json.dumps(event),
        text=True,
        capture_output=True,
        env=env,
    )
    return result.returncode


def test_guard_allows_only_source_documents():
    assert (
        run_guard("Read", {"file_path": str(REPO_ROOT / "literature/pdfs/masetti-1983.pdf")}) == 0
    )
    assert run_guard("Read", {"file_path": "literature/pdfs/masetti-1983.pdf"}) == 0
    assert run_guard("Glob", {"pattern": "literature/pdfs/*.pdf"}) == 0
    assert run_guard("WebFetch", {"url": "https://doi.org/10.1000/x"}) == 0


def test_guard_blocks_data_specs_and_escapes():
    assert (
        run_guard(
            "Read", {"file_path": str(REPO_ROOT / "src/opentcad/data/materials/silicon.yaml")}
        )
        == 2
    )
    assert run_guard("Read", {"file_path": "literature/pdfs/../../specs/models/MOD-DD-001.md"}) == 2
    assert run_guard("Read", {"file_path": "literature/notes/masetti-1983.md"}) == 2
    assert run_guard("Glob", {"pattern": "**/*.yaml"}) == 2
    assert run_guard("Grep", {"pattern": "1.12"}) == 2


# ── doi_lookup ─────────────────────────────────────────────────────────────────────────────
SYNTHETIC_CROSSREF = {  # shape of a Crossref "work" message; values are made up for the test
    "type": "journal-article",
    "title": ["A synthetic test record"],
    "author": [{"given": "Ada B.", "family": "Lovelace"}, {"given": "Ch.", "family": "Babbage"}],
    "issued": {"date-parts": [[1999, 1]]},
    "container-title": ["Journal of Tests"],
    "volume": "12",
    "issue": "3",
    "page": "45-67",
    "DOI": "10.9999/TEST.1999.1",
}


def test_doi_entry_renders_valid_yaml():
    entry = doi_lookup.entry_from_crossref(SYNTHETIC_CROSSREF, "researcher", "2026-10-19")
    assert entry["authors"] == ["A. B. Lovelace", "C. Babbage"]
    assert doi_lookup.suggest_id(SYNTHETIC_CROSSREF) == "lovelace-babbage-1999"
    block = doi_lookup.render("lovelace-babbage-1999", entry)
    refs = parse_references(yaml.safe_load("references:\n" + block))
    ref = refs["lovelace-babbage-1999"]
    assert validate_reference(ref) == []
    assert (ref.year, ref.doi, ref.extra["volume"], ref.extra["pages"]) == (
        1999,
        "10.9999/TEST.1999.1",
        12,
        "45-67",
    )


# ── orchestrator helpers ───────────────────────────────────────────────────────────────────
def test_session_names_are_unique_per_dispatch():
    state = {"dispatches": [{"name": "otcad-verify-pr21-1"}], "failures": {}}
    work = WorkItem("verify", "pr:21", "review")
    assert orchestrate.session_name(state, "otcad", work) == "otcad-verify-pr21-2"
    args = Namespace(permission_mode=None, model=None)
    assert orchestrate.dispatch_command(work, "otcad-verify-pr21-2", args) == [
        "claude", "--bg", "--name", "otcad-verify-pr21-2", "/role-verify pr:21",
    ]  # fmt: skip


def test_failed_items_stop_being_dispatched():
    state = {
        "dispatches": [{"name": "a", "item": "7", "role": "research"}],
        "failures": {"9": 2, "10": 1},
    }
    assert orchestrate.excluded_items(state, max_retries=2) == {"7", "9"}


def test_post_check_flags_sessions_that_ended_without_hand_off(capsys):
    from agentlib import Snapshot

    issue = {
        "number": 7,
        "title": "x",
        "state": "OPEN",
        "labels": [{"name": "status:in-progress"}],
        "body": "",
    }
    snap = Snapshot(slug="o/r", issues=[issue], prs=[])
    dispatch = {
        "name": "otcad-research-7-1",
        "role": "research",
        "item": "7",
        "final_state": "done",
    }
    orchestrate.post_check(dispatch, snap, dry_run=True)
    assert "needs-human #7" in capsys.readouterr().out
    snap.prs = [{"number": 9, "headRefName": "research/70-x", "labels": [], "body": "Closes #70"}]
    orchestrate.post_check(dispatch, snap, dry_run=True)
    assert "needs-human #7" in capsys.readouterr().out  # #70 is not #7
    snap.prs = [{"number": 9, "headRefName": "research/7-spec", "labels": [], "body": "Closes #7"}]
    orchestrate.post_check(dispatch, snap, dry_run=True)
    assert capsys.readouterr().out == ""  # a PR exists: hand-off happened
