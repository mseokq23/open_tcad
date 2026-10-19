"""Every reference is well formed, every model links to a spec file and to known sources."""

import pytest

from opentcad.literature import load_references, validate_reference
from opentcad.physics import available
from opentcad.units import constant_records


def test_all_references_are_well_formed():
    problems = [p for ref in load_references().values() for p in validate_reference(ref)]
    assert problems == []


@pytest.mark.parametrize("model", available(), ids=lambda m: m.id)
def test_model_has_spec_and_resolvable_sources(model, repo_root):
    refs = load_references()
    assert (repo_root / "specs" / "models" / f"{model.spec}.md").is_file(), (
        f"missing spec {model.spec}"
    )
    missing = [s for s in model.sources if s not in refs]
    assert not missing, f"{model.id} cites unknown sources {missing}"


def test_constants_cite_known_sources():
    refs = load_references()
    for name, record in constant_records().items():
        assert record["source"] in refs, name
        assert record.get("locator"), name
