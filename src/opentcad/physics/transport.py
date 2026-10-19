"""Drift-diffusion transport with Scharfetter-Gummel edge currents.

Spec: specs/models/MOD-DD-001.md. Sources: scharfetter-gummel-1969, selberherr-1984.

Edge currents use the Bernoulli function B(x) = x/(exp(x)-1) with
x = (psi@n0 - psi@n1)/V_t, and the identity B(-x) = B(x) + x.
"""

from __future__ import annotations

from opentcad.physics._dsmodel import Region
from opentcad.physics.registry import ModelInfo, register

CARRIERS = ("Electrons", "Holes")

ELECTRON_CURRENT = (
    "ElectronCharge*{mu}*EdgeInverseLength*V_t*"
    "kahan3(Electrons@n1*Bern01, Electrons@n1*vdiff, -Electrons@n0*Bern01)"
)
HOLE_CURRENT = (
    "-ElectronCharge*{mu}*EdgeInverseLength*V_t*"
    "kahan3(Holes@n1*Bern01, -Holes@n0*Bern01, -Holes@n0*vdiff)"
)


def setup_bernoulli(r: Region) -> None:
    """Edge models vdiff and Bern01 with hand-written derivatives (as in DEVSIM's examples)."""
    for name, expression in (
        ("vdiff", "(Potential@n0 - Potential@n1)/V_t"),
        ("vdiff:Potential@n0", "V_t^(-1)"),
        ("vdiff:Potential@n1", "-vdiff:Potential@n0"),
        ("Bern01", "B(vdiff)"),
        ("Bern01:Potential@n0", "dBdx(vdiff) * vdiff:Potential@n0"),
        ("Bern01:Potential@n1", "-Bern01:Potential@n0"),
    ):
        r.edge_raw(name, expression)


def setup_carrier_solutions(r: Region) -> None:
    """Declare Electrons/Holes and initialise them from the equilibrium solution."""
    for carrier in CARRIERS:
        r.solution(carrier)
    r.set_node_values("Electrons", init_from="IntrinsicElectrons")
    r.set_node_values("Holes", init_from="IntrinsicHoles")


def setup_currents(r: Region, mu_n: str = "mu_n", mu_p: str = "mu_p") -> None:
    """Scharfetter-Gummel electron and hole current densities (A/cm^2).

    ``mu_n`` / ``mu_p`` are DEVSIM parameter or edge-model names, so a mobility model
    can later replace the constant parameters without touching this function.
    """
    if not r.has_edge("Bern01"):
        setup_bernoulli(r)
    r.edge(
        "ElectronCurrent", ELECTRON_CURRENT.format(mu=mu_n), wrt=["Electrons", "Potential", "Holes"]
    )
    r.edge("HoleCurrent", HOLE_CURRENT.format(mu=mu_p), wrt=["Holes", "Potential", "Electrons"])


def setup_continuity(r: Region) -> None:
    """Electron and hole continuity equations. Requires ElectronGeneration/HoleGeneration."""
    r.node("NCharge", "-ElectronCharge * Electrons", wrt=["Electrons"])
    r.node("PCharge", "ElectronCharge * Holes", wrt=["Holes"])
    r.ds.equation(
        device=r.device,
        region=r.region,
        name="ElectronContinuityEquation",
        variable_name="Electrons",
        time_node_model="NCharge",
        edge_model="ElectronCurrent",
        node_model="ElectronGeneration",
        variable_update="positive",
    )
    r.ds.equation(
        device=r.device,
        region=r.region,
        name="HoleContinuityEquation",
        variable_name="Holes",
        time_node_model="PCharge",
        edge_model="HoleCurrent",
        node_model="HoleGeneration",
        variable_update="positive",
    )


register(
    ModelInfo(
        id="core.drift-diffusion-sg",
        name="Drift-diffusion with Scharfetter-Gummel discretization",
        kind="core",
        spec="MOD-DD-001",
        sources=("scharfetter-gummel-1969", "selberherr-1984"),
        parameters=("ElectronCharge", "V_t", "mu_n", "mu_p"),
        setup=setup_currents,
    )
)

register(
    ModelInfo(
        id="mobility.constant",
        name="Constant mobility (user input)",
        kind="mobility",
        spec="MOD-MOB-000",
        sources=("selberherr-1984",),
        parameters=("mu_n", "mu_p"),
    )
)
