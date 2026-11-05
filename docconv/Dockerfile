# docconv for Linux CPU. Models are downloaded at build time; at runtime the
# container works without network (`docker run --network none ...`).
FROM ghcr.io/astral-sh/uv:0.13.7 AS uv

FROM python:3.14.9-slim

# Tesseract for the standard-tesseract profile.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        tesseract-ocr tesseract-ocr-eng \
    && rm -rf /var/lib/apt/lists/*

COPY --from=uv /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH=/opt/venv/bin:$PATH \
    DOCCONV_ARTIFACTS_PATH=/opt/docconv-models

WORKDIR /app
# Dependencies first (cached layer), then the project itself. The uv cache is a
# BuildKit cache mount: reused across builds, never stored in the image.
COPY pyproject.toml uv.lock README.md ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-default-groups --extra vlm --no-install-project
COPY src ./src
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-default-groups --extra vlm --no-editable

# Models of the portable profiles (C1-C4, plus the optional C7, activated in the
# profile comparison); needs network at build time only.
RUN docconv models download && docconv models download --profile vlm-glmocr
ENV HF_HUB_OFFLINE=1

RUN useradd --create-home --uid 10001 docconv
USER docconv
WORKDIR /work
ENTRYPOINT ["docconv"]
