# pocs

Monorepo of proofs of concept.

Each POC lives in its own top-level folder and is an independent `uv` project
(no uv workspace): it has its own `pyproject.toml`, `uv.lock` and virtual
environment. CI workflows are filtered by folder.

The configuration of the repository (GitHub settings, CI, security, tooling) and
how to replicate it: [`docs/README.md`](docs/README.md).

## POCs

- [`docconv`](docconv/): local converter of documents (PDF, scanned PDF, images) to Markdown, with self-verification.

## Commit messages

Pull requests are squash-merged, so each PR title becomes one commit on `main`.
Titles follow `<area>: <summary>`, checked by the `pr-title` workflow:

- `<area>`: the POC folder (`docconv`), or `ci`, `pre-commit` or `repo` for
  repository-wide changes.
- `<summary>`: short and imperative (`docconv: pin Python 3.14.9`).

## Adding a POC

1. Create the folder as an independent `uv` project and its workflow
   `.github/workflows/<poc>.yml`, copying the `changes` job and the gate job
   from `docconv.yml` (gate `name: <poc>`).
2. Run `gh actions-lock` to add the new workflow to `.github/workflows/actions.lock`:
   the **Require lockfile** policy blocks any workflow missing from it.
3. Add the `<poc>` check to the `protect-main` ruleset's required status checks.
4. Add a local `<poc>-lint` hook to `.pre-commit-config.yaml` (and its id to `SKIP`
   in `.github/workflows/repo.yml`) and the POC's ecosystems to `.github/dependabot.yml`,
   with `<poc>` as their commit-message prefix.
