# Lab 3 — Continuous Integration (CI/CD)

## Bonus Task — Multi-App CI & Test Coverage

### Multi-App CI

A separate workflow for the Go app was created: `.github/workflows/go-ci.yml`.

**Path filters**:

- Python workflow runs only when `app_python/` changes.
- Go workflow runs only when `app_go/` changes.

This ensures that workflows are triggered selectively and independently, saving CI resources and avoiding unnecessary builds.

### Go Workflow

- Uses `actions/setup-go@v4` for Go environment
- Runs `go test ./... -v -cover` for unit tests
- Docker build and push with CalVer (`YYYY.MM`) and `latest` tags

**Docker tags created**:

- `sfedbro/app_go:2026.02`
- `sfedbro/app_go:latest`

### Test Coverage

- Coverage reports generated using Go's `-coverprofile`
- Uploaded to Codecov for badge display
- Coverage threshold enforced (40% worked for me)
- Current coverage: 68.11%

![Go Coverage](https://img.shields.io/codecov/c/github/sfedbro/devops-core-course/lab03?flag=go)

### Benefits of Path-Based Triggers

- Reduces unnecessary workflow runs
- Optimizes CI pipeline time
- Keeps multi-app monorepo CI organized
- Allows Python and Go workflows to run in parallel without interfering

### Workflow Proof

- Both Python and Go workflows run independently in GitHub Actions (see in `screenshots/`)
- Only triggers for relevant changes in respective directories
- Docker images for Go app successfully built and pushed
- Coverage reports uploaded to Codecov

### Path Filters — Proof of Selective Triggering

- Change in `app_go/` triggered **only** Go CI workflow
- Change in `app_python/` triggered **only** Python CI workflow
- Change in root files (e.g., `README.md`) did **not** trigger any workflow

This demonstrates correct path-based filtering in a monorepo setup.
