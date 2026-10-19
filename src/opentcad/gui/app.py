"""Main window skeleton. The design agent owns this module (docs/design-guide.md).

Layout (TCAD workflow, left to right): project tree -> central workspace (structure,
mesh, results tabs) -> property inspector; run log at the bottom.
"""

from __future__ import annotations

import sys

WORKFLOW = ("Structure", "Mesh", "Physics", "Simulation", "Results")


def _qt():
    try:
        from PySide6 import QtCore, QtGui, QtWidgets
    except ImportError as exc:  # pragma: no cover - depends on optional extra
        raise SystemExit(
            "The GUI needs the optional dependencies: pip install 'opentcad[gui]'"
        ) from exc
    return QtCore, QtGui, QtWidgets


def build_main_window():
    """Create (but do not show) the main window. Used by run() and by snapshot tests."""
    QtCore, _QtGui, QtWidgets = _qt()

    window = QtWidgets.QMainWindow()
    window.setObjectName("MainWindow")
    window.setWindowTitle("Open TCAD")
    window.resize(1280, 800)

    tree = QtWidgets.QTreeWidget()
    tree.setObjectName("ProjectTree")
    tree.setHeaderLabel("Project")
    for step in WORKFLOW:
        QtWidgets.QTreeWidgetItem(tree, [step])
    project_dock = QtWidgets.QDockWidget("Project", window)
    project_dock.setObjectName("ProjectDock")
    project_dock.setWidget(tree)
    window.addDockWidget(QtCore.Qt.DockWidgetArea.LeftDockWidgetArea, project_dock)

    tabs = QtWidgets.QTabWidget()
    tabs.setObjectName("Workspace")
    for name in ("Structure", "Mesh", "Results"):
        placeholder = QtWidgets.QLabel(f"{name} view (not implemented yet)")
        placeholder.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        tabs.addTab(placeholder, name)
    window.setCentralWidget(tabs)

    inspector = QtWidgets.QWidget()
    form = QtWidgets.QFormLayout(inspector)
    form.addRow("Selection", QtWidgets.QLabel("—"))
    inspector_dock = QtWidgets.QDockWidget("Properties", window)
    inspector_dock.setObjectName("PropertiesDock")
    inspector_dock.setWidget(inspector)
    window.addDockWidget(QtCore.Qt.DockWidgetArea.RightDockWidgetArea, inspector_dock)

    log = QtWidgets.QPlainTextEdit()
    log.setObjectName("RunLog")
    log.setReadOnly(True)
    log.setPlaceholderText("Simulation log")
    log_dock = QtWidgets.QDockWidget("Log", window)
    log_dock.setObjectName("LogDock")
    log_dock.setWidget(log)
    window.addDockWidget(QtCore.Qt.DockWidgetArea.BottomDockWidgetArea, log_dock)

    # Initial proportions; users can resize. Revisit with the design guide (P1-DES-001).
    horizontal, vertical = QtCore.Qt.Orientation.Horizontal, QtCore.Qt.Orientation.Vertical
    window.resizeDocks([project_dock, inspector_dock], [240, 300], horizontal)
    window.resizeDocks([log_dock], [150], vertical)

    window.statusBar().showMessage("Ready")
    return window


def snapshot(path: str, width: int = 1280, height: int = 800) -> str:
    """Render the main window off-screen to a PNG (set QT_QPA_PLATFORM=offscreen headless)."""
    _QtCore, _QtGui, QtWidgets = _qt()
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    window = build_main_window()
    window.resize(width, height)
    window.show()
    app.processEvents()
    if not window.grab().save(path):
        raise RuntimeError(f"could not write {path}")
    window.close()
    return path


def run() -> int:  # pragma: no cover - interactive
    _QtCore, _QtGui, QtWidgets = _qt()
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)
    window = build_main_window()
    window.show()
    return app.exec()
