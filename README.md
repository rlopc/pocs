# pocs

Monorepo of proofs of concept.

Each POC lives in its own top-level folder and is an independent `uv` project
(no uv workspace): it has its own `pyproject.toml`, `uv.lock` and virtual
environment. CI workflows are filtered by folder.

## POCs

- [`docconv`](docconv/): local converter of documents (PDF, scanned PDF, images) to Markdown, with self-verification.
