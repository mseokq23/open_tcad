"""1D meshes with DEVSIM's built-in mesher.

Each mesh line fixes a position and the local node spacing there; DEVSIM grades the
spacing between consecutive lines. Put fine spacing where the solution varies on the
Debye length (junctions, interfaces) and coarse spacing in quasi-neutral regions.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from opentcad._devsim import get_devsim


@dataclass(frozen=True)
class MeshLine:
    position_cm: float
    spacing_cm: float
    tag: str | None = None


def build_1d_mesh(
    mesh: str,
    lines: Sequence[MeshLine],
    region: str,
    material: str,
    contacts: Sequence[tuple[str, str]],
) -> None:
    """Create and finalize a single-region 1D mesh.

    ``contacts`` is a sequence of (contact_name, line_tag) pairs; the contact
    material is recorded as "metal".
    """
    if len(lines) < 2:
        raise ValueError("a 1D mesh needs at least two mesh lines")
    positions = [line.position_cm for line in lines]
    if positions != sorted(positions) or len(set(positions)) != len(positions):
        raise ValueError("mesh line positions must be strictly increasing")
    first, last = lines[0], lines[-1]
    if not first.tag or not last.tag:
        raise ValueError("the first and last mesh lines need tags")

    ds = get_devsim()
    ds.create_1d_mesh(mesh=mesh)
    for line in lines:
        kwargs = {"mesh": mesh, "pos": line.position_cm, "ps": line.spacing_cm}
        if line.tag:
            kwargs["tag"] = line.tag
        ds.add_1d_mesh_line(**kwargs)
    for name, tag in contacts:
        ds.add_1d_contact(mesh=mesh, name=name, tag=tag, material="metal")
    ds.add_1d_region(mesh=mesh, material=material, region=region, tag1=first.tag, tag2=last.tag)
    ds.finalize_mesh(mesh=mesh)
