# docconv for Linux CPU. Models are downloaded at build time; at runtime the
# container works without network (`docker run --network none ...`).
#
# Base images are pinned by tag and digest: the digest guarantees the content even
# if the tag is moved, and Dependabot updates both together.
FROM ghcr.io/astral-sh/uv:0.13.7@sha256:96f40d3904aad8d0bd010539001d36c8e2188b981e1334471a90c4a1d93bb490 AS uv
FROM python:3.14.9-slim@sha256:35caba83af2fe6da9a5d922f9b0156f21d1246a48278c58a08bd253303ba42e8 AS python

# Builder: resolves the environment with uv, which does not reach the final image.
FROM python AS builder
COPY --from=uv /uv /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/opt/venv

WORKDIR /app
# Dependencies first (cached layer), then the project itself. The uv cache is a
# BuildKit cache mount: reused across builds, never stored in the image.
COPY pyproject.toml uv.lock README.md ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-default-groups --extra vlm --no-install-project
COPY src ./src
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-default-groups --extra vlm --no-editable

# Runtime: same base image, so the environment's interpreter path stays valid.
FROM python

# Tesseract for the standard-tesseract profile.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        tesseract-ocr tesseract-ocr-eng \
    && rm -rf /var/lib/apt/lists/*

ENV PATH=/opt/venv/bin:$PATH \
    DOCCONV_ARTIFACTS_PATH=/opt/docconv-models

COPY --from=builder /opt/venv /opt/venv

# Models of the portable profiles (C1-C4, plus the optional C7, activated in the
# profile comparison); needs network at build time only.
RUN docconv models download && docconv models download --profile vlm-glmocr
ENV HF_HUB_OFFLINE=1

RUN useradd --create-home --uid 10001 docconv
USER docconv
WORKDIR /work
ENTRYPOINT ["docconv"]
