"""Shared test fixtures.

DEVSIM is process-global: every test that builds a device must start from
``opentcad._devsim.reset()`` (the ``fresh_devsim`` fixture does this).
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def repo_root() -> Path:
    return REPO_ROOT


@pytest.fixture
def fresh_devsim():
    from opentcad._devsim import reset

    return reset()


def pytest_runtest_setup(item: pytest.Item) -> None:
    """``@pytest.mark.requires_model("mobility.masetti")`` skips until the model is registered.

    The verifier writes verification tests from the spec before the implementation exists
    (docs/agent-workflow.md §2); they start running the moment the model is registered.
    """
    wanted = [
        model_id for mark in item.iter_markers(name="requires_model") for model_id in mark.args
    ]
    if not wanted:
        return
    from opentcad.physics import available

    registered = {m.id for m in available()}
    missing = [model_id for model_id in wanted if model_id not in registered]
    if missing:
        pytest.skip(f"not implemented yet: {', '.join(missing)} (verification written first)")
