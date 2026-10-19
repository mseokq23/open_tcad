"""Provenance checks for data files, specs and registered models (docs/literature-policy.md).

    uv run python scripts/check_citations.py            # CI: structure, sources, locators, statuses
    uv run python scripts/check_citations.py --strict   # phase gates: everything checked/verified
    uv run python scripts/check_citations.py --online   # also compare every DOI with Crossref

Exit code 1 when any error is found. Warnings never fail the run.
"""

from __future__ import annotations

import argparse
import difflib
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from opentcad.literature import load_references, validate_reference
from opentcad.materials import MaterialDB
from opentcad.physics import available
from opentcad.units import constant_records

REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC_DIRS = {"models": "model", "verification": "verification", "materials": "material"}
SPEC_STATUSES = ("draft", "reviewed", "implemented", "verified")
SPEC_ID = re.compile(r"^(MOD|VER|MAT)-[A-Z0-9]+-\d{3}$")
CELL_SPLIT = re.compile(r"(?<!\\)\|")
TBD = re.compile(r"\bTBD\b")
USER_AGENT = "opentcad-check-citations/0.1 (+https://github.com/mseokq23/open_tcad)"


@dataclass
class Report:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def error(self, where: str, message: str) -> None:
        self.errors.append(f"ERROR {where}: {message}")

    def warn(self, where: str, message: str) -> None:
        self.warnings.append(f"WARN  {where}: {message}")


# ── specs ──────────────────────────────────────────────────────────────────────────────────
def split_front_matter(text: str) -> tuple[dict | None, str]:
    if not text.startswith("---"):
        return None, text
    parts = text.split("\n---", 1)
    if len(parts) != 2:
        return None, text
    front = yaml.safe_load(parts[0].lstrip("-\n")) or {}
    return front, parts[1].split("\n", 1)[1] if "\n" in parts[1] else ""


def markdown_tables(body: str) -> list[list[list[str]]]:
    """Return tables as lists of rows (header first, separator dropped)."""
    tables, current = [], []
    for line in body.splitlines():
        if line.lstrip().startswith("|"):
            cells = [c.strip() for c in CELL_SPLIT.split(line.strip().strip("|"))]
            current.append(cells)
        elif current:
            tables.append(current)
            current = []
    if current:
        tables.append(current)
    cleaned = []
    for table in tables:
        rows = [r for r in table if not all(re.fullmatch(r":?-{2,}:?", c or "---") for c in r)]
        if rows:
            cleaned.append(rows)
    return cleaned


def source_ids(cell: str) -> list[str]:
    return [token for token in re.split(r"[,;\s]+", cell.replace("`", "")) if token]


def check_spec(
    path: Path, refs: dict, report: Report, strict: bool, spec_ids: set[str]
) -> dict | None:
    where = str(path.relative_to(REPO_ROOT)) if path.is_relative_to(REPO_ROOT) else str(path)
    front, body = split_front_matter(path.read_text(encoding="utf-8"))
    if front is None:
        report.error(where, "missing YAML front matter (see specs/TEMPLATE.md)")
        return None
    spec_id, status = front.get("id"), front.get("status")
    if spec_id != path.stem:
        report.error(where, f"front matter id {spec_id!r} must equal the file name {path.stem!r}")
    if spec_id and not SPEC_ID.match(str(spec_id)):
        report.error(where, f"id {spec_id!r} must look like MOD-<AREA>-<NNN>")
    expected_kind = SPEC_DIRS.get(path.parent.name)
    if front.get("kind") != expected_kind:
        report.error(where, f"kind must be {expected_kind!r} in specs/{path.parent.name}/")
    if status not in SPEC_STATUSES:
        report.error(where, f"status must be one of {SPEC_STATUSES}, got {status!r}")
    for src in front.get("sources") or []:
        if src not in refs:
            report.error(where, f"source {src!r} is not in references.yaml")
    for rel in front.get("implemented_in") or []:
        if not (REPO_ROOT / rel).exists():
            report.error(where, f"implemented_in path {rel} does not exist")
    for ver in front.get("verified_by") or []:
        if ver not in spec_ids:
            (report.error if status == "verified" else report.warn)(
                where, f"verified_by {ver} has no spec file yet"
            )
    for covered in front.get("covers") or []:
        if covered not in spec_ids:
            report.error(where, f"covers {covered}, which has no spec file")
    if status == "verified" and expected_kind == "model" and not front.get("verified_by"):
        report.error(where, "status verified requires verified_by")
    bootstrap = bool(front.get("bootstrap"))
    if bootstrap:
        (report.error if strict else report.warn)(
            where, "bootstrap spec: locators and independent review pending"
        )

    for table in markdown_tables(body):
        header = [h.lower() for h in table[0]]
        if "source" not in header or "locator" not in header:
            continue
        s_col, l_col = header.index("source"), header.index("locator")
        for row in table[1:]:
            if len(row) <= max(s_col, l_col):
                report.error(where, f"malformed table row: {' | '.join(row)}")
                continue
            label = row[0] or "row"
            sources, locator = source_ids(row[s_col]), row[l_col]
            if not sources:
                report.error(where, f"{label}: empty source")
            for src in sources:
                if src not in refs and not TBD.fullmatch(src):
                    report.error(where, f"{label}: source {src!r} is not in references.yaml")
            if not locator:
                report.error(where, f"{label}: empty locator")
            tbd_cells = [c for c in row if TBD.search(c)]
            if not tbd_cells:
                continue
            if status == "draft":
                report.warn(where, f"{label}: TBD in a draft ({len(tbd_cells)} cell(s))")
            elif bootstrap and not strict:
                report.warn(where, f"{label}: TBD in a bootstrap spec (P1-SPEC-001 fills it)")
            else:
                report.error(where, f"{label}: TBD is only allowed while the spec is draft")
    return front


