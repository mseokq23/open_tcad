"""1D abrupt PN diode: the phase-0 reference device used by the verification suite.

Geometry: anode (p side) at x = 0, junction at x = length_p, cathode (n side) at the end.
All lengths in cm, densities in cm^-3, mobilities in cm^2/(V s), lifetimes in s.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from opentcad.materials import MaterialDB
from opentcad.mesh import MeshLine, build_1d_mesh
from opentcad.physics import contacts, doping, poisson
from opentcad.physics._dsmodel import Region
from opentcad.units import constants

ANODE = "anode"
CATHODE = "cathode"


@dataclass(frozen=True)
class DiodeParams:
    """Inputs for :func:`build_pn_diode_1d`.

    Material values here are *inputs*. Use :meth:`from_material_db` to fill them from
    the cited material database; values passed directly are the caller's responsibility.
    """

    relative_permittivity: float
    intrinsic_density_cm3: float
    length_p_cm: float = 10e-4
    length_n_cm: float = 10e-4
    acceptors_cm3: float = 1e16
    donors_cm3: float = 1e16
    temperature_K: float = 300.0
    mu_n_cm2_Vs: float = 1000.0
    mu_p_cm2_Vs: float = 400.0
    tau_n_s: float = 1e-6
    tau_p_s: float = 1e-6
    spacing_contact_cm: float = 2e-6
    spacing_junction_cm: float = 2e-7

    @classmethod
    def from_material_db(
        cls,
        db: MaterialDB,
        material: str = "Si",
        *,
        policy: str = "dev",
        relative_permittivity: float | None = None,
        intrinsic_density_cm3: float | None = None,
        **geometry_and_transport: float,
    ) -> DiodeParams:
        """Fill material inputs from the database; explicit keyword values override it."""
        eps_r = db.value(
            material, "relative_permittivity", policy=policy, override=relative_permittivity
        )
        n_i = db.value(
            material,
            "intrinsic_carrier_density_300K",
            policy=policy,
            override=intrinsic_density_cm3,
        )
        return cls(relative_permittivity=eps_r, intrinsic_density_cm3=n_i, **geometry_and_transport)


@dataclass(frozen=True)
class DeviceHandle:
    device: str
    region: str
    anode: str
    cathode: str
    params: DiodeParams

    @property
    def r(self) -> Region:
        return Region(self.device, self.region)

    def describe(self) -> dict:
        return {"device": self.device, "region": self.region, **asdict(self.params)}


def _set_region_parameters(r: Region, p: DiodeParams) -> None:
    c = constants()
    for name, value in (
        ("Permittivity", p.relative_permittivity * c.eps0),
        ("ElectronCharge", c.q),
        ("n_i", p.intrinsic_density_cm3),
        ("T", p.temperature_K),
        ("V_t", c.thermal_voltage(p.temperature_K)),
        ("mu_n", p.mu_n_cm2_Vs),
        ("mu_p", p.mu_p_cm2_Vs),
        ("taun", p.tau_n_s),
        ("taup", p.tau_p_s),
        ("n1", p.intrinsic_density_cm3),  # trap level at the intrinsic level (MOD-RG-001)
        ("p1", p.intrinsic_density_cm3),
    ):
        r.set_param(name, value)


def build_pn_diode_1d(p: DiodeParams, device: str = "pn1d", material: str = "Si") -> DeviceHandle:
    """Create mesh, device, doping and the equilibrium Poisson problem (not yet solved)."""
    mesh = f"{device}_mesh"
    region = "bulk"
    build_1d_mesh(
        mesh,
        [
            MeshLine(0.0, p.spacing_contact_cm, ANODE),
            MeshLine(p.length_p_cm, p.spacing_junction_cm, "junction"),
            MeshLine(p.length_p_cm + p.length_n_cm, p.spacing_contact_cm, CATHODE),
        ],
        region=region,
        material=material,
        contacts=[(ANODE, ANODE), (CATHODE, CATHODE)],
    )
    r = Region(device, region)
    r.ds.create_device(mesh=mesh, device=device)
    _set_region_parameters(r, p)
    doping.setup_step_junction(r, p.length_p_cm, p.acceptors_cm3, p.donors_cm3)
    poisson.setup_potential_only(r)
    for contact in (ANODE, CATHODE):
        contacts.setup_ohmic_potential(r, contact)
    return DeviceHandle(device=device, region=region, anode=ANODE, cathode=CATHODE, params=p)
