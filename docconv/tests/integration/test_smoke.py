"""Smoke test with real models (profile C1). Needs `docconv models download`."""

from __future__ import annotations

import pytest

import docconv
from tests.conftest import REAL_INPUTS

pytestmark = pytest.mark.slow


def test_reading_converts_with_default_profile() -> None:
    result = docconv.convert(REAL_INPUTS / "b2-week_01-02_reading-source.pdf")
    assert result.report["profile"] == "standard-rapidocr"
    assert result.report["status"] == "success"
    assert len(result.markdown.split()) > 100
