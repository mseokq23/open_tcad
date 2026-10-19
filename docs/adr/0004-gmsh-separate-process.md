# 0004 — Gmsh runs as a separate process

Status: accepted (2026-10-19)

## Context
Gmsh is the best available open-source mesher for 2D/3D TCAD structures, but it is GPL-licensed
(with a linking exception for some libraries) and offers commercial licences for closed-source
integration. Importing its Python API loads `libgmsh` into our process.

## Decision
* Mesh generation writes a `.geo` script (or a small Python driver) and runs Gmsh as a separate
  process; `opentcad` never imports `gmsh` in library code. The result is read back as a `.msh`
  file with DEVSIM's `create_gmsh_mesh`.
* Gmsh is an optional dependency (`[mesh]` extra).

## Consequences
* Keeps the Apache-2.0 code base cleanly separated from GPL code and keeps a future binary
  distribution decision open.
* A little process overhead per mesh; negligible next to solve times.
