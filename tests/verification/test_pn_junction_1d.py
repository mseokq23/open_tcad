"""VER-PN-001: 1D abrupt PN junction against closed-form limits.

Spec with tolerance rationale: specs/verification/VER-PN-001.md. The inputs below are
synthetic test inputs chosen to make the analytic limits valid (low injection, negligible
recombination, short base); they are not material-database claims.
"""

from __future__ import annotations

import pytest

from opentcad._devsim import reset
from opentcad.devices import DiodeParams, build_pn_diode_1d
from opentcad.solver import (
    contact_current,
    enable_drift_diffusion,
    solve_dc,
    solve_equilibrium,
    sweep_bias,
)
from opentcad.units import constants
from opentcad.verification import analytic as ref

pytestmark = pytest.mark.verification

PARAMS = DiodeParams(
    relative_permittivity=11.7,
    intrinsic_density_cm3=1.0e10,
    acceptors_cm3=1.0e16,
    donors_cm3=1.0e16,
    length_p_cm=10e-4,
    length_n_cm=10e-4,
    mu_n_cm2_Vs=1000.0,
    mu_p_cm2_Vs=400.0,
    tau_n_s=1.0,  # recombination negligible: the short-base limit has none
    tau_p_s=1.0,
)
EPS = PARAMS.relative_permittivity * constants().eps0
JUNCTION = (
    PARAMS.acceptors_cm3,
    PARAMS.donors_cm3,
    PARAMS.intrinsic_density_cm3,
    PARAMS.temperature_K,
)


def short_base(v: float) -> float:
    return ref.short_base_diode_current(
        v,
        *JUNCTION,
        EPS,
        PARAMS.mu_n_cm2_Vs,
        PARAMS.mu_p_cm2_Vs,
        PARAMS.length_p_cm,
        PARAMS.length_n_cm,
    )


def simulate(params: DiodeParams):
    reset()
    dev = build_pn_diode_1d(params, device="ver_pn_001")
    solve_equilibrium()
    r = dev.r
    equilibrium = {
        "psi": r.node_values("Potential"),
        "E": r.edge_values("ElectricField"),
        "net_doping": r.node_values("NetDoping"),
    }
    enable_drift_diffusion(dev)
    solve_dc()
    equilibrium["J"] = contact_current(dev, dev.anode)
    forward = {
        round(p.bias_V, 6): p.currents_A_per_cm2 for p in sweep_bias(dev, dev.anode, 0.5, 0.05)
    }
    reverse = {
        round(p.bias_V, 6): p.currents_A_per_cm2 for p in sweep_bias(dev, dev.anode, -0.3, 0.1)
    }
    return dev, equilibrium, forward, reverse


@pytest.fixture(scope="module")
def result():
    return simulate(PARAMS)


def test_doping_reaches_the_device_exactly(result):
    # Regression for KI-003 (SYMDIFF integer-literal overflow turned 1e16 into 1.87e9).
    _, eq, _, _ = result
    assert eq["net_doping"][0] == pytest.approx(-PARAMS.acceptors_cm3, rel=1e-12)
    assert eq["net_doping"][-1] == pytest.approx(PARAMS.donors_cm3, rel=1e-12)


def test_built_in_potential(result):
    _, eq, _, _ = result
    assert eq["psi"][-1] - eq["psi"][0] == pytest.approx(
        ref.built_in_potential(*JUNCTION), rel=1e-9
    )


def test_peak_field_matches_depletion_approximation_with_tail_correction(result):
    _, eq, _, _ = result
    emax = max(abs(e) for e in eq["E"])
    assert emax == pytest.approx(
        ref.max_field(*JUNCTION, EPS, majority_tail_correction=True), rel=0.01
    )


def test_no_current_at_equilibrium(result):
    _, eq, _, _ = result
    assert abs(eq["J"]) < 1e-15


@pytest.mark.parametrize("bias", [0.1, 0.2, 0.3, 0.4, 0.5])
def test_forward_current_matches_short_base_theory(result, bias):
    dev, _, forward, _ = result
    assert forward[bias][dev.anode] == pytest.approx(short_base(bias), rel=0.01)


def test_ideality_factor_is_one_without_recombination(result):
    dev, _, forward, _ = result
    n = ref.ideality_factor(
        0.2, forward[0.2][dev.anode], 0.4, forward[0.4][dev.anode], PARAMS.temperature_K
    )
    assert n == pytest.approx(1.0, abs=0.005)


def test_terminal_currents_are_continuous_at_every_bias(result):
    # Kirchhoff: what enters at the anode leaves at the cathode, at every forward and reverse
    # point. Guards KI-006: in double precision the mismatch reached 0.5 % at 0.1 V and 40 %
    # in reverse bias; with extended precision it is ~1e-15 (round-off).
    dev, _, forward, reverse = result
    for bias, currents in {**forward, **reverse}.items():
        if bias == 0:
            continue
        j_a, j_c = currents[dev.anode], currents[dev.cathode]
        assert abs(j_a + j_c) <= 1e-12 * abs(j_a), f"bias {bias} V: {j_a:+.6e} vs {j_c:+.6e}"


def test_reverse_current_saturates_at_short_base_theory(result):
    dev, _, _, reverse = result
    for bias in (-0.1, -0.2, -0.3):
        assert reverse[bias][dev.anode] == pytest.approx(short_base(bias), rel=0.005)
    # The short-base saturation current still grows slightly as the depletion region widens.
    ratio = reverse[-0.3][dev.anode] / reverse[-0.1][dev.anode]
    assert ratio == pytest.approx(short_base(-0.3) / short_base(-0.1), rel=0.001)


def test_forward_current_is_mesh_converged(result):
    dev, _, forward, _ = result
    fine = DiodeParams(
        **{
            **PARAMS.__dict__,
            "spacing_contact_cm": PARAMS.spacing_contact_cm / 2,
            "spacing_junction_cm": PARAMS.spacing_junction_cm / 2,
        }
    )
    coarse_j = forward[0.4][dev.anode]
    dev_fine, _, forward_fine, _ = simulate(fine)
    assert forward_fine[0.4][dev_fine.anode] == pytest.approx(coarse_j, rel=1e-4)
