"""Mesh builders. 1D uses DEVSIM's built-in mesher; 2D/3D will use Gmsh (backlog P1-MESH-*)."""

from opentcad.mesh.oned import MeshLine, build_1d_mesh

__all__ = ["MeshLine", "build_1d_mesh"]