def check_specs(refs: dict, report: Report, strict: bool) -> dict[str, dict]:
    files = [p for folder in SPEC_DIRS for p in sorted((REPO_ROOT / "specs" / folder).glob("*.md"))]
    spec_ids = {p.stem for p in files}
    fronts = {}
    for path in files:
        front = check_spec(path, refs, report, strict, spec_ids)
        if front is not None:
            fronts[path.stem] = front
    return fronts


# ── data and models ────────────────────────────────────────────────────────────────────────
def check_references(refs: dict, report: Report) -> None:
    for ref in refs.values():
        for problem in validate_reference(ref):
            report.error("references.yaml", problem)


def check_constants(refs: dict, report: Report, strict: bool) -> set[str]:
    cited = set()
    for name, record in constant_records().items():
        where = f"constants.yaml:{name}"
        src = record.get("source")
        cited.add(src)
        if src not in refs:
            report.error(where, f"source {src!r} is not in references.yaml")
        if not record.get("locator"):
            report.error(where, "missing locator")
        if record.get("status") not in ("extracted", "checked"):
            report.error(
                where, f"status must be extracted or checked, got {record.get('status')!r}"
            )
        if record.get("status") == "checked" and record.get("extracted_by") in (
            record.get("checked_by") or []
        ):
            report.error(where, "checker must differ from extractor (two-key rule)")
        if strict and record.get("status") != "checked":
            report.error(where, "strict: constants must be checked")
    return cited


def check_materials(report: Report, strict: bool) -> set[str]:
    db = MaterialDB.load()
    for problem in db.validate():
        report.error("materials", problem)
    cited = set()
    for material in db.materials():
        for p in db.parameters(material).values():
            where = f"materials:{material}.{p.name}"
            if p.source:
                cited.add(p.source)
            if p.status in ("needs-source", "conflict"):
                (report.error if strict else report.warn)(
                    where, f"status {p.status}: needs a human-approved source"
                )
            elif strict and p.status != "checked":
                report.error(where, f"strict: status {p.status}, must be checked")
    return cited


def check_models(fronts: dict[str, dict], refs: dict, report: Report, strict: bool) -> set[str]:
    cited: set[str] = set()
    by_spec: dict[str, set[str]] = {}
    for model in available():
        by_spec.setdefault(model.spec, set()).update(model.sources)
    for spec, sources in sorted(by_spec.items()):
        front = fronts.get(spec)
        missing = set((front or {}).get("sources") or []) - sources
        if front is not None and missing:
            report.warn(
                f"spec {spec}", f"cites {sorted(missing)}, which no registered model of it lists"
            )
    for model in available():
        where = f"model {model.id}"
        cited.update(model.sources)
        front = fronts.get(model.spec)
        if front is None:
            report.error(where, f"spec {model.spec} not found in specs/models/")
            continue
        for src in model.sources:
            if src not in refs:
                report.error(where, f"source {src!r} is not in references.yaml")
            elif src not in (front.get("sources") or []):
                report.error(where, f"source {src!r} is not listed in spec {model.spec}")
        status = front.get("status")
        if status == "draft":
            report.error(where, f"registered, but spec {model.spec} is still draft")
        if strict and status != "verified":
            report.error(where, f"strict: spec {model.spec} is {status}, must be verified")
    return cited


