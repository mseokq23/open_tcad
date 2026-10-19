"""DEVSIM physics model builders. One module per model family; each registers a ModelInfo.

Rules for adding a model (docs/agent-workflow.md, docs/literature-policy.md):
1. A merged spec in specs/models/ comes first; the module docstring names its spec id.
2. Every parameter is read from DEVSIM parameters set from the material DB or user input,
   never a literal number inside an equation string (structural constants like 0.5 excepted).
3. Declare derivatives for every solution variable a model depends on (see _dsmodel.Region).
4. Register the model with its spec id and source ids.
"""

from opentcad.physics.registry import ModelInfo, available, get, register

__all__ = ["ModelInfo", "available", "get", "register"]
