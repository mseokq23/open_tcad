"""Unit tests for the closed-form references (no DEVSIM involved)."""

import math

import pytest

from opentcad.units import constants
from opentcad.verification import analytic as ref

EPS = 11.7 * constants().eps0  # synthetic test input


def test_thermal_voltage_300K():
    # k_B*T/q with CODATA 2022 exact constants
    assert ref.thermal_voltage(300.0) == pytest.approx(0.025851999786435535, rel=1e-12)


def test_built_in_potential_symmetric_junction():
    vt = ref.thermal_voltage(300.0)
    assert ref.built_in_potential(1e16, 1e16, 1e10, 300.0) == pytest.approx(vt * math.log(1e12))


def test_depletion_width_scales_with_square_root_of_voltage_drop():
    w0 = ref.depletion_width(1e16, 1e16, 1e10, 300.0, EPS, 0.0, majority_tail_correction=False)
    wr = ref.depletion_width(1e16, 1e16, 1e10, 300.0, EPS, -1.0, majority_tail_correction=False)
    vbi = ref.built_in_potential(1e16, 1e16, 1e10, 300.0)
    assert wr / w0 == pytest.approx(math.sqrt((vbi + 1.0) / vbi))


def test_depletion_width_rejects_large_forward_bias():
    with pytest.raises(ValueError):
        ref.depletion_width(1e16, 1e16, 1e10, 300.0, EPS, 2.0)


def test_short_base_current_is_zero_at_equilibrium_and_rectifies():
    args = (1e16, 1e16, 1e10, 300.0, EPS, 1000.0, 400.0, 10e-4, 10e-4)
    assert ref.short_base_diode_current(0.0, *args) == 0.0
    assert ref.short_base_diode_current(0.3, *args) > 0.0
    assert ref.short_base_diode_current(-0.3, *args) < 0.0
    assert ref.short_base_diode_current(0.3, *args) > 1e3 * abs(
        ref.short_base_diode_current(-0.3, *args)
    )


def test_ideality_factor_of_ideal_exponential_is_one():
    vt = ref.thermal_voltage(300.0)
    j = lambda v: 1e-12 * math.exp(v / vt)  # noqa: E731
    assert ref.ideality_factor(0.2, j(0.2), 0.4, j(0.4), 300.0) == pytest.approx(1.0)
