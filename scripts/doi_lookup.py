"""Turn a DOI into a verified bibliography entry for src/opentcad/data/references.yaml.

    uv run python scripts/doi_lookup.py 10.1109/T-ED.1983.21207                 # print the entry
    uv run python scripts/doi_lookup.py <doi> --by researcher --append          # add it to references.yaml
    uv run python scripts/doi_lookup.py <doi> --id masetti-1983 --append        # choose the id

Metadata comes from Crossref (https://api.crossref.org), never from memory. The entry records
``metadata_check: {method: crossref, date, by}``. Set CROSSREF_MAILTO to join Crossref's polite pool.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import yaml

from opentcad.literature import DOI_PATTERN, parse_references, validate_reference

REPO_ROOT = Path(__file__).resolve().parents[1]
REFERENCES = REPO_ROOT / "src" / "opentcad" / "data" / "references.yaml"
USER_AGENT = "opentcad-doi-lookup/0.1 (+https://github.com/mseokq23/open_tcad)"
KIND_MAP = {
    "journal-article": "article",
    "proceedings-article": "article",
    "posted-content": "article",
    "book": "book",
    "monograph": "book",
    "edited-book": "book",
    "reference-book": "book",
    "book-chapter": "chapter",
    "book-section": "chapter",
    "dissertation": "thesis",
    "standard": "standard",
    "dataset": "dataset",
}


def fetch(doi: str) -> dict:
    url = "https://api.crossref.org/works/" + urllib.parse.quote(doi)
    if os.environ.get("CROSSREF_MAILTO"):
        url += "?mailto=" + urllib.parse.quote(os.environ["CROSSREF_MAILTO"])
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)["message"]


def ascii_slug(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def author_name(author: dict) -> str:
    given = author.get("given", "")
    initials = " ".join(f"{part[0]}." for part in re.split(r"[\s.\-]+", given) if part)
    family = author.get("family") or author.get("name", "")
    return f"{initials} {family}".strip()


def year_of(message: dict) -> int | None:
    for key in ("issued", "published-print", "published-online"):
        parts = (message.get(key) or {}).get("date-parts") or []
        if parts and parts[0] and parts[0][0]:
            return int(parts[0][0])
    return None


def suggest_id(message: dict) -> str:
    families = [
        ascii_slug(a.get("family") or a.get("name", "")) for a in message.get("author") or []
    ]
    year = year_of(message) or "nd"
    if len(families) == 2:
        return f"{families[0]}-{families[1]}-{year}"
    return f"{families[0] if families else 'anon'}-{year}"


def entry_from_crossref(message: dict, by: str, today: str) -> dict:
    kind = KIND_MAP.get(message.get("type", ""), "article")
    entry: dict = {
        "kind": kind,
        "title": " ".join(message.get("title") or []).strip(),
        "authors": [author_name(a) for a in message.get("author") or []]
        or ["(no author in Crossref)"],
        "year": year_of(message),
    }
    container = " ".join(message.get("container-title") or []).strip()
    if container and kind != "book":
        entry["venue"] = container
    for key in ("volume", "issue"):
        if message.get(key):
            value = str(message[key])
            entry[key] = int(value) if value.isdigit() else value
    if message.get("page"):
        entry["pages"] = str(message["page"])
    if kind in ("book", "chapter") and message.get("publisher"):
        entry["publisher"] = message["publisher"]
    isbns = [re.sub(r"[^0-9X]", "", i) for i in message.get("ISBN") or []]
    isbn13 = [i for i in isbns if len(i) == 13]
    if isbn13:
        entry["isbn"] = isbn13[0]
    entry["doi"] = message.get("DOI")  # as registered; DOIs are case-insensitive
    entry["metadata_check"] = {"method": "crossref", "date": today, "by": by}
    return {k: v for k, v in entry.items() if v is not None}


def render(ref_id: str, entry: dict) -> str:
    lines = [f"  {ref_id}:"]
    for key, value in entry.items():
        if key == "metadata_check":
            lines.append(
                f"    metadata_check: {{method: {value['method']}, date: {json.dumps(value['date'])}, by: {value['by']}}}"
            )
        elif isinstance(value, list):
            lines.append(
                f"    {key}: [{', '.join(json.dumps(v, ensure_ascii=False) for v in value)}]"
            )
        elif isinstance(value, int) or (key == "kind" and re.fullmatch(r"[a-z]+", str(value))):
            lines.append(f"    {key}: {value}")
        else:
            lines.append(f"    {key}: {json.dumps(value, ensure_ascii=False)}")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "doi", help="DOI, e.g. 10.1109/T-ED.1983.21207 (a https://doi.org/ URL also works)"
    )
    parser.add_argument(
        "--id", help="reference id to use (default: suggested from authors and year)"
    )
    parser.add_argument("--by", default="researcher", help="who ran the lookup (role name)")
    parser.add_argument("--append", action="store_true", help="append the entry to references.yaml")
    args = parser.parse_args(argv)

    doi = re.sub(r"^(https?://(dx\.)?doi\.org/|doi:)", "", args.doi.strip(), flags=re.IGNORECASE)
    if not DOI_PATTERN.match(doi):
        print(f"not a DOI: {doi!r}", file=sys.stderr)
        return 2
    try:
        message = fetch(doi)
    except urllib.error.HTTPError as exc:
        print(
            f"Crossref has no record for {doi} (HTTP {exc.code}). Check the DOI at https://doi.org/{doi}",
            file=sys.stderr,
        )
        return 1
    except (urllib.error.URLError, TimeoutError) as exc:
        print(f"could not reach Crossref: {exc}", file=sys.stderr)
        return 1

    today = dt.date.today().isoformat()
    ref_id = args.id or suggest_id(message)
    entry = entry_from_crossref(message, args.by, today)
    block = render(ref_id, entry)
    print(block, end="")

    if not args.append:
        return 0
    text = REFERENCES.read_text(encoding="utf-8")
    current = yaml.safe_load(text).get("references") or {}
    if ref_id in current:
        print(f"id {ref_id!r} already exists in references.yaml; pass --id", file=sys.stderr)
        return 1
    if any(str(e.get("doi", "")).lower() == doi.lower() for e in current.values()):
        print(f"DOI {doi} is already in references.yaml", file=sys.stderr)
        return 1
    new_text = text.rstrip("\n") + "\n\n" + block
    parsed = parse_references(yaml.safe_load(new_text))
    problems = validate_reference(parsed[ref_id])
    if problems:
        print("entry would be invalid, not written:\n  " + "\n  ".join(problems), file=sys.stderr)
        return 1
    REFERENCES.write_text(new_text, encoding="utf-8")
    print(f"appended {ref_id} to {REFERENCES.relative_to(REPO_ROOT)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
