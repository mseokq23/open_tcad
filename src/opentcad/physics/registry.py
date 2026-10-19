"""Registry of physics models: one entry per model, each linked to its spec and sources.

The GUI lists models from here (with their citations), the verification report
checks that every registered model has a spec in ``specs/models/``, and
``scripts/check_citations.py`` checks that every source id resolves.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

KINDS = (
    "core",
    "statistics",
    "mobility",
    "recombination",
    "generation",
    "bandgap",
    "contact",
    "doping",
)


@dataclass(frozen=True)
class ModelInfo:
    id: str  # stable identifier, e.g. "recombination.srh"
    name: str  # human-readable name
    kind: str  # one of KINDS
    spec: str  # spec file under specs/models/, e.g. "MOD-RG-001"
    sources: tuple[str, ...]  # reference ids (data/references.yaml)
    parameters: tuple[str, ...] = ()  # DEVSIM parameter names the model reads
    setup: Callable[..., None] | None = field(default=None, compare=False, hash=False)
    status: str = "implemented"  # draft | implemented | verified


_REGISTRY: dict[str, ModelInfo] = {}


def register(info: ModelInfo) -> ModelInfo:
    if info.kind not in KINDS:
        raise ValueError(f"model kind must be one of {KINDS}, got {info.kind!r}")
    if info.id in _REGISTRY and _REGISTRY[info.id] != info:
        raise ValueError(f"model id {info.id!r} is already registered")
    _REGISTRY[info.id] = info
    return info


def get(model_id: str) -> ModelInfo:
    _ensure_loaded()
    return _REGISTRY[model_id]


def available(kind: str | None = None) -> list[ModelInfo]:
    _ensure_loaded()
    models = sorted(_REGISTRY.values(), key=lambda m: m.id)
    return [m for m in models if kind is None or m.kind == kind]


def _ensure_loaded() -> None:
    """Import every public module of ``opentcad.physics``; importing a module registers its models.

    New model modules are picked up automatically, so parallel PRs never edit a shared list.
    Importing them does not import DEVSIM (that happens lazily in ``opentcad._devsim``).
    """
    import importlib
    import pkgutil

    import opentcad.physics as package

    for module in pkgutil.iter_modules(package.__path__):
        if not module.name.startswith("_") and module.name != "registry":
            importlib.import_module(f"opentcad.physics.{module.name}")
