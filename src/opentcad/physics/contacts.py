"""Ideal ohmic contacts. Spec: specs/models/MOD-DD-001.md, section "Contacts".

At an ideal ohmic contact the carriers are in equilibrium with the doping
(charge neutrality, n*p = n_i^2) and the potential follows the applied bias:
  n-type: psi = V + V_t*ln(n0/n_i),  p-type: psi = V - V_t*ln(p0/n_i)
with n0, p0 from charge neutrality. The 1e-10 offsets avoid log(0).
"""

from __future__ import annotations

from opentcad.physics._dsmodel import Region
from opentcad.physics.registry import ModelInfo, register

CELEC = "(1e-10 + 0.5*abs(NetDoping + (NetDoping^2 + 4*n_i^2)^(0.5)))"
CHOLE = "(1e-10 + 0.5*abs(-NetDoping + (NetDoping^2 + 4*n_i^2)^(0.5)))"


def bias_parameter(contact: str) -> str:
    """Name of the device-level parameter that holds a contact's applied bias (V)."""
    return f"{contact}_bias"


def setup_ohmic_potential(r: Region, contact: str) -> None:
    """Dirichlet condition for the potential at an ohmic contact (equilibrium Poisson)."""
    r.ds.set_parameter(device=r.device, name=bias_parameter(contact), value=0.0)
    if not r.has_edge("ContactCharge"):
        r.edge("ContactCharge", "Permittivity*ElectricField", wrt=["Potential"])
    expression = (
        f"Potential - {bias_parameter(contact)} + "
        f"ifelse(NetDoping > 0, -V_t*log({CELEC}/n_i), V_t*log({CHOLE}/n_i))"
    )
    name = f"{contact}_potential"
    r.contact_node(contact, name, expression)
    r.contact_node(contact, f"{name}:Potential", "1")
    r.ds.contact_equation(
        device=r.device,
        contact=contact,
        name="PotentialEquation",
        node_model=name,
        edge_charge_model="ContactCharge",
    )


def setup_ohmic_carriers(r: Region, contact: str) -> None:
    """Dirichlet conditions for Electrons/Holes at an ohmic contact; currents are recorded."""
    electrons = f"Electrons - ifelse(NetDoping > 0, {CELEC}, n_i^2/{CHOLE})"
    holes = f"Holes - ifelse(NetDoping < 0, {CHOLE}, n_i^2/{CELEC})"
    for carrier, expression, equation, current in (
        ("Electrons", electrons, "ElectronContinuityEquation", "ElectronCurrent"),
        ("Holes", holes, "HoleContinuityEquation", "HoleCurrent"),
    ):
        name = f"{contact}_{carrier.lower()}"
        r.contact_node(contact, name, expression)
        r.contact_node(contact, f"{name}:{carrier}", "1")
        r.ds.contact_equation(
            device=r.device,
            contact=contact,
            name=equation,
            node_model=name,
            edge_current_model=current,
        )


register(
    ModelInfo(
        id="contact.ohmic-ideal",
        name="Ideal ohmic contact (charge neutrality, equilibrium carriers)",
        kind="contact",
        spec="MOD-DD-001",
        sources=("selberherr-1984", "sze-ng-2007"),  # MOD-DD-001 Eq. (7)
        parameters=("n_i", "V_t"),
        setup=setup_ohmic_potential,
    )
)
