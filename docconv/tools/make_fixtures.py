"""Regenerate the DoclingDocument fixtures used by the fast tests.

Usage (from the docconv folder; needs `docconv models download` and, for the
synthetic inputs, `tools/synthetic/generate.py`):
    uv run python tools/make_fixtures.py

Why generated files are versioned here: the fast tests (and the fast CI job) must
not load models, but producing a DoclingDocument does. So these JSON files are the
one exception to "do not version generated files". Never edit them by hand;
regenerate them whenever the Docling version or a model revision changes.

Inputs: the 6 real test cases and the `text` variant of the 5 synthetic templates,
converted with profile standard-rapidocr (C1). Reserved cases are never used.
Pictures keep their place and size, but their pixels are replaced by a 1x1 PNG so
that the files stay small (Docling would otherwise embed every image).
"""

from __future__ import annotations

from pathlib import Path

from docling_core.types.doc.base import ImageRefMode
from docling_core.types.doc.document import DoclingDocument, ImageRef
from PIL import Image

from docconv import engine
from docconv.profiles import load_catalog

PROJECT = Path(__file__).resolve().parents[1]
OUT = PROJECT / "tests" / "fixtures" / "doclingdocs"
PROFILE = "standard-rapidocr"
REAL = [
    "b2-week_01-01_grammar-source.pdf",
    "b2-week_01-02_reading-source.pdf",
    "b2-week_01-05_transformation-source.pdf",
    "b2-week_02-01_grammar-source.png",
    "b2-week_02-02_reading-source.pdf",
    "b2-week_03-02_reading-source.pdf",
]
SYNTHETIC = ["exercises", "reading", "styles", "summary", "table"]


def inputs() -> list[Path]:
    real = [PROJECT / "data/inputs/real" / name for name in REAL]
    synthetic = [PROJECT / f"data/inputs/synthetic/syn-{t}-text.pdf" for t in SYNTHETIC]
    missing = [p for p in real + synthetic if not p.is_file()]
    if missing:
        raise SystemExit(f"missing inputs (generate the synthetic set first): {missing}")
    return real + synthetic


def strip_pixels(doc: DoclingDocument) -> DoclingDocument:
    """Return a copy whose pictures and pages carry a 1x1 placeholder image."""
    light = doc.model_copy(deep=True)
    tiny = ImageRef.from_pil(Image.new("RGB", (1, 1), "white"), dpi=72)
    for picture in light.pictures:
        if picture.image is not None:
            picture.image = tiny.model_copy(update={"size": picture.image.size})
    for page in light.pages.values():
        page.image = None
    return light


def main() -> None:
    profile = load_catalog().get(PROFILE)
    OUT.mkdir(parents=True, exist_ok=True)
    for path in inputs():
        doc = strip_pixels(engine.convert_file(path, profile).document)
        target = OUT / f"{path.stem}.json"
        doc.save_as_json(target, image_mode=ImageRefMode.EMBEDDED)
        print(f"{target.relative_to(PROJECT)} ({target.stat().st_size // 1024} KiB)")


if __name__ == "__main__":
    main()
