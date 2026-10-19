"""Single entry point for DEVSIM, with a consistent linear-solver configuration.

DEVSIM keeps meshes, devices and parameters in process-global state, and
``devsim.reset_devsim()`` also resets the linear-solver choice back to its default.
Always use :func:`get_devsim` and :func:`reset` from this module instead of
importing ``devsim`` directly, so the solver choice survives resets.

Solver selection via the ``OPENTCAD_SOLVER`` environment variable:

* ``auto`` (default): DEVSIM's own choice. Intel MKL PARDISO when MKL is
  installed, otherwise the UMFPACK 5.1 (LGPL) solver bundled with DEVSIM.
* ``umfpack``: force the bundled UMFPACK solver (works without MKL PARDISO).
* ``mkl_pardiso``: require MKL PARDISO.

Arithmetic precision via ``OPENTCAD_PRECISION``:

* ``extended`` (default): DEVSIM's extended-precision models, equations and solver
  (``extended_model``, ``extended_equation``, ``extended_solver``). Needed for accurate
  small terminal currents: in double precision, minority-carrier densities are not resolved
  by the global update norms, and reverse-bias currents violated Kirchhoff's law by up to
  40 % in VER-PN-001 (docs/known-issues.md, KI-006).
* ``double``: plain double precision (faster; fine for high-current operating points).

Background: docs/known-issues.md (KI-001, KI-002, KI-006).
"""

from __future__ import annotations

import os
from types import ModuleType

VALID_SOLVERS = ("auto", "umfpack", "mkl_pardiso")
VALID_PRECISIONS = ("extended", "double")
_EXTENDED_FLAGS = ("extended_solver", "extended_model", "extended_equation")


def solver_choice() -> str:
    """Return the solver requested through ``OPENTCAD_SOLVER``."""
    choice = os.environ.get("OPENTCAD_SOLVER", "auto").strip().lower()
    if choice not in VALID_SOLVERS:
        raise ValueError(f"OPENTCAD_SOLVER must be one of {VALID_SOLVERS}, got {choice!r}")
    return choice


def precision_choice() -> str:
    """Return the arithmetic precision requested through ``OPENTCAD_PRECISION``."""
    choice = os.environ.get("OPENTCAD_PRECISION", "extended").strip().lower()
    if choice not in VALID_PRECISIONS:
        raise ValueError(f"OPENTCAD_PRECISION must be one of {VALID_PRECISIONS}, got {choice!r}")
    return choice


def _apply_precision(ds: ModuleType) -> None:
    extended = precision_choice() == "extended"
    for flag in _EXTENDED_FLAGS:
        ds.set_parameter(name=flag, value=extended)


def _apply_solver(ds: ModuleType) -> None:
    choice = solver_choice()
    if choice == "umfpack":
        from devsim.umfpack import umfshim  # bundled with DEVSIM

        ds.set_parameter(name="direct_solver", value="custom")
        ds.set_parameter(name="solver_callback", value=umfshim.local_solver_callback)
    elif choice == "mkl_pardiso":
        ds.set_parameter(name="direct_solver", value="mkl_pardiso")


def get_devsim() -> ModuleType:
    """Import DEVSIM and apply the configured solver."""
    import devsim

    _apply_solver(devsim)
    _apply_precision(devsim)
    return devsim


def reset() -> ModuleType:
    """Clear all DEVSIM state and re-apply the solver and precision configuration."""
    ds = get_devsim()
    ds.reset_devsim()
    _apply_solver(ds)
    _apply_precision(ds)
    return ds


def solver_info() -> dict[str, object]:
    """Return DEVSIM's own build and solver information, plus the requested choice."""
    ds = get_devsim()
    info = dict(ds.get_parameter(name="info"))
    info["direct_solver_active"] = ds.get_parameter(name="direct_solver")
    info["opentcad_solver_choice"] = solver_choice()
    info["opentcad_precision"] = precision_choice()
    return info
