"""Open TCAD: literature-grounded semiconductor device simulation built on DEVSIM.

Package map (see docs/architecture.md):

* ``opentcad.units``         physical constants from the cited CODATA table
* ``opentcad.literature``    machine-readable bibliography (``data/references.yaml``)
* ``opentcad.materials``     material parameter database with provenance and status gates
* ``opentcad.physics``       DEVSIM model builders, one module per model family
* ``opentcad.devices``       parameterised device builders (structure + mesh + doping)
* ``opentcad.solver``        solve orchestration: equilibrium, drift-diffusion, bias sweeps
* ``opentcad.verification``  closed-form reference solutions used by the verification tests
* ``opentcad.gui``           PySide6 application (optional ``[gui]`` extra)
"""

__version__ = "0.0.1"
