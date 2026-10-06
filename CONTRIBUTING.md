# Contributing

This document defines the development workflow for the Secure University Attendance System.

## Branch Structure

### `main`

The `main` branch contains the stable version of the project.

Do not develop directly on `main`.

Changes should reach `main` through pull requests.

### `sprint`

The `sprint` branch is the integration branch for the current sprint.

Completed features and fixes should normally be merged into `sprint` before being merged into `main`.

### Feature Branches

New features should use:

```text
feature/<description>
```

Examples:

```text
feature/student-login
feature/attendance-session
feature/student-dashboard
feature/database-setup
```

### Fix Branches

Bug fixes should use:

```text
fix/<description>
```

Examples:

```text
fix/login-validation
fix/attendance-recording
```

### Documentation Branches

Documentation changes can use:

```text
docs/<description>
```

Example:

```text
docs/database-design
```

## Development Workflow

Before starting work:

```bash
git checkout sprint
git pull
```

Create a new branch:

```bash
git checkout -b feature/<feature-name>
```

Example:

```bash
git checkout -b feature/student-login
```

Make your changes, then commit them:

```bash
git add .
git commit -m "Add student login"
```

Push the branch:

```bash
git push -u origin feature/student-login
```

Then create a pull request:

```text
feature/student-login
        ↓
      sprint
```

## Pull Requests

Before merging:

- Make sure the feature works
- Make sure CI passes
- Review the changed files
- Resolve merge conflicts
- Have another team member review the pull request when possible

Feature branches should normally merge into `sprint`.

At the end of a sprint or when a stable milestone is reached:

```text
sprint
   ↓
 main
```

## Commit Messages

Use short, descriptive commit messages.

Good examples:

```text
Add student login
Create attendance session endpoint
Fix device registration validation
Update database schema
```

Avoid vague messages such as:

```text
stuff
changes
fix
update
```

## Branch Cleanup

After a branch has been merged, delete it.

Locally:

```bash
git checkout sprint
git pull
git branch -d feature/student-login
```

## CI

GitHub Actions runs automatically on pushes to `main` and `sprint`, and on pull requests targeting either branch.

The `Repository checks` job verifies that `README.md` and `CONTRIBUTING.md` exist and are not empty. All required CI checks should pass before merging.

Application tests, builds, and security checks will be added when there is application code to validate. Deployment is not configured yet.
