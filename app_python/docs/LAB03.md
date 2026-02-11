# Lab 3 — Continuous Integration (CI/CD)

## Task 1 — Unit Testing

### Testing Framework Choice

For this project, pytest was selected as the testing framework.

### Justification:

- Simple and clean syntax compared to built-in unittest
- Excellent integration with FastAPI using TestClient
- Powerful assertion system
- Large ecosystem and community support
- Industry-standard choice for modern Python projects

pytest and required test dependencies were installed in the virtual environment and can be added to dependencies.

### Test Structure

A dedicated `tests/` directory was created(during lab 1, actually):

```
app_python/
    app.py
    tests/
```

It follows standard Python project conventions and allows pytest to discover tests automatically.

### Implemented Unit Tests

Unit tests were written using FastAPI’s `TestClient` to test the application without starting a real HTTP server.

### Tested Endpoints

#### `GET /`

The main service information endpoint is tested for:

- HTTP 200 status code
- Presence of required top-level JSON fields:
  - service
  - system
  - runtime
  - request
  - endpoints
- Correct service metadata:
  - service.name
  - service.framework

This ensures that the API contract is respected and the response structure remains stable.

#### `GET /health`

The health check endpoint is tested for:

- HTTP 200 status code
- Correct health payload structure:
  - status == "healthy"
  - presence of timestamp field
  - presence of uptime_seconds field
- Correct data types of uptime fields

This validates that monitoring and health checks can reliably consume this endpoint.

#### Error and Edge Case Considerations

While the main focus is on successful responses, the test suite validates:

- Correct HTTP status codes
- Required JSON fields exist
- Data types are correct for key fields

The tests are designed to catch:

- Breaking changes in response structure
- Missing fields
- Incorrect service metadata

This provides meaningful tests.

#### How the Application Is Tested Without Running a Server

FastAPI’s `TestClient` is used to simulate HTTP requests directly against the application object:

```
client = TestClient(app)
```

It is used for fast isolated unit tests without binding to network ports or running Uvicorn.

#### Stable Testing

To avoid fragile tests, the following are not asserted with exact values:

- Hostname
- Client IP address
- Timestamp values
- Platform-specific system information

Instead, tests verify existence and structure for better practice with system and environment-dependent data.

### How to Run Tests Locally

From the app_python directory with virtual environment activated:

```
pytest -v
```

#### Example Terminal Output

All tests success:

```
collected 8 items

tests/test_app.py::test_root_endpoint_status_code PASSED                                                         [ 12%]
tests/test_app.py::test_root_endpoint_structure PASSED                                                           [ 25%]
tests/test_app.py::test_service_info PASSED                                                                      [ 37%]
tests/test_app.py::test_health_endpoint_status_code PASSED                                                       [ 50%]
tests/test_app.py::test_health_endpoint_payload PASSED                                                           [ 62%]
tests/test_app.py::test_runtime_fields PASSED                                                                    [ 75%]
tests/test_app.py::test_system_info_fields PASSED                                                                [ 87%]
tests/test_app.py::test_not_found_endpoint PASSED                                                                [100%]
```

## Task 2 — GitHub Actions CI Workflow

This project uses GitHub Actions for CI.

Workflow stages:

- Linting with flake8
- Unit tests with pytest
- Docker image build and push to Docker Hub

Versioning strategy:
Calendar Versioning (CalVer) is used in format YYYY.MM.

Docker images are tagged with:

- `<version>` (e.g. 2026.02)
- latest
