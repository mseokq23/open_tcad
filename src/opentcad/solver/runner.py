"""Solve orchestration with a first convergence safeguard (step halving with rollback).

Phase 2 (backlog P2-SPEC-010, P2-CONV-001) extends this module: initial-guess strategies, damping
choices, continuation in doping/temperature, current-based convergence checks, and a
convergence benchmark suite. Extended precision is already the default (ADR-0006). Keep the public functions stable; add strategies behind them.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from opentcad._devsim import get_devsim
from opentcad.physics import contacts, poisson, recombination, transport
from opentcad.physics._dsmodel import Region

SOLUTIONS = ("Potential", "Electrons", "Holes")


class ConvergenceError(RuntimeError):
    """Newton iteration did not converge, even after step reduction."""


@dataclass(frozen=True)
class SolveSettings:
    # Carrier densities span ~1e-20..1e20 cm^-3, so the relative update norm decides
    # convergence for drift-diffusion; the absolute tolerance is deliberately loose.
    absolute_error: float = 1e10
    relative_error: float = 1e-12
    maximum_iterations: int = 40


DEFAULT_SETTINGS = SolveSettings()  # frozen, so sharing one default instance is safe


@dataclass
class OperatingPoint:
    bias_V: float
    currents_A_per_cm2: dict[str, float] = field(default_factory=dict)


def _solve(settings: SolveSettings, absolute_error: float | None = None) -> None:
    ds = get_devsim()
    try:
        ds.solve(
            type="dc",
            absolute_error=settings.absolute_error if absolute_error is None else absolute_error,
            relative_error=settings.relative_error,
            maximum_iterations=settings.maximum_iterations,
        )
    except ds.error as exc:  # DEVSIM raises devsim.error on convergence failure
        raise ConvergenceError(str(exc)) from exc


def solve_equilibrium(settings: SolveSettings = DEFAULT_SETTINGS) -> None:
    """Solve the equilibrium (potential-only) problem; potential tolerance is in volts."""
    _solve(settings, absolute_error=1.0)


def enable_drift_diffusion(dev, contact_names: tuple[str, ...] | None = None) -> None:
    """Switch an equilibrium-solved device to full drift-diffusion with SRH recombination."""
    r: Region = dev.r
    transport.setup_carrier_solutions(r)
    poisson.setup_poisson_with_carriers(r)
    recombination.setup_srh(r)
    transport.setup_currents(r)
    transport.setup_continuity(r)
    for contact in contact_names or (dev.anode, dev.cathode):
        contacts.setup_ohmic_carriers(r, contact)


def solve_dc(settings: SolveSettings = DEFAULT_SETTINGS) -> None:
    _solve(settings)


def contact_current(dev, contact: str) -> float:
    """Total (electron + hole) current at a contact, A/cm^2 in 1D.

    Sign: positive when conventional current flows into the device through this contact.
    """
    ds = get_devsim()
    return float(
        ds.get_contact_current(
            device=dev.device, contact=contact, equation="ElectronContinuityEquation"
        )
        + ds.get_contact_current(
            device=dev.device, contact=contact, equation="HoleContinuityEquation"
        )
    )


def _snapshot(dev) -> dict[str, list[float]]:
    r: Region = dev.r
    return {name: r.node_values(name) for name in SOLUTIONS}


def _restore(dev, snap: dict[str, list[float]]) -> None:
    r: Region = dev.r
    for name, values in snap.items():
        r.set_node_values(name, values=values)


def sweep_bias(
    dev,
    contact: str,
    stop_V: float,
    step_V: float,
    start_V: float | None = None,
    min_step_V: float = 1e-4,
    settings: SolveSettings = DEFAULT_SETTINGS,
    record: tuple[str, ...] | None = None,
) -> list[OperatingPoint]:
    """Ramp one contact's bias from its current value (or ``start_V``) to ``stop_V``.

    On a convergence failure the last converged solution is restored and the step is
    halved, down to ``min_step_V``. Every converged point is returned, including
    intermediate points created by step halving.
    """
    ds = get_devsim()
    name = contacts.bias_parameter(contact)
    record = record or (dev.anode, dev.cathode)
    v = float(ds.get_parameter(device=dev.device, name=name)) if start_V is None else start_V
    direction = 1.0 if stop_V >= v else -1.0
    step = abs(step_V)
    points: list[OperatingPoint] = []

    if start_V is not None:
        ds.set_parameter(device=dev.device, name=name, value=v)
        _solve(settings)
    points.append(OperatingPoint(v, {c: contact_current(dev, c) for c in record}))

    while direction * (stop_V - v) > 1e-12:
        target = v + direction * min(step, abs(stop_V - v))
        snap = _snapshot(dev)
        ds.set_parameter(device=dev.device, name=name, value=target)
        try:
            _solve(settings)
        except ConvergenceError:
            _restore(dev, snap)
            ds.set_parameter(device=dev.device, name=name, value=v)
            step /= 2.0
            if step < min_step_V:
                raise ConvergenceError(
                    f"bias sweep on {contact!r} stalled at {v:.6g} V (step < {min_step_V:g} V)"
                ) from None
            continue
        v = target
        points.append(OperatingPoint(v, {c: contact_current(dev, c) for c in record}))
        step = min(abs(step_V), step * 1.5)  # recover the step size after a success
    return points
