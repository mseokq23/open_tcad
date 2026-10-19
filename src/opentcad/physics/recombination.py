"""Shockley-Read-Hall recombination. Spec: specs/models/MOD-RG-001.md.

U_SRH = (n*p - n_i^2) / (tau_p*(n + n1) + tau_n*(p + p1))   [cm^-3 s^-1]
Sources: shockley-read-1952, hall-1952.
"""

from __future__ import annotations

from opentcad.physics._dsmodel import Region
from opentcad.physics.registry import ModelInfo, register

USRH = "(Electrons*Holes - n_i^2)/(taup*(Electrons + n1) + taun*(Holes + p1))"


def setup_srh(r: Region) -> None:
    """Create USRH and the generation terms used by the continuity equations.

    Requires parameters ``taun``, ``taup`` (s) and ``n1``, ``p1`` (cm^-3).
    """
    carriers = ["Electrons", "Holes"]
    r.node("USRH", USRH, wrt=carriers)
    r.node("ElectronGeneration", "-ElectronCharge * USRH", wrt=carriers)
    r.node("HoleGeneration", "+ElectronCharge * USRH", wrt=carriers)


register(
    ModelInfo(
        id="recombination.srh",
        name="Shockley-Read-Hall recombination (single trap level)",
        kind="recombination",
        spec="MOD-RG-001",
        sources=("shockley-read-1952", "hall-1952"),
        parameters=("taun", "taup", "n1", "p1", "n_i"),
        setup=setup_srh,
    )
)
