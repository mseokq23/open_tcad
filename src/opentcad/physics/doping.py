"""Doping profiles. Spec: specs/models/MOD-DOP-001.md."""

from __future__ import annotations

from opentcad.physics._dsmodel import Region, num
from opentcad.physics.registry import ModelInfo, register


def setup_step_junction(
    r: Region, x_junction_cm: float, acceptors_cm3: float, donors_cm3: float
) -> None:
    """Abrupt junction along x: acceptors for x < x_j, donors for x > x_j.

    Creates node models ``Acceptors``, ``Donors`` and ``NetDoping = Donors - Acceptors``.
    """
    r.node("Acceptors", f"{num(acceptors_cm3)}*step({num(x_junction_cm)} - x)")
    r.node("Donors", f"{num(donors_cm3)}*step(x - {num(x_junction_cm)})")
    r.node("NetDoping", "Donors - Acceptors")


register(
    ModelInfo(
        id="doping.step",
        name="Abrupt (step) junction doping",
        kind="doping",
        spec="MOD-DOP-001",
        sources=("sze-ng-2007",),
        setup=setup_step_junction,
    )
)
