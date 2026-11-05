"""Thin layer over Docling: the only module that builds a DocumentConverter.

Importing this module switches Hugging Face to offline mode. Models are read from
the artifacts folder (see ``docconv.models``); nothing is downloaded at runtime.
"""

from __future__ import annotations

import os

# Must run before any Hugging Face library is imported.
os.environ["HF_HUB_OFFLINE"] = "1"

import time  # noqa: E402
from dataclasses import dataclass  # noqa: E402
from functools import cache  # noqa: E402
from importlib.metadata import version  # noqa: E402
from pathlib import Path  # noqa: E402

from docling.datamodel import vlm_model_specs  # noqa: E402
from docling.datamodel.accelerator_options import AcceleratorDevice, AcceleratorOptions  # noqa: E402
from docling.datamodel.base_models import InputFormat  # noqa: E402
from docling.datamodel.pipeline_options import (  # noqa: E402
    OcrMacOptions,
    OcrMode,
    OcrOptions,
    PdfPipelineOptions,
    RapidOcrOptions,
    TesseractCliOcrOptions,
    VlmPipelineOptions,
)
from docling.document_converter import (  # noqa: E402
    DocumentConverter,
    FormatOption,
    ImageFormatOption,
    PdfFormatOption,
)
from docling.pipeline.vlm_pipeline import VlmPipeline  # noqa: E402
from docling.utils.accelerator_utils import decide_device  # noqa: E402
from docling_core.types.doc.document import DoclingDocument  # noqa: E402

from docconv.models import ensure_models  # noqa: E402
from docconv.profiles import Profile  # noqa: E402


@dataclass(frozen=True)
class EngineResult:
    document: DoclingDocument
    status: str
    errors: list[str]
    seconds: float


def _ocr_options(profile: Profile) -> OcrOptions:
    mode = OcrMode(profile.ocr_mode)
    lang = list(profile.ocr_lang)
    match profile.ocr_engine:
        case "rapidocr":
            return RapidOcrOptions(mode=mode)
        case "tesseract":
            return TesseractCliOcrOptions(mode=mode, lang=lang or ["eng"])
        case "ocrmac":
            return OcrMacOptions(mode=mode, lang=lang or ["en-US"])
    raise ValueError(f"unsupported OCR engine: {profile.ocr_engine}")


def _format_options(profile: Profile, artifacts: Path) -> dict[InputFormat, FormatOption]:
    accelerator = AcceleratorOptions(device=AcceleratorDevice(profile.device))
    if profile.pipeline == "vlm":
        assert profile.vlm_spec is not None
        vlm_opts = VlmPipelineOptions(
            artifacts_path=artifacts,
            vlm_options=getattr(vlm_model_specs, profile.vlm_spec),
            generate_picture_images=True,
            images_scale=profile.images_scale,
            accelerator_options=accelerator,
        )
        return {
            InputFormat.PDF: PdfFormatOption(pipeline_cls=VlmPipeline, pipeline_options=vlm_opts),
            InputFormat.IMAGE: ImageFormatOption(
                pipeline_cls=VlmPipeline, pipeline_options=vlm_opts
            ),
        }
    std_opts = PdfPipelineOptions(
        artifacts_path=artifacts,
        do_ocr=True,
        do_table_structure=True,
        ocr_options=_ocr_options(profile),
        generate_picture_images=True,
        images_scale=profile.images_scale,
        accelerator_options=accelerator,
    )
    return {
        InputFormat.PDF: PdfFormatOption(pipeline_options=std_opts),
        InputFormat.IMAGE: ImageFormatOption(pipeline_options=std_opts),
    }


@cache
def _converter(profile: Profile) -> DocumentConverter:
    artifacts = ensure_models(profile)
    return DocumentConverter(
        allowed_formats=[InputFormat.PDF, InputFormat.IMAGE],
        format_options=_format_options(profile, artifacts),
    )


def convert_file(path: Path, profile: Profile) -> EngineResult:
    """Convert one document with ``profile``. Models load on first use and stay cached."""
    converter = _converter(profile)
    start = time.monotonic()
    result = converter.convert(path, raises_on_error=True)
    return EngineResult(
        document=result.document,
        status=result.status.value,
        errors=[e.error_message for e in result.errors],
        seconds=time.monotonic() - start,
    )


def resolved_device(profile: Profile) -> str:
    return str(decide_device(profile.device))


def versions() -> dict[str, str]:
    return {pkg: version(pkg) for pkg in ("docling", "docling-core", "docling-parse")}
