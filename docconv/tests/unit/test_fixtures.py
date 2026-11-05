"""The versioned DoclingDocument fixtures load and render.

Regenerate them with tools/make_fixtures.py.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from docling_core.types.doc.document import DoclingDocument

from docconv.render import render

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "doclingdocs"
ALL = sorted(FIXTURES.glob("*.json"))


def test_fixture_set_is_complete() -> None:
    assert len(ALL) == 11
    assert not any("02-05" in p.name or "03-01" in p.name or "03-05" in p.name for p in ALL)


@pytest.mark.parametrize("path", ALL, ids=lambda p: p.stem)
def test_fixture_renders(path: Path) -> None:
    doc = DoclingDocument.load_from_json(path)
    out = render(doc, path.stem)
    assert out.markdown.strip()
    assert len(out.images) == len(doc.pictures)
