# Contributing

See the [contribution guide](https://carrot.ac.uk/contributing) for details.

This page covers everything specific to contributing code to Carrot Mapper.

## Ways to contribute

- **Bugs & feature requests** — open an [issue](https://github.com/Health-Informatics-UoN/carrot-mapper/issues). Please check existing issues first to avoid duplicates.
- **New to the project?** Look for issues labelled [`good first issue`](https://github.com/Health-Informatics-UoN/carrot-mapper/labels/good%20first%20issue) or [`help wanted`](https://github.com/Health-Informatics-UoN/hutch-bunny/labels/help%20wanted).
- **Bigger changes** please open an issue to discuss the approach before you start. It saves you from spending time on something that turns out not to fit. Check the [roadmap](https://github.com/orgs/Health-Informatics-UoN/projects/1/views/15) for planned work first.
- **Security vulnerabilities** — do not open a public issue. Follow the process in [`SECURITY.md`](SECURITY.md) instead.

## Development setup

See the [developer setup guide](https://carrot.ac.uk/mapper/dev_guide/quickstart).

## Pre-commit hooks

This repo uses [pre-commit](https://pre-commit.com/) to run Ruff (lint + format) before each commit. Install the hooks once per clone:

```bash
uv run pre-commit install
```

## Code style & type checking

- **Ruff** lints and formats the codebase (config in `pyproject.toml`); this is enforced by pre-commit and CI ([`check.quality.yml`](.github/workflows/check.quality.yml)).
- All container images (API, frontend, Airflow webserver/scheduler) must build successfully — enforced by CI ([`check.container-build.yml`](.github/workflows/check.container-build.yml)).
- **mypy** runs in strict mode — all new code must be fully typed, with no implicit `Any`. This isn't currently wired into pre-commit or CI, so please run it yourself before opening a PR:
  ```bash
  uv run mypy src/
  ```
- Docstrings follow the Google style convention (enforced via Ruff's pydocstyle rules).

## Pull requests

- Open your PR against `main`. Keep PRs focused — small, single-purpose PRs are easier to review and land faster than large ones.
- PR titles must follow [Conventional Commits](https://www.conventionalcommits.org/) (e.g. `feat: ...`, `fix: ...`, `docs: ...`) — this is enforced by CI (see [`check-pr-title.yml`](.github/workflows/check-pr-title.yml)) and drives the release process below. We squash-merge, so the PR title becomes the commit on `main` — individual commits within your branch don't need to follow the convention.
- Link the issue your PR addresses, where there is one.
- Before requesting review, check that `ruff check`, `ruff format --check` all pass locally — CI will run equivalent checks, but catching issues locally is faster for everyone.
- Draft PRs are welcome if you'd like early feedback on direction before the change is finished.

## Releases

Releases are automated with `semantic-release` based on Conventional Commit PR titles merged to `main`: a `fix:` triggers a patch release, `feat:` a minor release, and a breaking change (`!` or a `BREAKING CHANGE:` footer) a major release. This also determines the container image tags published to `ghcr.io/carrot/`.

