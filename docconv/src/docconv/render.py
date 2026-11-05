"""DoclingDocument -> Markdown.

Phase 1: Docling's own Markdown export, with pictures renamed to
``<stem>.assets/image-NNN.png`` in reading order. The output convention rules
(postprocess/) come later.
"""

from __future__ import annotations

import io
from dataclasses import dataclass

from docling_core.types.doc.base import ImageRefMode
from docling_core.types.doc.document import DoclingDocument, PictureItem

_MARK = "<!-- docconv:picture -->"


@dataclass(frozen=True)
class ImageAsset:
    """One extracted illustration: its relative path in the Markdown and PNG bytes."""

    path: str
    png: bytes


@dataclass(frozen=True)
class Rendered:
    markdown: str
    images: list[ImageAsset]


def assets_dir_name(stem: str) -> str:
    return f"{stem}.assets"


def image_path(stem: str, index: int) -> str:
    return f"{assets_dir_name(stem)}/image-{index:03d}.png"


def render(doc: DoclingDocument, stem: str) -> Rendered:
    """Export ``doc`` to Markdown, replacing each picture with a numbered image link."""
    markdown = doc.export_to_markdown(image_mode=ImageRefMode.PLACEHOLDER, image_placeholder=_MARK)
    pictures = [item for item, _ in doc.iterate_items() if isinstance(item, PictureItem)]
    pieces = markdown.split(_MARK)
    if len(pieces) - 1 != len(pictures):
        raise RuntimeError(
            f"{len(pieces) - 1} picture placeholders but {len(pictures)} pictures in document"
        )
    images: list[ImageAsset] = []
    out = [pieces[0]]
    for picture, rest in zip(pictures, pieces[1:], strict=True):
        pil = picture.get_image(doc)
        if pil is not None:
            buf = io.BytesIO()
            pil.save(buf, format="PNG")
            asset = ImageAsset(path=image_path(stem, len(images) + 1), png=buf.getvalue())
            images.append(asset)
            out.append(f"![Illustration {len(images)}]({asset.path})")
        out.append(rest)
    text = "".join(out)
    if not text.endswith("\n"):
        text += "\n"
    return Rendered(markdown=text, images=images)
