"""Compare conversion profiles on the test cases.

Usage (from the docconv folder):
    uv run --all-extras --group benchmark python benchmark/run.py --env mac
    uv run --group benchmark python benchmark/run.py --env linux        # in Docker
    uv run --group benchmark python benchmark/run.py --env mac --reserved

Each run of a profile is a new process (`docconv convert ... --json`, natively or in
`docker run --network none`) that converts every case in a fixed order: real cases
then synthetic ones, alphabetically by stem. Metrics are computed here, on the host.
- Cold: seconds from process start until the first document is done.
- Warm: wall seconds per page of each following document; median over all runs.
- Memory: peak resident memory reported by the process.
Quality is measured on the first run. If the first run goes over three times a veto
limit, the process is stopped and the profile is marked as vetoed.
Writes data/outputs/<env>/benchmark.json (raw) and data/outputs/<env>/results.md.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import statistics
import subprocess
import sys
import time
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pypdfium2 as pdfium
from metrics import compare

PROJECT = Path(__file__).resolve().parents[1]
DATA = PROJECT / "data"
CONFIG = tomllib.loads((Path(__file__).parent / "cases.toml").read_text(encoding="utf-8"))
SUFFIXES = (".pdf", ".png", ".jpg", ".jpeg")
TYPES = ("text", "scan", "image")
PROFILES = {
    "mac": [
        "standard-rapidocr",
        "standard-tesseract",
        "standard-fullocr",
        "vlm-granite",
        "vlm-granite-mlx",
        "standard-ocrmac",
    ],
    "linux": ["standard-rapidocr", "standard-tesseract", "standard-fullocr", "vlm-granite"],
}
POLL_S = 1.0


@dataclass(frozen=True)
class Case:
    stem: str
    source: Path
    expected: Path
    group: str  # real | synthetic | reserved
    type: str
    pages: int


def _pages(path: Path) -> int:
    if path.suffix.lower() != ".pdf":
        return 1
    pdf = pdfium.PdfDocument(path)
    try:
        return len(pdf)
    finally:
        pdf.close()


def _source(folder: Path, stem: str) -> Path:
    for suffix in SUFFIXES:
        if (folder / f"{stem}{suffix}").is_file():
            return folder / f"{stem}{suffix}"
    raise FileNotFoundError(f"no input for {stem} in {folder}")


def discover(reserved: bool) -> list[Case]:
    """Cases in the fixed order: real (or reserved), then synthetic; alphabetical."""
    cases: list[Case] = []
    group = "reserved" if reserved else "real"
    for md in sorted((DATA / "expected" / group).glob("*.md")):
        src = _source(DATA / "inputs" / "real", md.stem)
        cases.append(Case(md.stem, src, md, group, CONFIG["types"][group][md.stem], _pages(src)))
    if reserved:
        return cases
    for src in sorted((DATA / "inputs" / "synthetic").glob("syn-*")):
        template, variant = src.stem.rsplit("-", 1)
        expected = DATA / "expected" / "synthetic" / f"{template}.md"
        kind = CONFIG["types"]["synthetic"][variant]
        cases.append(Case(src.stem, src, expected, "synthetic", kind, _pages(src)))
    return cases


def _command(env: str, profile: str, cases: list[Case], out: Path, image: str) -> list[str]:
    if env == "mac":
        exe = Path(sys.executable).with_name("docconv")
        files = [str(c.source) for c in cases]
        return [str(exe), "convert", *files, "-o", str(out), "--profile", profile, "--json"]

    def inside(p: Path) -> str:
        return "/data/" + p.relative_to(DATA).as_posix()

    return [
        "docker",
        "run",
        "--rm",
        "--network",
        "none",
        "--user",
        f"{os.getuid()}:{os.getgid()}",
        "-e",
        "HOME=/tmp",
        "-v",
        f"{DATA}:/data",
        image,
        "convert",
        *[inside(c.source) for c in cases],
        "-o",
        inside(out),
        "--profile",
        profile,
        "--json",
    ]


def run_once(
    env: str, profile: str, cases: list[Case], out: Path, image: str, early_cut: bool
) -> dict[str, Any]:
    """One process over all cases. Returns per-document reports and a veto reason, if any."""
    out.mkdir(parents=True, exist_ok=True)
    veto = CONFIG["veto"][env]
    log = out / "run.log"
    start = time.time()
    with log.open("w") as stderr, (out / "stdout.json").open("w") as stdout:
        proc = subprocess.Popen(
            _command(env, profile, cases, out, image), stdout=stdout, stderr=stderr
        )
        reports: dict[str, dict[str, Any]] = {}
        last_done, cut = start, None
        while proc.poll() is None:
            time.sleep(POLL_S)
            for case in cases:
                path = out / f"{case.stem}.report.json"
                if case.stem not in reports and path.is_file() and path.stat().st_mtime >= start:
                    try:
                        reports[case.stem] = json.loads(path.read_text(encoding="utf-8"))
                    except json.JSONDecodeError:
                        continue  # still being written
                    last_done = time.time()
            if not early_cut:
                continue
            elapsed_first = time.time() - start
            pending = [c for c in cases if c.stem not in reports]
            if not reports and elapsed_first > 3 * veto["cold_max"]:
                cut = f"cold > {3 * veto['cold_max']} s (3x veto) at {elapsed_first:.0f} s"
            elif reports and pending:
                waited = time.time() - last_done
                if waited > 3 * veto["warm_max"] * pending[0].pages:
                    cut = (
                        f"warm > {3 * veto['warm_max']} s/page (3x veto) on {pending[0].stem}: "
                        f"{waited:.0f} s for {pending[0].pages} page(s)"
                    )
            if cut is not None:
                proc.kill()
                proc.wait()
                break
    return {
        "reports": reports,
        "cut": cut,
        "returncode": proc.returncode,
        "wall_s": time.time() - start,
    }


def timings(run: dict[str, Any], cases: list[Case]) -> dict[str, Any]:
    """Cold seconds and warm seconds per page (per document) from one run."""
    done = [c for c in cases if c.stem in run["reports"]]
    since = [run["reports"][c.stem]["timings"]["since_process_start_s"] for c in done]
    warm = {}
    for i in range(1, len(done)):
        warm[done[i].stem] = (since[i] - since[i - 1]) / done[i].pages
    mem = max((run["reports"][c.stem]["max_rss_mib"] for c in done), default=None)
    return {"cold_s": since[0] if since else None, "warm_s_per_page": warm, "max_rss_mib": mem}


def quality(run: dict[str, Any], cases: list[Case], out: Path) -> dict[str, Any]:
    result = {}
    for case in cases:
        md = out / f"{case.stem}.md"
        if case.stem not in run["reports"] or not md.is_file():
            continue
        expected = case.expected.read_text(encoding="utf-8")
        result[case.stem] = compare(expected, md.read_text(encoding="utf-8"))
    return result


def benchmark_profile(
    env: str, profile: str, cases: list[Case], out_root: Path, image: str, repeats: int
) -> dict[str, Any]:
    out = out_root / profile
    runs, scores = [], {}
    for n in range(repeats):
        print(f"[{env}] {profile}: run {n + 1}/{repeats}", flush=True)
        run = run_once(env, profile, cases, out, image, early_cut=n == 0)
        if n == 0:
            scores = quality(run, cases, out)
        first = next(iter(run["reports"].values()), {})
        runs.append(
            timings(run, cases)
            | {
                "cut": run["cut"],
                "returncode": run["returncode"],
                "device": first.get("device"),
                "versions": first.get("versions"),
                "failed": [c.stem for c in cases if c.stem not in run["reports"]],
            }
        )
        if run["cut"]:
            print(f"  vetoed: {run['cut']}", flush=True)
            break
    return {"profile": profile, "runs": runs, "quality": scores}


# --- Aggregation and report ------------------------------------------------------------

METRICS = [
    ("wer_norm", "WER n", "pct"),
    ("wer_strict", "WER s", "pct"),
    ("cer", "CER", "pct"),
    ("invented", "Inv", "num"),
    ("omitted", "Omit", "num"),
    ("heading_f1", "Head F1", "f2"),
    ("heading_level_ok", "Head lvl", "pct0"),
    ("lists_ok", "Lists", "pct0"),
    ("table_shape_ok", "Tbl shape", "pct0"),
    ("table_cells_ok", "Cells", "pct0"),
    ("bold_f1", "Bold F1", "f2"),
    ("underline_f1", "Under F1", "f2"),
]


def _mean(values: list[float | None]) -> float | None:
    present = [v for v in values if v is not None]
    return sum(present) / len(present) if present else None


def aggregate(
    result: dict[str, Any], cases: list[Case], group: str, kind: str, env: str
) -> dict[str, Any] | None:
    docs = [c for c in cases if c.group == group and c.type == kind]
    if not docs:
        return None
    scored = [result["quality"][c.stem] for c in docs if c.stem in result["quality"]]
    row: dict[str, Any] = {key: _mean([s[key] for s in scored]) for key, _, _ in METRICS}
    row["images"] = (
        sum(s["images_output"] for s in scored),
        sum(s["images_expected"] for s in scored),
    )
    row["docs"] = (len(scored), len(docs))
    runs = result["runs"]
    warm = [
        r["warm_s_per_page"][c.stem] for r in runs for c in docs if c.stem in r["warm_s_per_page"]
    ]
    row["warm"] = statistics.median(warm) if warm else None
    colds = [r["cold_s"] for r in runs if r["cold_s"] is not None]
    row["cold"] = statistics.median(colds) if colds else None
    row["mem"] = max((r["max_rss_mib"] for r in runs if r["max_rss_mib"]), default=None)
    row["cut"] = next((r["cut"] for r in runs if r["cut"]), None)
    th = CONFIG["thresholds"][kind]
    fails = []
    if row["docs"][0] < row["docs"][1]:
        fails.append("missing outputs")
    if row["wer_norm"] is None or row["wer_norm"] > th["wer_norm_max"]:
        fails.append("WER")
    if "invented_max" in th and (row["invented"] is None or row["invented"] > th["invented_max"]):
        fails.append("invented")
    if row["heading_f1"] is not None and row["heading_f1"] < th["heading_f1_min"]:
        fails.append("headings")
    shape = row["table_shape_ok"]
    if "table_shape_min" in th and shape is not None and shape < th["table_shape_min"]:
        fails.append("table shape")
    veto = CONFIG["veto"][env]
    vetoes = []
    if row["cut"] is not None:
        vetoes.append("early cut")
    if row["warm"] is not None and row["warm"] > veto["warm_max"]:
        vetoes.append("warm")
    if row["cold"] is not None and row["cold"] > veto["cold_max"]:
        vetoes.append("cold")
    row["fails"], row["vetoes"] = fails, vetoes
    return row


def _fmt(value: float | None, style: str) -> str:
    if value is None:
        return "N/A"
    if style == "pct":
        return f"{100 * value:.1f} %"
    if style == "pct0":
        return f"{100 * value:.0f} %"
    if style == "f2":
        return f"{value:.2f}"
    return f"{value:.1f}" if isinstance(value, float) else str(value)


def report(results: list[dict[str, Any]], cases: list[Case], env: str, meta: dict[str, Any]) -> str:
    lines = [
        f"# Benchmark results ({env})",
        "",
        "Generated by `benchmark/run.py`; output of render.py without post-processing.",
        "",
        "Environment: " + ", ".join(f"{k}: {v}" for k, v in meta.items()),
    ]
    groups = ["reserved"] if any(c.group == "reserved" for c in cases) else ["real", "synthetic"]
    for group in groups:
        for kind in TYPES:
            rows = [(r["profile"], aggregate(r, cases, group, kind, env)) for r in results]
            rows = [(p, row) for p, row in rows if row is not None]
            if not rows:
                continue
            header = [
                "Profile",
                *(h for _, h, _ in METRICS),
                "Images",
                "Cold s",
                "Warm s/p",
                "Mem MiB",
                "Thresholds",
                "Veto",
            ]
            lines += ["", f"## {group.capitalize()} — {kind}", ""]
            lines.append("| " + " | ".join(header) + " |")
            lines.append("| " + " | ".join("---" for _ in header) + " |")
            for profile, row in rows:
                cells = [
                    profile
                    + (
                        ""
                        if row["docs"][0] == row["docs"][1]
                        else f" ({row['docs'][0]}/{row['docs'][1]} docs)"
                    )
                ]
                cells += [_fmt(row[key], style) for key, _, style in METRICS]
                cells += [
                    f"{row['images'][0]}/{row['images'][1]}",
                    _fmt(row["cold"], "num"),
                    _fmt(row["warm"], "num"),
                    _fmt(row["mem"], "num"),
                ]
                cells.append("pass" if not row["fails"] else "fail: " + ", ".join(row["fails"]))
                cells.append("ok" if not row["vetoes"] else "vetoed: " + ", ".join(row["vetoes"]))
                lines.append("| " + " | ".join(cells) + " |")
            if group != "synthetic":
                lines += ["", _decision(rows)]
    cuts = [f"- {r['profile']}: {run['cut']}" for r in results for run in r["runs"] if run["cut"]]
    if cuts:
        lines += ["", "Early cuts:", "", *cuts]
    return "\n".join(lines) + "\n"


def _decision(rows: list[tuple[str, dict[str, Any]]]) -> str:
    passing = [(p, r) for p, r in rows if not r["fails"] and not r["vetoes"]]
    if passing:
        best = min(passing, key=lambda pr: pr[1]["warm"] if pr[1]["warm"] is not None else 1e9)
        return f"Decision: **{best[0]}** passes and is the fastest warm."
    ranked = [(p, r) for p, r in rows if r["wer_norm"] is not None]
    if not ranked:
        return "Decision: no profile produced output."
    p, r = min(ranked, key=lambda pr: pr[1]["wer_norm"])
    reasons = ", ".join(r["fails"] + r["vetoes"]) or "none"
    return f"Decision: no profile passes (indicative). Lowest WER: **{p}**; fails: {reasons}."


def _meta(env: str) -> dict[str, Any]:
    meta: dict[str, Any] = {"date": time.strftime("%Y-%m-%d"), "host": platform.platform()}
    if env == "mac":
        brand = subprocess.run(
            ["sysctl", "-n", "machdep.cpu.brand_string"], capture_output=True, text=True
        )
        meta["cpu"] = brand.stdout.strip()
        mem = subprocess.run(["sysctl", "-n", "hw.memsize"], capture_output=True, text=True)
        meta["ram_gib"] = round(int(mem.stdout.strip() or 0) / 2**30)
    else:
        fmt = "{{.NCPU}} {{.MemTotal}} {{.Architecture}}"
        info = subprocess.run(["docker", "info", "--format", fmt], capture_output=True, text=True)
        cpus, mem, arch = [*info.stdout.split(), "?", "0", "?"][:3]
        meta |= {"docker_cpus": cpus, "docker_mem_gib": round(int(mem) / 2**30, 1), "arch": arch}
    return meta


def main() -> None:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--env", choices=["mac", "linux"], required=True)
    parser.add_argument("--profiles", help="comma-separated profile names (default: all for env)")
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--reserved", action="store_true", help="use the reserved set (phase 5)")
    parser.add_argument("--image", default="docconv:latest", help="Docker image for --env linux")
    parser.add_argument(
        "--report-only",
        action="store_true",
        help="do not convert: recompute quality from the saved outputs and rewrite the report",
    )
    args = parser.parse_args()
    if args.reserved:
        profiles = (args.profiles or "default").split(",")
    else:
        profiles = args.profiles.split(",") if args.profiles else PROFILES[args.env]
    cases = discover(args.reserved)
    out_root = DATA / "outputs" / (f"{args.env}-reserved" if args.reserved else args.env)
    if args.report_only:
        saved = json.loads((out_root / "benchmark.json").read_text(encoding="utf-8"))
        results, meta = saved["results"], saved["meta"]
        for result in results:
            done = {
                "reports": {c.stem: {} for c in cases if c.stem not in result["runs"][0]["failed"]}
            }
            result["quality"] = quality(done, cases, out_root / result["profile"])
    else:
        fresh = [
            benchmark_profile(args.env, p, cases, out_root, args.image, args.repeats)
            for p in profiles
        ]
        # Merge with earlier runs of other profiles (e.g. C7 measured later).
        saved_path = out_root / "benchmark.json"
        saved = json.loads(saved_path.read_text(encoding="utf-8")) if saved_path.is_file() else {}
        kept = [r for r in saved.get("results", []) if r["profile"] not in profiles]
        results = kept + fresh
        meta = _meta(args.env)
    raw = {"meta": meta, "cases": [c.stem for c in cases], "results": results}
    (out_root / "benchmark.json").write_text(json.dumps(raw, indent=2) + "\n", encoding="utf-8")
    (out_root / "results.md").write_text(report(results, cases, args.env, meta), encoding="utf-8")
    print(f"written {out_root / 'results.md'}")


if __name__ == "__main__":
    main()