def check_cited_metadata(refs: dict, cited: set[str], report: Report, strict: bool) -> None:
    for ref_id in sorted(cited):
        ref = refs.get(ref_id)
        if ref is None:
            continue
        method = (ref.extra.get("metadata_check") or {}).get("method")
        if method in (None, "none"):
            (report.error if strict else report.warn)(
                f"references.yaml:{ref_id}",
                "bibliographic metadata never checked (metadata_check.method)",
            )


# ── Crossref ───────────────────────────────────────────────────────────────────────────────
def crossref(doi: str) -> dict:
    url = "https://api.crossref.org/works/" + urllib.parse.quote(doi)
    mailto = os.environ.get("CROSSREF_MAILTO")
    if mailto:
        url += "?mailto=" + urllib.parse.quote(mailto)
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)["message"]


def normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def years_of(message: dict) -> set[int]:
    years = set()
    for key in ("issued", "published-print", "published-online", "published"):
        parts = (message.get(key) or {}).get("date-parts") or []
        if parts and parts[0] and parts[0][0]:
            years.add(int(parts[0][0]))
    return years


def check_online(refs: dict, report: Report) -> None:
    for ref in refs.values():
        if not ref.doi:
            continue
        where = f"crossref:{ref.id}"
        try:
            message = crossref(ref.doi)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, KeyError) as exc:
            report.warn(where, f"could not query Crossref ({exc})")
            continue
        title = " ".join(message.get("title") or [])
        ratio = difflib.SequenceMatcher(None, normalize(title), normalize(ref.title)).ratio()
        if ratio < 0.9:
            report.error(where, f"title mismatch ({ratio:.2f}): Crossref has {title!r}")
        if ref.year is not None and years_of(message) and int(ref.year) not in years_of(message):
            report.error(
                where, f"year {ref.year} not in Crossref dates {sorted(years_of(message))}"
            )
        for key, field_name in (("volume", "volume"), ("issue", "issue")):
            mine = ref.extra.get(key)
            theirs = message.get(field_name)
            if mine is not None and theirs is not None and str(mine) != str(theirs):
                report.error(where, f"{key} {mine} differs from Crossref {theirs}")
        pages = ref.extra.get("pages")
        if (
            pages
            and message.get("page")
            and str(pages).split("-")[0] != str(message["page"]).split("-")[0]
        ):
            report.error(where, f"pages {pages} differ from Crossref {message['page']}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="phase-gate rules: all values checked, models verified",
    )
    parser.add_argument(
        "--online", action="store_true", help="compare DOIs with Crossref (network)"
    )
    parser.add_argument("--quiet", action="store_true", help="print errors only")
    args = parser.parse_args(argv)

    report = Report()
    refs = load_references()
    check_references(refs, report)
    fronts = check_specs(refs, report, args.strict)
    cited = set()
    cited |= check_constants(refs, report, args.strict)
    cited |= check_materials(report, args.strict)
    cited |= check_models(fronts, refs, report, args.strict)
    for front in fronts.values():
        cited.update(front.get("sources") or [])
    check_cited_metadata(refs, cited, report, args.strict)
    if args.online:
        check_online(refs, report)

    for line in report.errors:
        print(line)
    if not args.quiet:
        for line in report.warnings:
            print(line)
        counts = MaterialDB.load().status_counts()
        statuses = {f.get("status") for f in fronts.values()}
        print(
            f"checked {len(refs)} references, {len(fronts)} specs, {len(available())} models; "
            f"parameter status {counts}; spec statuses {sorted(s for s in statuses if s)}"
        )
    mode = "strict" if args.strict else "standard"
    print(f"{mode} check: {len(report.errors)} error(s), {len(report.warnings)} warning(s)")
    return 1 if report.errors else 0


if __name__ == "__main__":
    sys.exit(main())
