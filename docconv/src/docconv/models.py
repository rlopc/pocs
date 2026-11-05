"""Model artifacts: pinned downloads and the offline artifacts folder.

Docling reads every model from ``artifacts_path`` when it is set, and then never
downloads anything (RapidOCR included, which otherwise fetches its own files from
ModelScope). That folder is ``$DOCCONV_ARTIFACTS_PATH`` or ``~/.cache/docconv/models``.
"""

from __future__ import annotations

import os
import sys
from collections.abc import Iterable
from importlib.metadata import version
from pathlib import Path

from docconv.profiles import ModelSpec, Profile

ARTIFACTS_ENV = "DOCCONV_ARTIFACTS_PATH"


class ModelsMissingError(RuntimeError):
    """A profile needs model artifacts that have not been downloaded."""


def artifacts_path() -> Path:
    configured = os.environ.get(ARTIFACTS_ENV, "")
    if configured:
        return Path(configured).expanduser()
    return Path.home() / ".cache" / "docconv" / "models"


def missing_models(profile: Profile, root: Path | None = None) -> list[ModelSpec]:
    """Return the models of ``profile`` whose folder is absent or empty."""
    base = root or artifacts_path()
    missing = []
    for spec in profile.models:
        folder = base / spec.folder
        if not folder.is_dir() or not any(folder.iterdir()):
            missing.append(spec)
    return missing


def ensure_models(profile: Profile) -> Path:
    """Fail with a clear message if ``profile`` cannot run offline; return the artifacts path."""
    root = artifacts_path()
    missing = missing_models(profile, root)
    if missing:
        names = ", ".join(f"{m.key} ({m.repo}@{m.revision})" for m in missing)
        raise ModelsMissingError(
            f"profile '{profile.name}' is missing models in {root}: {names}. "
            f"Run: docconv models download --profile {profile.name}"
        )
    return root


def _download_one(spec: ModelSpec, root: Path) -> None:
    target = root / spec.folder
    if spec.source == "hf":
        from huggingface_hub import snapshot_download

        snapshot_download(repo_id=spec.repo, revision=spec.revision, local_dir=target)
        return
    # RapidOCR: the ModelScope tag follows the installed rapidocr version.
    installed = f"v{version('rapidocr')}"
    if installed != spec.revision:
        raise RuntimeError(
            f"model '{spec.key}' pins {spec.revision} but rapidocr {installed} is installed; "
            "update the revision in profiles.toml together with the rapidocr version"
        )
    from docling.models.stages.ocr.rapid_ocr_model import RapidOcrModel

    assert spec.backend is not None and spec.lang is not None and spec.model_size is not None
    RapidOcrModel.download_models(
        backend=spec.backend, local_dir=target, lang=spec.lang, model_size=spec.model_size
    )


def download(profiles: Iterable[Profile]) -> list[ModelSpec]:
    """Download every model used by ``profiles`` at its pinned revision."""
    if "huggingface_hub" in sys.modules:
        from huggingface_hub import constants

        if constants.HF_HUB_OFFLINE:
            raise RuntimeError("cannot download models: Hugging Face offline mode is active")
    else:
        os.environ["HF_HUB_OFFLINE"] = "0"
    root = artifacts_path()
    root.mkdir(parents=True, exist_ok=True)
    seen: dict[str, ModelSpec] = {}
    for profile in profiles:
        for spec in profile.models:
            seen.setdefault(spec.key, spec)
    for spec in seen.values():
        _download_one(spec, root)
    return list(seen.values())
