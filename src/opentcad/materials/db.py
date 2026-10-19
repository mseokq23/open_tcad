"""Material parameter database.

Every parameter carries its provenance (``source`` id + ``locator``) and a status:

* ``needs-source`` no acceptable source yet; ``value`` is null and ``candidates`` lists options
* ``extracted``    one reader took the value from ``source`` at ``locator``
* ``checked``      a second, independent reader confirmed it (two-key rule)
* ``conflict``     sources disagree; a human decision is required

Usage policies:

* ``dev``    allows ``extracted`` and ``checked`` (day-to-day development)
* ``strict`` allows only ``checked`` (phase gates and release builds)

A caller can always pass an explicit ``override`` value. That value is then the
caller's input (e.g. a test input or a user-specified material), not a database claim.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path

import yaml

from opentcad.literature import Reference, load_references

STATUSES = ("needs-source", "extracted", "checked", "conflict")
POLICIES: dict[str, frozenset[str]] = {
    "dev": frozenset({"extracted", "checked"}),
    "strict": frozenset({"checked"}),
}


class ParameterError(RuntimeError):
    """A parameter is missing or not usable under the requested policy."""


@dataclass(frozen=True)
class Parameter:
    material: str
    name: str
    symbol: str
    value: float | None
    unit: str
    status: str
    source: str | None = None
    locator: str | None = None
    conditions: dict = field(default_factory=dict, compare=False, hash=False)
    extracted_by: str | None = None
    checked_by: tuple[str, ...] = ()
    candidates: tuple[dict, ...] = ()
    notes: str = ""


def _parse_parameter(material: str, name: str, entry: dict) -> Parameter:
    value = entry.get("value")
    return Parameter(
        material=material,
        name=name,
        symbol=str(entry.get("symbol", name)),
        value=float(value) if value is not None else None,
        unit=str(entry.get("unit", "")),
        status=str(entry.get("status", "")),
        source=entry.get("source"),
        locator=entry.get("locator"),
        conditions=dict(entry.get("conditions") or {}),
        extracted_by=entry.get("extracted_by"),
        checked_by=tuple(entry.get("checked_by") or ()),
        candidates=tuple(entry.get("candidates") or ()),
        notes=str(entry.get("notes") or ""),
    )


def validate_parameter(p: Parameter, references: dict[str, Reference]) -> list[str]:
    """Return problems with one parameter record (empty list = OK)."""
    where = f"{p.material}.{p.name}"
    problems: list[str] = []
    if p.status not in STATUSES:
        problems.append(f"{where}: status must be one of {STATUSES}, got {p.status!r}")
        return problems
    if not p.unit:
        problems.append(f"{where}: missing unit")
    if p.status in ("extracted", "checked"):
        if p.value is None:
            problems.append(f"{where}: status {p.status} requires a value")
        if not p.source:
            problems.append(f"{where}: missing source")
        elif p.source not in references:
            problems.append(f"{where}: source {p.source!r} is not in references.yaml")
        if not p.locator:
            problems.append(f"{where}: missing locator (table/equation/page where the value is)")
        if not p.extracted_by:
            problems.append(f"{where}: missing extracted_by")
    if p.status == "checked":
        if not p.checked_by:
            problems.append(f"{where}: status checked requires checked_by")
        elif p.extracted_by in p.checked_by:
            problems.append(f"{where}: checker must differ from extractor (two-key rule)")
    if p.status in ("needs-source", "conflict"):
        if p.value is not None:
            problems.append(f"{where}: status {p.status} must have value: null")
        minimum = 1 if p.status == "needs-source" else 2
        if len(p.candidates) < minimum:
            problems.append(f"{where}: status {p.status} needs at least {minimum} candidate(s)")
        for cand in p.candidates:
            src = cand.get("source")
            if src and src not in references:
                problems.append(f"{where}: candidate source {src!r} is not in references.yaml")
    return problems


class MaterialDB:
    """Read-only view over ``data/materials/*.yaml``."""

    def __init__(
        self, materials: dict[str, dict[str, Parameter]], references: dict[str, Reference]
    ):
        self._materials = materials
        self.references = references

    @classmethod
    def load(
        cls, directory: str | Path | None = None, references_path: str | None = None
    ) -> MaterialDB:
        if directory is None:
            directory = Path(str(resources.files("opentcad").joinpath("data/materials")))
        materials: dict[str, dict[str, Parameter]] = {}
        for file in sorted(Path(directory).glob("*.yaml")):
            raw = yaml.safe_load(file.read_text(encoding="utf-8"))
            mat_id = raw["id"]
            materials[mat_id] = {
                name: _parse_parameter(mat_id, name, entry)
                for name, entry in (raw.get("parameters") or {}).items()
            }
        return cls(materials, load_references(references_path))

    def materials(self) -> list[str]:
        return sorted(self._materials)

    def parameters(self, material: str) -> dict[str, Parameter]:
        if material not in self._materials:
            raise ParameterError(f"unknown material {material!r}; known: {self.materials()}")
        return dict(self._materials[material])

    def get(self, material: str, name: str) -> Parameter:
        params = self.parameters(material)
        if name not in params:
            raise ParameterError(f"{material} has no parameter {name!r}")
        return params[name]

    def value(
        self,
        material: str,
        name: str,
        *,
        policy: str = "dev",
        override: float | None = None,
    ) -> float:
        """Return a usable value, enforcing the status policy unless ``override`` is given."""
        if override is not None:
            return float(override)
        if policy not in POLICIES:
            raise ValueError(f"policy must be one of {sorted(POLICIES)}")
        p = self.get(material, name)
        if p.status not in POLICIES[policy] or p.value is None:
            raise ParameterError(
                f"{material}.{name} has status {p.status!r}, not usable under policy {policy!r}. "
                "Resolve its source (docs/literature-policy.md) or pass an explicit override."
            )
        return p.value

    def validate(self) -> list[str]:
        problems: list[str] = []
        for material in self.materials():
            for p in self._materials[material].values():
                problems.extend(validate_parameter(p, self.references))
        return problems

    def status_counts(self) -> dict[str, int]:
        counts = {s: 0 for s in STATUSES}
        for material in self.materials():
            for p in self._materials[material].values():
                counts[p.status] = counts.get(p.status, 0) + 1
        return counts
