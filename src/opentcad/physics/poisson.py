"""Poisson equation, Boltzmann statistics. Spec: specs/models/MOD-DD-001.md.

Sign convention (DEVSIM finite-volume form): residual at a node is
  sum_edges(EdgeCouple * eps * E_edge) + NodeVolume * (-q * (p - n + N_D - N_A)) = 0
with E_edge = (psi@n0 - psi@n1) / L, i.e. div(eps*E) = rho with E = -grad(psi).
The potential psi is referenced to the intrinsic level, so n = n_i*exp(psi/V_t) at equilibrium.
"""

from __future__ import annotations

from opentcad.physics._dsmodel import Region
from opentcad.physics.registry import ModelInfo, register

POTENTIAL = "Potential"


def setup_potential_only(r: Region) -> None:
    """Equilibrium Poisson equation with carriers given by Boltzmann statistics.

    Requires parameters ``Permittivity`` (F/cm), ``ElectronCharge`` (C), ``n_i`` (cm^-3),
    ``V_t`` (V) and node model ``NetDoping`` (cm^-3).
    """
    r.solution(POTENTIAL)
    r.node("IntrinsicElectrons", "n_i*exp(Potential/V_t)", wrt=[POTENTIAL])
    r.node("IntrinsicHoles", "n_i^2/IntrinsicElectrons", wrt=[POTENTIAL])
    r.node(
        "IntrinsicCharge", "kahan3(IntrinsicHoles, -IntrinsicElectrons, NetDoping)", wrt=[POTENTIAL]
    )
    r.node("PotentialIntrinsicCharge", "-ElectronCharge * IntrinsicCharge", wrt=[POTENTIAL])
    r.edge("ElectricField", "(Potential@n0 - Potential@n1)*EdgeInverseLength", wrt=[POTENTIAL])
    r.edge("PotentialEdgeFlux", "Permittivity * ElectricField", wrt=[POTENTIAL])
    r.ds.equation(
        device=r.device,
        region=r.region,
        name="PotentialEquation",
        variable_name=POTENTIAL,
        node_model="PotentialIntrinsicCharge",
        edge_model="PotentialEdgeFlux",
        variable_update="log_damp",
    )


def setup_poisson_with_carriers(r: Region) -> None:
    """Replace the equilibrium Poisson equation with one using solved Electrons/Holes."""
    r.node(
        "PotentialNodeCharge",
        "-ElectronCharge*kahan3(Holes, -Electrons, NetDoping)",
        wrt=["Electrons", "Holes"],
    )
    r.ds.equation(
        device=r.device,
        region=r.region,
        name="PotentialEquation",
        variable_name=POTENTIAL,
        node_model="PotentialNodeCharge",
        edge_model="PotentialEdgeFlux",
        variable_update="log_damp",
    )


register(
    ModelInfo(
        id="core.poisson-boltzmann",
        name="Poisson equation with Boltzmann statistics",
        kind="core",
        spec="MOD-DD-001",
        sources=("selberherr-1984",),
        parameters=("Permittivity", "ElectronCharge", "n_i", "V_t"),
        setup=setup_potential_only,
    )
)
