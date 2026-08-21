# Contributing

See the [contribution guide](https://carrot.ac.uk/contributing) for details.

This page covers everything specific to contributing code to Carrot Mapper.

## Ways to contribute

- **Bugs & feature requests** — open an [issue](https://github.com/Health-Informatics-UoN/carrot-mapper/issues). Please check existing issues first to avoid duplicates.
- **New to the project?** Look for issues labelled [`good first issue`](https://github.com/Health-Informatics-UoN/carrot-mapper/labels/good%20first%20issue) or [`help wanted`](https://github.com/Health-Informatics-UoN/hutch-bunny/labels/help%20wanted).
- **Bigger changes** please open an issue to discuss the approach before you start. It saves you from spending time on something that turns out not to fit. Check the [roadmap](https://github.com/orgs/Health-Informatics-UoN/projects/1/views/15) for planned work first.
- **Security vulnerabilities** — do not open a public issue. Follow the process in [`SECURITY.md`](SECURITY.md) instead.

## Development setup

See the [developer setup guide](https://carrot.ac.uk/mapper/dev_guide/quickstart) for full details. In short:

`docker compose up` only runs the supporting services (Postgres, minio/azurite, omop-lite, Airflow) — the API and frontend are run from source so you get fast reload and a normal debugger.

Airflow's own migration needs a Postgres `airflow` schema to already exist, which is created by the API (`airflow_schema_creation` management command), not by Airflow itself. So **the first time** you bring the stack up (or any time after wiping the `db` volume), start the API's one-time setup *between* two docker compose stages rather than bringing everything up at once:

1. Start Postgres and let the OMOP vocab loader finish (it's a one-shot container — wait for it to exit before continuing):
   ```bash
   cp .env.example .env
   docker compose up -d db omop-lite
   docker wait $(docker compose ps -q omop-lite)
   ```
2. Bootstrap and run the API from source (in a second terminal, from `app/api`):
   ```bash
   uv sync
   uv run manage.py airflow_schema_creation
   uv run manage.py migrate
   uv run manage.py automatic_seeding_data
   uv run manage.py default_super_user
   uv run manage.py automatic_queue_and_containers_creation
   uv run manage.py runserver
   ```
   `python-dotenv` walks up from `app/api` looking for a `.env`, so the root `.env` created above covers the API too — no separate `app/api/.env` is needed.
3. Now that the `airflow` schema exists, bring up the rest of the stack (in a third terminal):
   ```bash
   docker compose up -d
   ```
4. Run the frontend from source (in a fourth terminal, from `app/next-client-app`):
   ```bash
   cp .env.example .env
   npm install
   npm run dev
   ```

On later days, once the schema and migrations already exist in the `db` volume, this ordering doesn't matter any more — a plain `docker compose up -d` for the whole stack, then `uv run manage.py runserver` and `npm run dev`, is fine.

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
