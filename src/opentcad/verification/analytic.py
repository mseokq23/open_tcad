"""Analytic limits for an abrupt PN junction. Spec: specs/verification/VER-PN-001.md.

Textbook results (sze-ng-2007, ch. 2 "p-n Junctions"; selberherr-1984). Units: cm, V, A/cm^2.
These are independent of the simulator: never import DEVSIM here.
"""

from __future__ import annotations

import math

from opentcad.units import constants


def thermal_voltage(temperature_K: float) -> float:
    return constants().thermal_voltage(temperature_K)


def built_in_potential(acceptors: float, donors: float, n_i: float, temperature_K: float) -> float:
    """V_bi = V_t*ln(N_A*N_D/n_i^2) (non-degenerate, complete ionisation)."""
    return thermal_voltage(temperature_K) * math.log(acceptors * donors / n_i**2)


def depletion_width(
    acceptors: float,
    donors: float,
    n_i: float,
    temperature_K: float,
    eps: float,
    bias_V: float = 0.0,
    majority_tail_correction: bool = True,
) -> float:
    """Depletion-approximation width. With the correction, V_bi -> V_bi - 2*V_t."""
    q = constants().q
    vbi = built_in_potential(acceptors, donors, n_i, temperature_K)
    v = vbi - bias_V - (2 * thermal_voltage(temperature_K) if majority_tail_correction else 0.0)
    if v <= 0:
        raise ValueError("forward bias too large for the depletion approximation")
    return math.sqrt(2 * eps * v * (acceptors + donors) / (q * acceptors * donors))


def max_field(
    acceptors: float,
    donors: float,
    n_i: float,
    temperature_K: float,
    eps: float,
    bias_V: float = 0.0,
    majority_tail_correction: bool = True,
) -> float:
    """Peak field |E|max = q*N_A*N_D*W / (eps*(N_A + N_D)) in V/cm."""
    q = constants().q
    w = depletion_width(
        acceptors, donors, n_i, temperature_K, eps, bias_V, majority_tail_correction
    )
    return q * acceptors * donors * w / (eps * (acceptors + donors))


def short_base_diode_current(
    bias_V: float,
    acceptors: float,
    donors: float,
    n_i: float,
    temperature_K: float,
    eps: float,
    mu_n: float,
    mu_p: float,
    length_p: float,
    length_n: float,
) -> float:
    """Ideal short-base diode current density (low injection, no recombination, ohmic contacts).

    J = q*n_i^2*(D_n/(N_A*W_p) + D_p/(N_D*W_n))*(exp(V/V_t) - 1), D = mu*V_t, and W_p, W_n
    the quasi-neutral widths: side length minus the depletion edge (depletion approximation
    without the 2*V_t correction, matching the classical derivation).
    """
    q = constants().q
    vt = thermal_voltage(temperature_K)
    w = depletion_width(
        acceptors, donors, n_i, temperature_K, eps, bias_V, majority_tail_correction=False
    )
    xp = w * donors / (acceptors + donors)
    xn = w * acceptors / (acceptors + donors)
    j0 = (
        q
        * n_i**2
        * (mu_n * vt / (acceptors * (length_p - xp)) + mu_p * vt / (donors * (length_n - xn)))
    )
    return j0 * math.expm1(bias_V / vt)


def ideality_factor(v1: float, j1: float, v2: float, j2: float, temperature_K: float) -> float:
    """n from two points on an exponential I-V curve: n = (V2 - V1)/(V_t*ln(J2/J1))."""
    return (v2 - v1) / (thermal_voltage(temperature_K) * math.log(j2 / j1))
