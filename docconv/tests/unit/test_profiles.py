from __future__ import annotations

import copy
import tomllib
from collections.abc import Callable
from importlib import resources
from typing import Any

import pytest

from docconv import profiles
from docconv.profiles import ProfileError, load_catalog, parse_catalog

EXPECTED = {
    "standard-rapidocr",
    "standard-tesseract",
    "standard-fullocr",
    "vlm-granite",
    "vlm-granite-mlx",
    "standard-ocrmac",
    "vlm-glmocr",
}


def _raw() -> dict[str, Any]:
    text = resources.files("docconv").joinpath("profiles.toml").read_text(encoding="utf-8")
    return tomllib.loads(text)


def test_catalog_has_all_configurations() -> None:
    catalog = load_catalog()
    assert set(catalog.profiles) == EXPECTED
    assert catalog.get().name == "standard-rapidocr"
    assert catalog.get("default").name == "standard-rapidocr"


def test_every_model_is_pinned() -> None:
    for profile in load_catalog().profiles.values():
        assert profile.models, profile.name
        for model in profile.models:
            if model.source == "hf":
                assert len(model.revision) == 40, f"{model.key} is not pinned to a commit SHA"
            assert model.license


def test_only_glmocr_is_optional() -> None:
    optional = {p.name for p in load_catalog().profiles.values() if p.optional}
    assert optional == {"vlm-glmocr"}


def test_unknown_profile() -> None:
    with pytest.raises(ProfileError, match="unknown profile 'nope'"):
        load_catalog().get("nope")


def test_platform_gating(monkeypatch: pytest.MonkeyPatch) -> None:
    catalog = load_catalog()
    monkeypatch.setattr(profiles, "current_platform", lambda: "linux-x86_64")
    assert catalog.get_usable("vlm-granite").name == "vlm-granite"
    with pytest.raises(ProfileError, match="needs platform darwin-arm64"):
        catalog.get_usable("vlm-granite-mlx")
    monkeypatch.setattr(profiles, "current_platform", lambda: "darwin-arm64")
    assert catalog.get_usable("vlm-granite-mlx").name == "vlm-granite-mlx"


def test_current_platform_normalises_arch(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(profiles.platform, "system", lambda: "Linux")
    monkeypatch.setattr(profiles.platform, "machine", lambda: "aarch64")
    assert profiles.current_platform() == "linux-arm64"


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda d: d.pop("default"), "missing field 'default'"),
        (lambda d: d.update(default="ghost"), "default profile 'ghost'"),
        (lambda d: d["profiles"]["vlm-granite"].update(pipeline="x"), "unknown pipeline"),
        (lambda d: d["profiles"]["standard-rapidocr"].pop("ocr_engine"), "needs ocr_engine"),
        (lambda d: d["profiles"]["vlm-granite"].pop("vlm_spec"), "needs vlm_spec"),
        (lambda d: d["profiles"]["vlm-granite"].update(platforms="win"), "unknown platforms"),
        (lambda d: d["profiles"]["vlm-granite"].update(models=["ghost"]), "unknown model"),
        (lambda d: d["models"]["glm-ocr"].update(source="ftp"), "unknown source"),
        (lambda d: d["models"]["glm-ocr"].pop("revision"), "missing field 'revision'"),
    ],
)
def test_invalid_catalog(mutate: Callable[[dict[str, Any]], object], message: str) -> None:
    data = copy.deepcopy(_raw())
    mutate(data)
    with pytest.raises(ProfileError, match=message):
        parse_catalog(data)
