"""Library entry point: ``convert()``."""

from __future__ import annotations

import json
import resource
import sys
import time
from dataclasses import dataclass
from importlib.metadata import version
from pathlib import Path
from types import ModuleType
from typing import Any

import psutil
from docling_core.types.doc.document import DoclingDocument

from docconv.profiles import load_catalog
from docconv.render import ImageAsset, assets_dir_name, render

SUPPORTED_SUFFIXES = frozenset({".pdf", ".png", ".jpg", ".jpeg"})


class UnsupportedInputError(ValueError):
    """The input file does not exist or its type is not supported."""


@dataclass
class Result:
    """Outcome of converting one document.

    ``markdown`` and ``images`` are always in memory. When ``convert`` gets an
    ``output_dir``, ``markdown_path``, ``report_path`` and ``assets_path`` point to
    the written files.
    """

    source: Path
    markdown: str
    images: list[ImageAsset]
    report: dict[str, Any]
    markdown_path: Path | None = None
    report_path: Path | None = None
    assets_path: Path | None = None


def _engine() -> ModuleType:
    # Imported lazily: loading Docling is slow and tests replace the engine.
    from docconv import engine

    return engine


def max_rss_mib() -> float:
    """Peak resident memory of this process in MiB.

    ``ru_maxrss`` is in bytes on macOS and in KiB on Linux.
    """
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return peak / (1024 * 1024) if sys.platform == "darwin" else peak / 1024


def seconds_since_process_start() -> float:
    # psutil ships no type information.
    return time.time() - float(psutil.Process().create_time())


def _page_count(doc: DoclingDocument) -> int:
    return len(doc.pages) or 1


def convert(
    path: str | Path, profile: str = "default", output_dir: str | Path | None = None
) -> Result:
    """Convert a PDF or image to Markdown.

    Args:
        path: input file (``.pdf``, ``.png``, ``.jpg``, ``.jpeg``).
        profile: profile name from ``profiles.toml`` (``"default"`` for the default one).
        output_dir: if given, write ``<stem>.md``, ``<stem>.assets/`` and
            ``<stem>.report.json`` there; if ``None``, nothing is written to disk.
    """
    source = Path(path)
    if not source.is_file():
        raise UnsupportedInputError(f"not a file: {source}")
    if source.suffix.lower() not in SUPPORTED_SUFFIXES:
        raise UnsupportedInputError(f"unsupported file type: {source.suffix} ({source})")

    selected = load_catalog().get_usable(profile)
    engine = _engine()
    outcome = engine.convert_file(source, selected)
    stem = source.stem
    rendered = render(outcome.document, stem)
    pages = _page_count(outcome.document)

    report: dict[str, Any] = {
        "source": str(source),
        "profile": selected.name,
        "pipeline": selected.pipeline,
        "device": engine.resolved_device(selected),
        "status": outcome.status,
        "errors": outcome.errors,
        "pages": [{"page": n, "route": selected.name} for n in range(1, pages + 1)],
        "images": len(rendered.images),
        "timings": {
            "convert_s": round(outcome.seconds, 3),
            "since_process_start_s": round(seconds_since_process_start(), 3),
        },
        "max_rss_mib": round(max_rss_mib(), 1),
        "versions": {"docconv": version("docconv"), **engine.versions()},
        "models": [{"key": m.key, "repo": m.repo, "revision": m.revision} for m in selected.models],
        "verification": None,
    }
    result = Result(
        source=source, markdown=rendered.markdown, images=rendered.images, report=report
    )
    if output_dir is not None:
        _write(result, Path(output_dir), stem)
    return result


def _write(result: Result, out_dir: Path, stem: str) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    result.markdown_path = out_dir / f"{stem}.md"
    result.markdown_path.write_text(result.markdown, encoding="utf-8")
    if result.images:
        result.assets_path = out_dir / assets_dir_name(stem)
        result.assets_path.mkdir(exist_ok=True)
        for image in result.images:
            (out_dir / image.path).write_bytes(image.png)
    result.report_path = out_dir / f"{stem}.report.json"
    result.report_path.write_text(
        json.dumps(result.report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
