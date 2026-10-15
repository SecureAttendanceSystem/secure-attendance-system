# Contributing

Follow [README.md](README.md) to set up the project. Use `sprint` for integration
and `main` for stable milestones. Submit changes through pull requests.

## Branch and pull request

Start with a clean working tree and an updated `sprint`:

```bash
git switch sprint
git pull --ff-only
git switch -c feature/short-description
```

Use the branch name suggested by Linear when provided. Otherwise use
`feature/`, `fix/`, or `docs/` followed by a short description.

Before committing, run the checks in the relevant component README and review
`git diff`. Commit app lockfiles with dependency changes and Alembic revisions
with model changes. Keep `.env`, credentials, dependencies, and build output out of Git.

Stage the files for your change, then:

```bash
git diff --cached
git commit -m "Describe the change"
git push -u origin HEAD
```

Open a pull request targeting `sprint`. Include the Linear issue, a brief change
description, and validation results. Wait for CI and team review before merging.
Stable milestones reach `main` through a pull request from `sprint`.
For setup changes, have another teammate follow the instructions and record the
result in the pull request or Linear issue.
