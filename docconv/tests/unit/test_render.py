from __future__ import annotations

import io

import pytest
from PIL import Image

from docconv import render
from tests.conftest import make_doc


def test_pictures_are_numbered_in_reading_order() -> None:
    out = render.render(make_doc(pictures=2), "my-doc")
    assert "![Illustration 1](my-doc.assets/image-001.png)" in out.markdown
    assert "![Illustration 2](my-doc.assets/image-002.png)" in out.markdown
    assert out.markdown.index("image-001") < out.markdown.index("image-002")
    assert [i.path for i in out.images] == [
        "my-doc.assets/image-001.png",
        "my-doc.assets/image-002.png",
    ]
    assert Image.open(io.BytesIO(out.images[0].png)).format == "PNG"


def test_text_and_trailing_newline() -> None:
    out = render.render(make_doc(pictures=0), "x")
    assert "Sample title" in out.markdown
    assert "First paragraph." in out.markdown
    assert out.markdown.endswith("\n")
    assert out.images == []


def test_picture_without_pixels_is_dropped() -> None:
    doc = make_doc(pictures=0)
    doc.add_picture()
    out = render.render(doc, "x")
    assert out.images == []
    assert "docconv:picture" not in out.markdown


def test_placeholder_mismatch_is_an_error(monkeypatch: pytest.MonkeyPatch) -> None:
    doc = make_doc(pictures=1)
    monkeypatch.setattr(type(doc), "export_to_markdown", lambda self, **kw: "no placeholder")
    with pytest.raises(RuntimeError, match="0 picture placeholders but 1 pictures"):
        render.render(doc, "x")
