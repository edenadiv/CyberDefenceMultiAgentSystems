import pytest

from cdmas.validator.export import build_export


@pytest.mark.slow
async def test_build_export_structure():
    data = await build_export()
    assert set(data["topology"]["segments"]) == {"internal", "server", "public-facing", "sec-mon"}
    assert data["replay"]["events"]
    assert "metrics" in data["replay"]
    assert len(data["validation"]) == 6
    assert all("constraints" in v for v in data["validation"])
