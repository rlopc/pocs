from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from docconv import api, cli, profiles
from tests.conftest import FakeEngine

runner = CliRunner()


def _tree(tmp_path: Path) -> Path:
    root = tmp_path / "docs"
    (root / "sub").mkdir(parents=True)
    for rel in ("a.pdf", "b.PNG", "sub/a.pdf", "sub/c.jpeg", "notes.txt", ".DS_Store"):
        (root / rel).write_bytes(b"x")
    return root


def test_folder_mirrors_layout_and_warns(fake_engine: FakeEngine, tmp_path: Path) -> None:
    root = _tree(tmp_path)
    out = tmp_path / "out"
    res = runner.invoke(cli.app, ["convert", str(root), "-o", str(out)])
    assert res.exit_code == 0, res.output
    assert (out / "a.md").is_file()
    assert (out / "b.md").is_file()
    assert (out / "sub" / "a.md").is_file()
    assert (out / "sub" / "c.report.json").is_file()
    assert "skipped unsupported file" in res.output
    assert "notes.txt" in res.output
    assert ".DS_Store" not in res.output
    assert len(fake_engine.calls) == 4


def test_json_output(fake_engine: FakeEngine, sample_pdf: Path, tmp_path: Path) -> None:
    res = runner.invoke(cli.app, ["convert", str(sample_pdf), "-o", str(tmp_path / "o"), "--json"])
    assert res.exit_code == 0, res.output
    reports = json.loads(res.stdout)
    assert len(reports) == 1
    assert reports[0]["profile"] == "standard-rapidocr"
    assert reports[0]["markdown_path"].endswith("doc.md")


def test_conversion_failure_keeps_going(fake_engine: FakeEngine, tmp_path: Path) -> None:
    root = _tree(tmp_path)
    fake_engine.fail_on = {"b.PNG"}
    res = runner.invoke(cli.app, ["convert", str(root), "-o", str(tmp_path / "o"), "--json"])
    assert res.exit_code == 2
    assert len(fake_engine.calls) == 4
    errors = [r for r in json.loads(res.stdout) if "error" in r]
    assert len(errors) == 1
    assert "boom: b.PNG" in errors[0]["error"]


def test_failure_in_summary_mode(fake_engine: FakeEngine, sample_pdf: Path, tmp_path: Path) -> None:
    fake_engine.fail_on = {sample_pdf.name}
    res = runner.invoke(cli.app, ["convert", str(sample_pdf), "-o", str(tmp_path / "o")])
    assert res.exit_code == 2
    assert "FAIL" in res.output


def test_verification_failure_exit_code(
    fake_engine: FakeEngine, sample_pdf: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    real_convert = cli.api.convert

    def convert(
        path: str | Path, profile: str = "default", output_dir: str | Path | None = None
    ) -> api.Result:
        result = real_convert(path, profile=profile, output_dir=output_dir)
        result.report["verification"] = {"passed": False}
        return result

    monkeypatch.setattr(cli.api, "convert", convert)
    res = runner.invoke(cli.app, ["convert", str(sample_pdf), "-o", str(tmp_path / "o")])
    assert res.exit_code == 1
    assert "VERIFY-FAIL" in res.output


def test_output_collision(fake_engine: FakeEngine, tmp_path: Path) -> None:
    for d in ("x", "y"):
        (tmp_path / d).mkdir()
        (tmp_path / d / "same.pdf").write_bytes(b"x")
    res = runner.invoke(
        cli.app,
        [
            "convert",
            str(tmp_path / "x/same.pdf"),
            str(tmp_path / "y/same.pdf"),
            "-o",
            str(tmp_path),
        ],
    )
    assert res.exit_code == 2
    assert "output collision" in res.output


def test_missing_input(fake_engine: FakeEngine, tmp_path: Path) -> None:
    res = runner.invoke(cli.app, ["convert", str(tmp_path / "nope.pdf")])
    assert res.exit_code == 2
    assert "not found" in res.output


def test_profile_not_available_here(
    fake_engine: FakeEngine, sample_pdf: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(profiles, "current_platform", lambda: "linux-x86_64")
    res = runner.invoke(cli.app, ["convert", str(sample_pdf), "--profile", "vlm-granite-mlx"])
    assert res.exit_code == 2
    assert "needs platform darwin-arm64" in res.output
    assert fake_engine.calls == []


def test_models_download_selection(monkeypatch: pytest.MonkeyPatch) -> None:
    from docconv import models

    picked: list[list[str]] = []

    def fake_download(selected: list[profiles.Profile]) -> list[profiles.ModelSpec]:
        picked.append([p.name for p in selected])
        return [m for p in selected for m in p.models]

    monkeypatch.setattr(models, "download", fake_download)
    monkeypatch.setattr(profiles, "current_platform", lambda: "linux-x86_64")
    res = runner.invoke(cli.app, ["models", "download"])
    assert res.exit_code == 0, res.output
    assert set(picked[0]) == {
        "standard-rapidocr",
        "standard-tesseract",
        "standard-fullocr",
        "vlm-granite",
    }
    res = runner.invoke(cli.app, ["models", "download", "--profile", "vlm-glmocr"])
    assert res.exit_code == 0, res.output
    assert picked[1] == ["vlm-glmocr"]
    assert "zai-org/GLM-OCR@" in res.output
    res = runner.invoke(cli.app, ["models", "download", "--profile", "vlm-granite-mlx"])
    assert res.exit_code == 2
