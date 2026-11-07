# docconv

Local converter of documents to Markdown: PDFs with a text layer, scanned PDFs and
images (PNG, JPEG). It is built on [Docling](https://github.com/docling-project/docling),
runs every model locally and works without network at runtime.

Status: proof of concept. Phase 1 exports Docling's Markdown as is; per-page routing,
the output convention rules and self-verification come later.

## Constraints

- Self-hosted: no third-party APIs; all models run where the converter runs.
- Portable: must run on Linux (CPU or NVIDIA GPU) and macOS. Platform-specific
  accelerators (Apple Vision OCR, MLX) are optional backends, never required.
- Licensing: runtime dependencies and model weights must allow commercial use
  and hosted deployment.

## Installation

Requires [uv](https://docs.astral.sh/uv/) and Python 3.14 (uv installs it if missing).

```bash
uv sync                               # development environment
uv sync --extra vlm                   # + vision-language model profiles (Transformers; MLX on Apple Silicon)
uv sync --extra ocrmac                # + Apple Vision OCR (macOS only)
uv tool install --editable .          # `docconv` command on the PATH
```

The `standard-tesseract` profile also needs the `tesseract` binary with English data
(`brew install tesseract`, `apt-get install tesseract-ocr tesseract-ocr-eng`).

### Models

Models are downloaded once, at pinned revisions, into `$DOCCONV_ARTIFACTS_PATH`
(default `~/.cache/docconv/models`):

```bash
docconv models download                          # every non-optional profile available here
docconv models download --profile vlm-glmocr     # a specific (or optional) profile
```

At runtime docconv never downloads anything: Docling reads the models from that folder
and Hugging Face runs in offline mode. A missing model is an error that names the
command to run.

## Usage

```bash
docconv convert report.pdf scans/ -o out/            # files and folders (recursive)
docconv convert page.png --profile standard-fullocr
docconv convert docs/ --json                         # JSON list of reports on stdout
```

For each document it writes `<stem>.md`, `<stem>.assets/image-NNN.png` and
`<stem>.report.json` (profile, route per page, device, timings, peak memory, versions
of Docling and of every model). Folder inputs keep their sub-folder layout under the
output folder; files other than `.pdf`, `.png`, `.jpg` and `.jpeg` are skipped with a
warning.

Exit codes: `0` all converted and verified; `1` some verification failed; `2` usage
error or some conversion failed. Every document is processed even if one fails.

As a library:

```python
import docconv

result = docconv.convert("report.pdf")  # in memory, nothing written
result = docconv.convert("report.pdf", output_dir="out", profile="vlm-granite")
print(result.markdown, result.report)
```

## Profiles

Defined in `src/docconv/profiles.toml`, each with the pinned revision of every model.

| Profile | Pipeline | OCR / model | Platforms |
| --- | --- | --- | --- |
| `standard-rapidocr` (default) | layout + OCR + TableFormer | RapidOCR (ONNX Runtime) | any |
| `standard-tesseract` | same | Tesseract (system binary) | any |
| `standard-fullocr` | same | RapidOCR, full-page OCR | any |
| `vlm-granite` | vision-language model | granite-docling-258M (Transformers) | any |
| `vlm-granite-mlx` | vision-language model | granite-docling-258M (MLX) | macOS arm64 |
| `standard-ocrmac` | layout + OCR + TableFormer | Apple Vision | macOS arm64 |
| `vlm-glmocr` (optional) | vision-language model | GLM-OCR (Transformers) | any |

The device is chosen automatically (CUDA, MPS or CPU). Linux with an NVIDIA GPU is
supported by design but not tested.

## Development

```bash
make verify                    # everything the CI `checks` job runs: check-versions, lint, test
make lint                      # ruff format/check, ty, pymarkdown (the pre-commit hook)
make test                      # fast tests (no models), with coverage >= 80 %
uv run pytest -m slow --no-cov # tests that load models (run `docconv models download` first)
```

Pre-commit hooks are configured at the repository root (`pre-commit install` there).

### Tool versions

The Dockerfile is the reference for the `uv` and Python versions: Dependabot keeps it
up to date. Two other places repeat them by hand: `UV_VERSION` in
`.github/workflows/docconv.yml` and `.python-version`. CI runs `make check-versions`,
which fails and says what to change when they differ from the Dockerfile, when the
local `uv` is older than it, or when the pinned Python is not installed.

```bash
make check-versions   # report mismatches; changes nothing
make update-tooling   # brew upgrade uv (Homebrew) + install the pinned Python
```

When a Dependabot PR bumps the Dockerfile, update `UV_VERSION` and `.python-version`
in the same PR.

### Synthetic test documents

`tools/synthetic/` builds documents from one source of truth per document: the same
blocks produce the HTML (rendered to PDF by WeasyPrint) and the expected Markdown.
Variants: `text` (PDF with a text layer) and `scan` (rasterised at 200 dpi, with noise,
up to ±1.5° skew and JPEG compression) for all five templates, plus `png` for the
table. Output is deterministic for a given seed and is not versioned:

```bash
uv run --group synthetic python tools/synthetic/generate.py --seed 42
```

WeasyPrint needs Pango (`brew install pango` on macOS). If it cannot load the
Homebrew libraries, prefix the command with `DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib`.

### Markdown lint

`.pymarkdown.json` configures [PyMarkdown](https://pymarkdown.readthedocs.io/). JSON
has no comments, so the reason for each change is listed here:

- `md013` (line length) disabled: the output convention puts one paragraph per line.
- `md033` (inline HTML) allows only `u`: underline is rendered as `<u>…</u>`.
- `md036` (emphasis used as a heading) disabled: bold lines such as the key word of an
  exercise (`**ORDER**`) or a bold subtitle are bold text in the source, not headings.

## Docker (Linux CPU)

```bash
docker build -t docconv .
docker run --rm --network none -v "$PWD/in:/in:ro" -v "$PWD/out:/out" \
  docconv convert /in -o /out
```

The image bundles the models of the portable profiles (downloaded at build time) and
installs CPU-only PyTorch. It runs as a non-root user.

### System packages in the image

On top of `python:3.14.7-slim` (Debian), the image installs only:

| Package | License |
| --- | --- |
| `tesseract-ocr`, `tesseract-ocr-eng` (and `tesseract-ocr-osd`, pulled in) | Apache-2.0 |

They pull in 67 shared libraries. Most are permissive (MIT, BSD, Apache-2.0, ISC,
zlib, libpng), but some are copyleft: `libjbig0` (GPL-2+, through `libtiff6` and
Leptonica) and LGPL libraries such as GLib, Pango, FriBidi, GnuTLS, libthai and
libunistring. They are used unmodified, as Debian ships them. To list them with the
licenses declared in their Debian copyright files:

```bash
docker run --rm --entrypoint sh docconv -c \
  'for p in $(dpkg-query -W -f "\${Package}\n"); do
     echo "$p: $(grep -h "^License:" /usr/share/doc/$p/copyright 2>/dev/null | sort -u | tr "\n" " ")"
   done'
```
