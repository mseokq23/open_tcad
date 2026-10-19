"""Bibliography access: every ``source`` id used in data files and specs resolves here."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import lru_cache
from importlib import resources
from pathlib import Path

import yaml

DOI_PATTERN = re.compile(r"^10\.\d{4,9}/\S+$")
ISBN13_PATTERN = re.compile(r"^97[89]\d{10}$")
KINDS = ("article", "book", "chapter", "thesis", "web", "dataset", "standard")


@dataclass(frozen=True)
class Reference:
    id: str
    kind: str
    title: str
    authors: tuple[str, ...]
    year: int | None = None
    venue: str | None = None
    doi: str | None = None
    isbn: str | None = None
    url: str | None = None
    accessed: str | None = None
    extra: dict = field(default_factory=dict, compare=False, hash=False)

    def short(self) -> str:
        """Compact human-readable citation, e.g. for GUI tooltips."""
        first = self.authors[0] if self.authors else "?"
        etal = " et al." if len(self.authors) > 1 else ""
        locator = (
            f"doi:{self.doi}"
            if self.doi
            else (self.url or (f"ISBN {self.isbn}" if self.isbn else ""))
        )
        year = self.year if self.year is not None else "n.d."
        return f"{first}{etal} ({year}). {self.title}. {locator}".strip()


def _default_path() -> Path:
    return Path(str(resources.files("opentcad").joinpath("data/references.yaml")))


def parse_references(raw: dict) -> dict[str, Reference]:
    refs: dict[str, Reference] = {}
    for ref_id, entry in (raw.get("references") or {}).items():
        known = {"kind", "title", "authors", "year", "venue", "doi", "isbn", "url", "accessed"}
        refs[ref_id] = Reference(
            id=ref_id,
            kind=entry.get("kind", ""),
            title=entry.get("title", ""),
            authors=tuple(entry.get("authors") or ()),
            year=entry.get("year"),
            venue=entry.get("venue"),
            doi=entry.get("doi"),
            isbn=str(entry["isbn"]) if entry.get("isbn") is not None else None,
            url=entry.get("url"),
            accessed=entry.get("accessed"),
            extra={k: v for k, v in entry.items() if k not in known},
        )
    return refs


@lru_cache(maxsize=4)
def load_references(path: str | None = None) -> dict[str, Reference]:
    """Load the bibliography (default: the packaged ``data/references.yaml``)."""
    file = Path(path) if path else _default_path()
    return parse_references(yaml.safe_load(file.read_text(encoding="utf-8")))


def validate_reference(ref: Reference) -> list[str]:
    """Return a list of problems with one bibliography entry (empty list = OK)."""
    problems: list[str] = []
    if ref.kind not in KINDS:
        problems.append(f"{ref.id}: kind must be one of {KINDS}, got {ref.kind!r}")
    if not ref.title:
        problems.append(f"{ref.id}: missing title")
    if not ref.authors:
        problems.append(f"{ref.id}: missing authors")
    if ref.doi and not DOI_PATTERN.match(ref.doi):
        problems.append(f"{ref.id}: malformed DOI {ref.doi!r}")
    if ref.isbn and not ISBN13_PATTERN.match(ref.isbn):
        problems.append(f"{ref.id}: ISBN must be 13 digits without dashes, got {ref.isbn!r}")
    if ref.kind in ("article", "chapter") and not ref.doi:
        problems.append(f"{ref.id}: articles and chapters need a DOI")
    if ref.kind == "book" and not (ref.isbn or ref.doi):
        problems.append(f"{ref.id}: books need an ISBN or DOI")
    if ref.kind in ("web", "dataset") and not ref.url:
        problems.append(f"{ref.id}: web sources and datasets need a URL")
    return problems
