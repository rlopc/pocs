"""Command-line interface.

Exit codes of ``docconv convert``: 0 = all documents converted and verified;
1 = some verification failed; 2 = usage error or some conversion failed.
All documents are processed even when one fails.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Any

import typer

from docconv import api
from docconv.profiles import ProfileError, load_catalog

EXIT_OK = 0
EXIT_VERIFICATION = 1
EXIT_ERROR = 2

app = typer.Typer(
    help="Convert documents (PDF, scanned PDF, images) to Markdown, locally.",
    no_args_is_help=True,
    pretty_exceptions_enable=False,
)
models_app = typer.Typer(help="Manage model artifacts.", no_args_is_help=True)
app.add_typer(models_app, name="models")


@dataclass(frozen=True)
class Job:
    source: Path
    out_dir: Path


def collect_jobs(inputs: list[Path], output: Path) -> tuple[list[Job], list[str]]:
    """Expand files and folders into jobs; return (jobs, warnings).

    Folders are walked recursively and their sub-folder layout is mirrored under
    ``output``; files given directly go to ``output`` itself.
    """
    jobs: list[Job] = []
    warnings: list[str] = []
    for item in inputs:
        if item.is_dir():
            for path in sorted(p for p in item.rglob("*") if p.is_file()):
                if path.suffix.lower() in api.SUPPORTED_SUFFIXES:
                    jobs.append(Job(path, output / path.parent.relative_to(item)))
                elif not path.name.startswith("."):
                    warnings.append(f"skipped unsupported file: {path}")
        else:
            jobs.append(Job(item, output))
    return jobs, warnings


def _run_job(job: Job, profile: str, seen: set[Path]) -> tuple[dict[str, Any], int]:
    target = (job.out_dir / f"{job.source.stem}.md").resolve()
    if target in seen:
        return {"source": str(job.source), "error": f"output collision: {target}"}, EXIT_ERROR
    seen.add(target)
    try:
        result = api.convert(job.source, profile=profile, output_dir=job.out_dir)
    except Exception as exc:  # noqa: BLE001 - report every failure and keep going
        return {"source": str(job.source), "error": f"{type(exc).__name__}: {exc}"}, EXIT_ERROR
    report = dict(result.report)
    report["markdown_path"] = str(result.markdown_path)
    verification = report.get("verification")
    failed = isinstance(verification, dict) and not verification.get("passed", True)
    return report, EXIT_VERIFICATION if failed else EXIT_OK


@app.command()
def convert(
    inputs: Annotated[list[Path], typer.Argument(help="Files or folders to convert.")],
    output: Annotated[Path, typer.Option("--output", "-o", help="Output folder.")] = Path(
        "docconv-out"
    ),
    profile: Annotated[
        str, typer.Option("--profile", "-p", help="Profile name (see profiles.toml).")
    ] = "default",
    as_json: Annotated[
        bool, typer.Option("--json", help="Print a JSON list of reports instead of a summary.")
    ] = False,
) -> None:
    """Convert documents to Markdown.

    Writes <stem>.md, <stem>.assets/ and <stem>.report.json per document.
    Models are read from $DOCCONV_ARTIFACTS_PATH (default ~/.cache/docconv/models);
    run `docconv models download` first.
    """
    try:
        load_catalog().get_usable(profile)
    except ProfileError as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(EXIT_ERROR) from None
    missing = [p for p in inputs if not p.exists()]
    if missing:
        typer.echo(f"error: not found: {', '.join(map(str, missing))}", err=True)
        raise typer.Exit(EXIT_ERROR)

    jobs, warnings = collect_jobs(inputs, output)
    for warning in warnings:
        typer.echo(f"warning: {warning}", err=True)

    reports: list[dict[str, Any]] = []
    codes: list[int] = []
    seen: set[Path] = set()
    for job in jobs:
        report, code = _run_job(job, profile, seen)
        reports.append(report)
        codes.append(code)
        if not as_json:
            if "error" in report:
                typer.echo(f"FAIL {job.source}: {report['error']}", err=True)
            else:
                status = "OK  " if code == EXIT_OK else "VERIFY-FAIL"
                typer.echo(
                    f"{status} {job.source} -> {report['markdown_path']} "
                    f"({len(report['pages'])} p, {report['images']} img, "
                    f"{report['timings']['convert_s']} s)"
                )
    if as_json:
        typer.echo(json.dumps(reports, indent=2, ensure_ascii=False))
    raise typer.Exit(max(codes, default=EXIT_OK))


@models_app.command("download")
def models_download(
    profile: Annotated[
        list[str] | None,
        typer.Option(
            "--profile",
            "-p",
            help="Profile(s) whose models to download. Default: every non-optional "
            "profile available on this platform.",
        ),
    ] = None,
) -> None:
    """Download model artifacts at their pinned revisions (needs network)."""
    from docconv import models

    catalog = load_catalog()
    try:
        if profile is not None and len(profile) > 0:
            selected = [catalog.get_usable(name) for name in profile]
        else:
            selected = [
                p for p in catalog.profiles.values() if p.available_here() and not p.optional
            ]
    except ProfileError as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(EXIT_ERROR) from None
    specs = models.download(selected)
    for spec in specs:
        typer.echo(f"{spec.key}: {spec.repo}@{spec.revision}")
    typer.echo(f"models in {models.artifacts_path()}")
