"""GUI smoke test: the main window builds and renders off-screen."""

import os

import pytest

pytestmark = pytest.mark.gui

pytest.importorskip("PySide6", reason="install the [gui] extra to run GUI tests")


def test_main_window_renders_offscreen(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from opentcad.gui.app import snapshot

    out = snapshot(str(tmp_path / "main.png"))
    assert os.path.getsize(out) > 5_000
