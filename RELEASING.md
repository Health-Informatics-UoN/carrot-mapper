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
| any type with a `BREAKING CHANGE:` footer                          | major, `5.0.0` → `6.0.0` |
| `chore:`, `docs:`, `ci:`, `refactor:`, `test:`, `style:`, `build:` | no release               |

Tags have **no** `v` **prefix** (`5.0.0`, not `v5.0.0`).

### Breaking changes: read this before merging one

The `angular` preset we use does **not** understand the `feat!:` shorthand.
A `!` in the title gives you a _minor_ release. The only thing that triggers a
major release is a `BREAKING CHANGE:` footer **in the squash commit message**.

semantic-release reads the commit, not the PR. Unless the repo's squash-merge
default includes the PR description, the PR body never reaches git. So when you
merge a breaking PR:

1. Click **Squash and merge**.
2. In the commit description box, make sure this line is there, with a blank line above it:
   ```
    BREAKING CHANGE: <what breaks and what operators must do>
   ```
3. Confirm the merge, then check the new tag on the

   [Releases page](https://github.com/Health-Informatics-UoN/carrot-mapper/releases).

If it went wrong (you got a minor release instead), merge another PR with the
same `feat:` title and the footer added at merge time. Don't delete or move tags.

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
- A release must have run on **test for at least one working day** first, with
  the checks below done there. Security fixes can skip the soak period, but not the checks.

### Checklist

Before:

- [ ] The release is on test, and the smoke test below passes there.
- [ ] You've read the GitHub Release notes for **every** version between what's live in
  ```
  production and the one you're deploying. Pay particular attention to the **BREAKING CHANGES** sections.
  ```
- [ ] Any new or changed environment variables or secrets are already set on the
  ```
  production App Services (Azure) and the `production` GitHub environment.
  ```
- [ ] Any new infrastructure the release needs (e.g. Keycloak) already exists in production.
- [ ] Major release: you've backed up the production database and announced a maintenance window to users.

Deploy:

- [ ] Actions → **Deploy to Production (carrot.ac.uk)** → **Run workflow** → `image_tag` = `X.Y.Z`.
- [ ] A `production` environment reviewer approves the run.

After (smoke test):

- [ ] You can log in to carrot.ac.uk.
- [ ] Scan reports and projects load.
- [ ] Uploading a small scan report triggers the Airflow DAG, and it completes.
- [ ] The Airflow UI and API are reachable, and the scheduler is healthy.
- [ ] No new errors show up in Azure logs / Application Insights in the first 30 minutes.
- [ ] You've recorded the deployed version and date (e.g. in the release's GitHub notes or the team channel).

### Rolling back

Re-run **Deploy to Production** with the previous version's tag.

- This is only safe if the release you're rolling back from didn't run
  irreversible migrations. If in doubt, check `app/api/**/migrations/` in the
  diff between the two tags first.
- A rolled-back major release may also need its environment changes reverted.
- Then fix forward on `main`. Don't leave production pinned to an old version long term.

## 5. Hotfixes

We **fix forward**. There are no release branches.

1. Open a `fix: …` PR against `main` and get it reviewed (an expedited review is fine).
2. Merge it, which cuts a patch release and deploys it to test automatically.
3. Check the fix on test, then deploy that patch version to production.

Because `main` is always releasable, a hotfix ships with everything else merged
since the last production deploy. If `main` holds unreleased work that must not
go out yet, talk to the maintainers before merging the fix. That's the one case
where a temporary release branch may be justified.

## 6. Supported versions

Only the **latest release** is supported. Security and bug fixes are not
backported to older major or minor lines. Deployers running their own instance
should keep up with minor releases, and read the breaking-change notes before
taking a major release.

## 7. Routine maintenance

| What                                                                                                | When                                           | Who                    |
| --------------------------------------------------------------------------------------------------- | ---------------------------------------------- | ---------------------- |
| Review and merge Dependabot PRs. Python and Actions updates are grouped; review majors individually | monthly, the week they open                    | maintainers (rotating) |
| Deploy the latest release to production, if it has been soaking on test                             | at least monthly                               | maintainers            |
| Check that `main` is green and test is healthy                                                      | weekly                                         | maintainers            |
| Upgrade pinned base images (Python, Node, Airflow)                                                  | each minor release of the component, as needed | maintainers            |
| Review open security advisories and Dependabot alerts                                               | weekly                                         | maintainers            |

Dependabot PR titles use `fix(dependencies):` for runtime dependencies (which
produces a patch release) and `chore(dependencies):` for GitHub Actions (no
release). A Dependabot **major** bump that requires deployers to change
anything must get a `BREAKING CHANGE:` footer at merge time, like any other
breaking PR.

## Known limitations

- The `feat!:` shorthand won't work until the shared
  [`semantic-release.yml`](https://github.com/Health-Informatics-UoN/workflows/blob/main/.github/workflows/semantic-release.yml)
  workflow installs `conventional-changelog-conventionalcommits`, and this repo
  switches to `preset: "conventionalcommits"`.
