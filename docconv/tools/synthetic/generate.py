"""Generate the synthetic test documents and their expected Markdown.

Usage (from the docconv folder):
    uv run --group synthetic python tools/synthetic/generate.py --seed 42

Writes data/inputs/synthetic/syn-<template>-<variant>.pdf|png and
data/expected/synthetic/syn-<template>.md (both git-ignored: regenerate them).
Variants: `text` (WeasyPrint PDF) and `scan` (rasterised and degraded) for every
template, plus `png` for the table. Output is deterministic for a given seed.
On macOS, WeasyPrint needs Pango from Homebrew; if it is not found, run with
DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib.
"""

from __future__ import annotations

import argparse
import base64
import io
import time
import zlib
from pathlib import Path

import numpy as np
import pypdfium2 as pdfium
from documents import ALL
from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup
from model import Document, runs_html, to_markdown
from PIL import Image, ImageDraw
from weasyprint import HTML

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]
SCAN_DPI = 200
PNG_WIDTH = 1536
# Fixed metadata dates keep the scanned PDFs byte-identical between runs.
FIXED_DATE = time.gmtime(1767225600)  # 2026-01-01T00:00:00Z; Pillow expects a struct_time


def _env() -> Environment:
    env = Environment(
        loader=FileSystemLoader(HERE / "templates"),
        autoescape=select_autoescape(["html", "j2"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.filters["kind"] = lambda block: type(block).__name__
    # runs_html escapes every text run; only its own tags reach the template unescaped.
    env.filters["runs"] = lambda runs: Markup(runs_html(runs))  # noqa: S704
    return env


def _draw_picture(rng: np.random.Generator) -> str:
    """A simple, original illustration: coloured shapes on a light background."""
    img = Image.new("RGB", (300, 220), tuple(int(v) for v in rng.integers(215, 250, 3)))
    draw = ImageDraw.Draw(img)
    for _ in range(4):
        x0, y0 = (int(v) for v in rng.integers(0, 200, 2))
        x1, y1 = x0 + int(rng.integers(40, 110)), y0 + int(rng.integers(40, 110))
        colour = tuple(int(v) for v in rng.integers(30, 200, 3))
        if rng.random() < 0.5:
            draw.ellipse((x0, y0, x1, y1), fill=colour)
        else:
            draw.rectangle((x0, y0, x1, y1), fill=colour)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    # A data URI, not a file: the PDF must not depend on a temporary path.
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def _write_text_pdf(doc: Document, out: Path, rng: np.random.Generator) -> None:
    image_uris = {name: _draw_picture(rng) for name in doc.images}
    html = _env().get_template("document.html.j2").render(doc=doc, image_uris=image_uris)
    HTML(string=html).write_pdf(out)


def _degrade(page: Image.Image, rng: np.random.Generator) -> Image.Image:
    angle = float(rng.uniform(-1.5, 1.5))
    rotated = page.convert("L").rotate(angle, resample=Image.Resampling.BICUBIC, fillcolor=255)
    noisy = np.asarray(rotated, dtype=np.float32) + rng.normal(
        0, 8, (rotated.height, rotated.width)
    )
    img = Image.fromarray(np.clip(noisy, 0, 255).astype(np.uint8), mode="L")
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=60)
    return Image.open(io.BytesIO(buf.getvalue()))


def _write_scan_pdf(text_pdf: Path, out: Path, rng: np.random.Generator) -> None:
    pdf = pdfium.PdfDocument(text_pdf)
    pages = [_degrade(page.render(scale=SCAN_DPI / 72).to_pil(), rng) for page in pdf]
    pdf.close()
    pages[0].save(
        out,
        format="PDF",
        save_all=True,
        append_images=pages[1:],
        resolution=SCAN_DPI,
        creationDate=FIXED_DATE,
        modDate=FIXED_DATE,
    )


def _write_png(text_pdf: Path, out: Path) -> None:
    pdf = pdfium.PdfDocument(text_pdf)
    page = pdf[0]
    page.render(scale=PNG_WIDTH / page.get_width()).to_pil().save(out, format="PNG")
    pdf.close()


def generate(seed: int, inputs: Path, expected: Path) -> list[Path]:
    inputs.mkdir(parents=True, exist_ok=True)
    expected.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for factory in ALL:
        doc = factory()
        # One independent, reproducible stream per template.
        rng = np.random.default_rng([seed, zlib.crc32(doc.name.encode())])
        md = expected / f"syn-{doc.name}.md"
        md.write_text(to_markdown(doc), encoding="utf-8")
        text_pdf = inputs / f"syn-{doc.name}-text.pdf"
        _write_text_pdf(doc, text_pdf, rng)
        scan_pdf = inputs / f"syn-{doc.name}-scan.pdf"
        _write_scan_pdf(text_pdf, scan_pdf, rng)
        written += [md, text_pdf, scan_pdf]
        if doc.name == "table":
            png = inputs / f"syn-{doc.name}-png.png"
            _write_png(text_pdf, png)
            written.append(png)
    return written


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else None)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--inputs", type=Path, default=PROJECT / "data/inputs/synthetic")
    parser.add_argument("--expected", type=Path, default=PROJECT / "data/expected/synthetic")
    args = parser.parse_args()
    for path in generate(args.seed, args.inputs, args.expected):
        print(path.relative_to(PROJECT) if path.is_relative_to(PROJECT) else path)


if __name__ == "__main__":
    main()
