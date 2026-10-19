"""Material database: schema, status gates, and internal consistency of extracted values."""

import math

import pytest

from opentcad.materials import MaterialDB, ParameterError
from opentcad.units import constants


@pytest.fixture(scope="module")
def db() -> MaterialDB:
    return MaterialDB.load()


def test_database_has_no_schema_or_provenance_problems(db):
    assert db.validate() == []


def test_needs_source_parameter_is_blocked_without_override(db):
    with pytest.raises(ParameterError):
        db.value("Si", "relative_permittivity")
    assert db.value("Si", "relative_permittivity", override=11.7) == 11.7


def test_strict_policy_rejects_values_that_are_not_two_key_checked(db):
    with pytest.raises(ParameterError):
        db.value("Si", "bandgap_300K", policy="strict")
    assert db.value("Si", "bandgap_300K", policy="dev") == pytest.approx(1.12)


def test_bandgap_temperature_law_reproduces_300K_value(db):
    # Guards against transcription errors in the three extracted coefficients.
    e0 = db.value("Si", "bandgap_T_E0")
    alpha = db.value("Si", "bandgap_T_alpha")
    beta = db.value("Si", "bandgap_T_beta")
    eg300 = e0 - alpha * 300.0**2 / (300.0 + beta)
    assert eg300 == pytest.approx(db.value("Si", "bandgap_300K"), abs=0.01)


def test_effective_dos_prefactors_reproduce_300K_values(db):
    t15 = 300.0**1.5
    assert db.value("Si", "effective_dos_conduction_prefactor") * t15 == pytest.approx(
        db.value("Si", "effective_dos_conduction_300K"), rel=0.02
    )
    assert db.value("Si", "effective_dos_valence_prefactor") * t15 == pytest.approx(
        db.value("Si", "effective_dos_valence_300K"), rel=0.02
    )


def test_intrinsic_density_is_consistent_with_nc_nv_and_bandgap(db):
    # n_i = sqrt(Nc*Nv)*exp(-Eg/(2 kT)); a loose bound that still catches exponent typos.
    kt_ev = constants().thermal_voltage(300.0)
    nc = db.value("Si", "effective_dos_conduction_300K")
    nv = db.value("Si", "effective_dos_valence_300K")
    eg = db.value("Si", "bandgap_300K")
    ni_calc = math.sqrt(nc * nv) * math.exp(-eg / (2 * kt_ev))
    assert ni_calc == pytest.approx(db.value("Si", "intrinsic_carrier_density_300K"), rel=0.15)
