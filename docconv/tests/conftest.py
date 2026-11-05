"""Shared fixtures. Fast tests never load models: ``fake_engine`` replaces Docling."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace

import pytest
from docling_core.types.doc.document import DoclingDocument, ImageRef
from docling_core.types.doc.labels import DocItemLabel
from PIL import Image

from docconv import api

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REAL_INPUTS = PROJECT_ROOT / "data" / "inputs" / "real"


def make_doc(pictures: int = 1) -> DoclingDocument:
    """A small document: title, paragraph and ``pictures`` pictures with pixel data."""
    doc = DoclingDocument(name="sample")
    doc.add_title("Sample title")
    doc.add_text(DocItemLabel.TEXT, "First paragraph.")
    for i in range(pictures):
        pil = Image.new("RGB", (4, 4), color=(i * 40 % 256, 0, 0))
        doc.add_picture(image=ImageRef.from_pil(pil, dpi=72))
    return doc


@dataclass
class FakeEngine:
    """Stands in for ``docconv.engine``; set ``fail_on`` to make a file fail."""

    doc_factory: Callable[[], DoclingDocument] = make_doc
    fail_on: set[str] = field(default_factory=set)
    calls: list[tuple[Path, str]] = field(default_factory=list)

    def convert_file(self, path: Path, profile: object) -> SimpleNamespace:
        name = getattr(profile, "name", "?")
        self.calls.append((path, name))
        if path.name in self.fail_on:
            raise RuntimeError(f"boom: {path.name}")
        return SimpleNamespace(
            document=self.doc_factory(), status="success", errors=[], seconds=0.5
        )

    def resolved_device(self, profile: object) -> str:
        return "cpu"

    def versions(self) -> dict[str, str]:
        return {"docling": "test"}


@pytest.fixture
def fake_engine(monkeypatch: pytest.MonkeyPatch) -> FakeEngine:
    engine = FakeEngine()
    monkeypatch.setattr(api, "_engine", lambda: engine)
    return engine


@pytest.fixture
def sample_pdf(tmp_path: Path) -> Path:
    """An input file; its content is irrelevant because the engine is faked."""
    path = tmp_path / "in" / "doc.pdf"
    path.parent.mkdir()
    path.write_bytes(b"%PDF-1.4\n")
    return path
