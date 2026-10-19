"""Solver and precision configuration of the DEVSIM wrapper (KI-001, KI-004, KI-006)."""

import pytest

from opentcad import _devsim


def test_extended_precision_is_the_default(monkeypatch):
    monkeypatch.delenv("OPENTCAD_PRECISION", raising=False)
    assert _devsim.precision_choice() == "extended"
    ds = _devsim.reset()
    assert all(ds.get_parameter(name=flag) for flag in _devsim._EXTENDED_FLAGS)


def test_precision_survives_reset_and_can_be_lowered(monkeypatch):
    monkeypatch.setenv("OPENTCAD_PRECISION", "double")
    ds = _devsim.reset()
    assert not any(ds.get_parameter(name=flag) for flag in _devsim._EXTENDED_FLAGS)
    monkeypatch.delenv("OPENTCAD_PRECISION")
    _devsim.reset()


@pytest.mark.parametrize(
    ("variable", "function"),
    [
        ("OPENTCAD_PRECISION", _devsim.precision_choice),
        ("OPENTCAD_SOLVER", _devsim.solver_choice),
    ],
)
def test_invalid_choices_are_rejected(monkeypatch, variable, function):
    monkeypatch.setenv(variable, "quadruple-pardiso")
    with pytest.raises(ValueError):
        function()
