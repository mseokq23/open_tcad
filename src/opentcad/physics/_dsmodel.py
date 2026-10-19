"""Thin helpers for declaring DEVSIM models together with their symbolic derivatives.

DEVSIM assembles the Newton Jacobian from derivative models named
``<model>:<variable>`` (node and contact models) and ``<model>:<variable>@n0`` /
``@n1`` (edge models). A missing derivative model silently becomes zero and
breaks convergence, so every model declared through these helpers lists the
solution variables it depends on and gets its derivatives from SYMDIFF ``diff()``.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from types import ModuleType

from opentcad._devsim import get_devsim


def num(value: float) -> str:
    """Format a number for a DEVSIM/SYMDIFF expression.

    SYMDIFF reads digit-only literals as 32-bit integers, so ``10000000000000000``
    silently becomes 1874919424 (docs/known-issues.md, KI-003). Always interpolate
    numbers through this function, which emits a float literal with an exponent.
    """
    return f"{float(value):.17e}"


@dataclass(frozen=True)
class Region:
    """A (device, region) pair with helpers for model declaration."""

    device: str
    region: str

    @property
    def ds(self) -> ModuleType:
        return get_devsim()

    def set_param(self, name: str, value: float) -> None:
        self.ds.set_parameter(device=self.device, region=self.region, name=name, value=value)

    def get_param(self, name: str) -> float:
        return float(self.ds.get_parameter(device=self.device, region=self.region, name=name))

    def solution(self, name: str) -> None:
        """Declare a node solution variable and its edge projections (name@n0, name@n1)."""
        self.ds.node_solution(device=self.device, region=self.region, name=name)
        self.ds.edge_from_node_model(device=self.device, region=self.region, node_model=name)

    def node(self, name: str, expression: str, wrt: Iterable[str] = ()) -> None:
        self.ds.node_model(device=self.device, region=self.region, name=name, equation=expression)
        for var in wrt:
            self.ds.node_model(
                device=self.device,
                region=self.region,
                name=f"{name}:{var}",
                equation=f"diff({expression}, {var})",
            )

    def edge(self, name: str, expression: str, wrt: Iterable[str] = ()) -> None:
        self.ds.edge_model(device=self.device, region=self.region, name=name, equation=expression)
        for var in wrt:
            for end in ("n0", "n1"):
                self.ds.edge_model(
                    device=self.device,
                    region=self.region,
                    name=f"{name}:{var}@{end}",
                    equation=f"diff({expression}, {var}@{end})",
                )

    def edge_raw(self, name: str, expression: str) -> None:
        """Declare an edge model exactly as written (for hand-written derivatives)."""
        self.ds.edge_model(device=self.device, region=self.region, name=name, equation=expression)

    def contact_node(
        self, contact: str, name: str, expression: str, wrt: Iterable[str] = ()
    ) -> None:
        self.ds.contact_node_model(
            device=self.device, contact=contact, name=name, equation=expression
        )
        for var in wrt:
            self.ds.contact_node_model(
                device=self.device,
                contact=contact,
                name=f"{name}:{var}",
                equation=f"diff({expression}, {var})",
            )

    def has_node(self, name: str) -> bool:
        return name in self.ds.get_node_model_list(device=self.device, region=self.region)

    def has_edge(self, name: str) -> bool:
        return name in self.ds.get_edge_model_list(device=self.device, region=self.region)

    def node_values(self, name: str) -> list[float]:
        return list(
            self.ds.get_node_model_values(device=self.device, region=self.region, name=name)
        )

    def edge_values(self, name: str) -> list[float]:
        return list(
            self.ds.get_edge_model_values(device=self.device, region=self.region, name=name)
        )

    def set_node_values(
        self, name: str, values: list[float] | None = None, init_from: str | None = None
    ) -> None:
        if init_from is not None:
            self.ds.set_node_values(
                device=self.device, region=self.region, name=name, init_from=init_from
            )
        else:
            self.ds.set_node_values(
                device=self.device, region=self.region, name=name, values=list(values or [])
            )
