from __future__ import annotations

import json
from pathlib import Path

import pytest

import docconv
from docconv import api
from tests.conftest import FakeEngine, make_doc


def test_in_memory_conversion_writes_nothing(
    fake_engine: FakeEngine, sample_pdf: Path, tmp_path: Path
) -> None:
    before = set(tmp_path.rglob("*"))
    result = docconv.convert(sample_pdf)
    assert set(tmp_path.rglob("*")) == before
    assert result.markdown_path is None
    assert "Sample title" in result.markdown
    assert len(result.images) == 1
    report = result.report
    assert report["profile"] == "standard-rapidocr"
    assert report["pages"] == [{"page": 1, "route": "standard-rapidocr"}]
    assert report["device"] == "cpu"
    assert report["verification"] is None
    assert {m["key"] for m in report["models"]} >= {"layout-heron", "tableformer"}
    assert report["max_rss_mib"] > 0
    assert report["timings"]["since_process_start_s"] > 0


def test_writes_markdown_assets_and_report(
    fake_engine: FakeEngine, sample_pdf: Path, tmp_path: Path
) -> None:
    out = tmp_path / "out"
    result = api.convert(sample_pdf, profile="standard-fullocr", output_dir=out)
    assert result.markdown_path == out / "doc.md"
    assert (out / "doc.assets" / "image-001.png").is_file()
    assert result.report_path is not None
    report = json.loads(result.report_path.read_text(encoding="utf-8"))
    assert report["profile"] == "standard-fullocr"
    assert fake_engine.calls == [(sample_pdf, "standard-fullocr")]


def test_no_assets_folder_without_images(fake_engine: FakeEngine, sample_pdf: Path) -> None:
    fake_engine.doc_factory = lambda: make_doc(pictures=0)
    result = api.convert(sample_pdf, output_dir=sample_pdf.parent / "out")
    assert result.assets_path is None
    assert not (sample_pdf.parent / "out" / "doc.assets").exists()


@pytest.mark.parametrize("name", ["missing.pdf", "notes.txt"])
def test_rejects_bad_inputs(fake_engine: FakeEngine, tmp_path: Path, name: str) -> None:
    path = tmp_path / name
    if name.endswith(".txt"):
        path.write_text("x")
    with pytest.raises(api.UnsupportedInputError):
        api.convert(path)
    assert fake_engine.calls == []


def test_unknown_profile(fake_engine: FakeEngine, sample_pdf: Path) -> None:
    with pytest.raises(docconv.ProfileError):
        api.convert(sample_pdf, profile="nope")
