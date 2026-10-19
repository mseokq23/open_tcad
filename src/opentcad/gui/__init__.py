"""Desktop application (PySide6). Optional: install with the ``[gui]`` extra.

Design rules: docs/design-guide.md. The GUI never calls DEVSIM in its own process;
simulations run in a worker process (backlog P1-RUN-001) so a crash or a long
solve cannot freeze the window, and DEVSIM's global state stays isolated.
"""
