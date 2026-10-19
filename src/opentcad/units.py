"""Physical constants, loaded from the cited CODATA table in ``data/constants.yaml``.

Never hard-code a physical constant elsewhere in the code base; read it from here.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from importlib import resources

import yaml

CM_PER_M = 1.0e2


@dataclass(frozen=True)
class PhysicalConstants:
    """Constants in the units the simulator uses (DEVSIM models here are cm-based)."""

    q: float  # elementary charge, C
    k_B: float  # Boltzmann constant, J/K
    eps0: float  # vacuum permittivity, F/cm

    def thermal_voltage(self, temperature_K: float) -> float:
        """k_B*T/q in volts."""
        return self.k_B * temperature_K / self.q


def _load_table() -> dict:
    text = resources.files("opentcad").joinpath("data/constants.yaml").read_text(encoding="utf-8")
    return yaml.safe_load(text)


@lru_cache(maxsize=1)
def constants() -> PhysicalConstants:
    """Return the constants table (cached)."""
    table = _load_table()["constants"]
    return PhysicalConstants(
        q=float(table["elementary_charge"]["value"]),
        k_B=float(table["boltzmann_constant"]["value"]),
        eps0=float(table["vacuum_permittivity"]["value"]) / CM_PER_M,  # F/m -> F/cm
    )


def constant_records() -> dict[str, dict]:
    """Raw records including provenance fields, for reports and the GUI."""
    return dict(_load_table()["constants"])
