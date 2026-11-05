"""Named conversion profiles, loaded from the packaged ``profiles.toml``."""

from __future__ import annotations

import platform
import tomllib
from dataclasses import dataclass, field
from functools import cache
from importlib import resources
from typing import Any, Literal

Pipeline = Literal["standard", "vlm"]
OcrEngine = Literal["rapidocr", "tesseract", "ocrmac"]
ModelSource = Literal["hf", "rapidocr"]

_PIPELINES = ("standard", "vlm")
_OCR_ENGINES = ("rapidocr", "tesseract", "ocrmac")
_SOURCES = ("hf", "rapidocr")
_PLATFORMS = ("any", "darwin-arm64")


class ProfileError(ValueError):
    """Unknown profile, invalid profile data, or profile not usable on this platform."""


@dataclass(frozen=True)
class ModelSpec:
    key: str
    source: ModelSource
    repo: str
    revision: str
    folder: str
    license: str
    backend: str | None = None
    lang: str | None = None
    model_size: str | None = None


@dataclass(frozen=True)
class Profile:
    name: str
    pipeline: Pipeline
    models: tuple[ModelSpec, ...]
    device: str = "auto"
    images_scale: float = 2.0
    image_export: str = "referenced"
    platforms: str = "any"
    optional: bool = False
    ocr_engine: OcrEngine | None = None
    ocr_mode: str = "default"
    ocr_lang: tuple[str, ...] = field(default_factory=tuple)
    vlm_spec: str | None = None

    def available_here(self) -> bool:
        return self.platforms == "any" or self.platforms == current_platform()


def current_platform() -> str:
    """Return the platform tag used in profiles (``darwin-arm64`` or ``<os>-<arch>``)."""
    system = platform.system().lower()
    machine = platform.machine().lower()
    if machine == "aarch64":
        machine = "arm64"
    return f"{system}-{machine}"


def _require(table: dict[str, Any], key: str, where: str) -> Any:
    if key not in table:
        raise ProfileError(f"{where}: missing field '{key}'")
    return table[key]


def _parse_model(key: str, raw: dict[str, Any]) -> ModelSpec:
    where = f"model '{key}'"
    source = _require(raw, "source", where)
    if source not in _SOURCES:
        raise ProfileError(f"{where}: unknown source '{source}'")
    return ModelSpec(
        key=key,
        source=source,
        repo=_require(raw, "repo", where),
        revision=_require(raw, "revision", where),
        folder=_require(raw, "folder", where),
        license=_require(raw, "license", where),
        backend=raw.get("backend"),
        lang=raw.get("lang"),
        model_size=raw.get("model_size"),
    )


def _parse_profile(name: str, raw: dict[str, Any], models: dict[str, ModelSpec]) -> Profile:
    where = f"profile '{name}'"
    pipeline = _require(raw, "pipeline", where)
    if pipeline not in _PIPELINES:
        raise ProfileError(f"{where}: unknown pipeline '{pipeline}'")
    ocr_engine = raw.get("ocr_engine")
    vlm_spec = raw.get("vlm_spec")
    if pipeline == "standard" and ocr_engine not in _OCR_ENGINES:
        raise ProfileError(f"{where}: standard pipeline needs ocr_engine in {_OCR_ENGINES}")
    if pipeline == "vlm" and not vlm_spec:
        raise ProfileError(f"{where}: vlm pipeline needs vlm_spec")
    platforms = raw.get("platforms", "any")
    if platforms not in _PLATFORMS:
        raise ProfileError(f"{where}: unknown platforms '{platforms}'")
    try:
        used = tuple(models[key] for key in _require(raw, "models", where))
    except KeyError as exc:
        raise ProfileError(f"{where}: unknown model {exc}") from None
    return Profile(
        name=name,
        pipeline=pipeline,
        models=used,
        device=raw.get("device", "auto"),
        images_scale=float(raw.get("images_scale", 2.0)),
        image_export=raw.get("image_export", "referenced"),
        platforms=platforms,
        optional=bool(raw.get("optional", False)),
        ocr_engine=ocr_engine,
        ocr_mode=raw.get("ocr_mode", "default"),
        ocr_lang=tuple(raw.get("ocr_lang", ())),
        vlm_spec=vlm_spec,
    )


@dataclass(frozen=True)
class Catalog:
    default: str
    profiles: dict[str, Profile]

    def get(self, name: str | None = None) -> Profile:
        """Return a profile by name (``None`` or ``"default"`` means the default one)."""
        resolved = self.default if name in (None, "default") else name
        assert resolved is not None
        try:
            return self.profiles[resolved]
        except KeyError:
            known = ", ".join(sorted(self.profiles))
            raise ProfileError(f"unknown profile '{name}' (known: default, {known})") from None

    def get_usable(self, name: str | None = None) -> Profile:
        """Like :meth:`get`, but fail if the profile does not run on this platform."""
        profile = self.get(name)
        if not profile.available_here():
            raise ProfileError(
                f"profile '{profile.name}' needs platform {profile.platforms}; "
                f"this is {current_platform()}"
            )
        return profile


def parse_catalog(data: dict[str, Any]) -> Catalog:
    models = {key: _parse_model(key, raw) for key, raw in data.get("models", {}).items()}
    profiles = {
        name: _parse_profile(name, raw, models) for name, raw in data.get("profiles", {}).items()
    }
    default = _require(data, "default", "profiles.toml")
    if default not in profiles:
        raise ProfileError(f"default profile '{default}' is not defined")
    return Catalog(default=default, profiles=profiles)


@cache
def load_catalog() -> Catalog:
    text = resources.files("docconv").joinpath("profiles.toml").read_text(encoding="utf-8")
    return parse_catalog(tomllib.loads(text))
