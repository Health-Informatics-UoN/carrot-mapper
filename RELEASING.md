# Releasing and maintaining Carrot Mapper

This is the maintainer guide for how a change gets from a merged PR to
production, and how released versions are looked after. For how to write and
open a PR, see [CONTRIBUTING.md](CONTRIBUTING.md).

## Overview

```
PR merged to main ──► Release workflow ──► Deploy to Dev and Test ──► (soak on test) ──► Deploy to Production
   (squash)          version + images         automatic                  manual             manual + approval
```

| Environment               | How it is deployed                                                                                | Image tag                | Who                                                                  |
| ------------------------- | ------------------------------------------------------------------------------------------------- | ------------------------ | -------------------------------------------------------------------- |
| dev                       | Automatically on every merge to `main`, or manually from a branch via **Build and Deploy to Dev** | commit SHA / branch name | anyone with write access                                             |
| test                      | Automatically after dev succeeds (with manual approval)                                           | commit SHA               | anyone with write access                                             |
| production (carrot.ac.uk) | Manually via **Deploy to Production**                                                             | semver, e.g. `5.0.0`     | a maintainer, with approval from a `production` environment reviewer |

## 1. Versioning

We use [Semantic Versioning](https://semver.org/). Version numbers are
**never set by hand**. `semantic-release` works out the next version from the
commit messages on `main` since the last tag ([`release.config.js`](release.config.js)).

| Squash commit on `main`                                            | Release                  |
| ------------------------------------------------------------------ | ------------------------ |
| `fix: …`, `perf: …`                                                | patch, `5.0.0` → `5.0.1` |
| `feat: …`                                                          | minor, `5.0.0` → `5.1.0` |
| any type with `!`, e.g. `feat!: …`, or a `BREAKING CHANGE:` footer | major, `5.0.0` → `6.0.0` |
| `chore:`, `docs:`, `ci:`, `refactor:`, `test:`, `style:`, `build:` | no release               |

Tags have **no** `v` **prefix** (`5.0.0`, not `v5.0.0`).

### Breaking changes: read this before merging one

semantic-release reads the **commit message on `main`**, not the PR. We
squash-merge using **only the PR title** as the commit message, so the PR
description never reaches git. Writing `BREAKING CHANGE:` in the PR
description does **nothing**.

There are two ways to mark a breaking change. Both give a major release:

**Option A: conventional style (recommended).** Add `!` after the type in the PR title:

```
feat!: update Airflow to 3.3.2 and use Keycloak for Airflow auth
```

Nothing extra is needed at merge time. CI accepts `!` in PR titles.

**Option B: angular style.** Keep a normal PR title (`feat: …`). Then, when you
click **Squash and merge**, add the footer to the **extended description** box
in the merge dialog:

```
BREAKING CHANGE: <what breaks and what operators must do>
```

This is easy to forget, because the box is empty by default. Only the person
merging can do it, so say in the PR that it's breaking.

You can use both at once: a `!` title, plus a `BREAKING CHANGE:` footer in the
extended description. The footer text is then shown in the release notes'
**BREAKING CHANGES** section, which is useful for telling operators what to do.

After merging, check that the new major tag appears on the
[Releases page](https://github.com/Health-Informatics-UoN/carrot-mapper/releases).
If you got a minor release instead, merge another empty PR with a `feat!:` title.
Don't delete or move tags.

A change counts as **breaking** if anyone deploying Carrot has to do something
beyond pulling the new images. For example:

- new required environment variables, or renamed or removed ones
- new required services (e.g. Keycloak), or a changed service topology
- database migrations that can't be rolled back, or that need manual steps
- removed or incompatible API endpoints
- a major-version upgrade of a component operators run (Airflow, Postgres, …)

## 2. What a release produces

Each push to `main` runs [`release.yml`](.github/workflows/release.yml):

1. **semantic-release** creates the git tag and a GitHub Release with generated notes (only if a releasable commit landed).
2. Four images are built and pushed to `ghcr.io/health-informatics-uon/carrot/`:

   `backend`, `frontend`, `airflow-api`, `airflow-scheduler`. They are tagged `edge` and with the commit SHA.

3. When a release was cut, the images are also tagged `X.Y.Z`, `X.Y` and `X`.

All four images always share one version number. Deploy them together, and
never mix versions across services.

## 3. Deploying to dev and test

This is automatic: [`deploy.test.yml`](.github/workflows/deploy.test.yml) runs
after every successful **Release** workflow and deploys the commit-SHA images
to dev, then test.

To redeploy or roll back test by hand, go to Actions → **Deploy to Dev and Test** → **Run workflow**
and give it an `image_tag` (`5.0.0`, a commit SHA, or `edge`).

To try a feature branch before merging, go to Actions → **Build and Deploy to Dev** → run it
on your branch. That only touches dev. The next merge to `main` will overwrite it.

## 4. Deploying to production

Production is only ever deployed with a **semver tag** of a published release.
Don't deploy `edge` or a SHA.

### When to deploy

- Deploy on demand when a release is worth shipping. There is no fixed schedule.

## 5. Dependabot PRs

Dependabot PR titles use `fix(dependencies):` for runtime dependencies (which
produces a patch release) and `chore(dependencies):` for GitHub Actions (no
release). A Dependabot **major** bump that requires deployers to change
anything must be marked as breaking like any other breaking PR: edit the PR
title to add `!` (e.g. `fix(dependencies)!: …`), or add a `BREAKING CHANGE:`
footer in the extended description at merge time.
