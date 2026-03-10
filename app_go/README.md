# devops-info-service (Go)

![Go Coverage](https://img.shields.io/codecov/c/github/sfedbro/devops-core-course/lab03?flag=go)

## Overview

This is the Go implementation of the DevOps Info Service. It provides the same API as the Python version.

## Prerequisites

- Go 1.20+ installed

## Build

```bash
go build -o devops-info-service.exe
```

## Run

```
# Default port 8080
./devops-info-service.exe

# Or specify port via environment variable
PORT=3000 ./devops-info-service.exe
```

## API Endpoints

- `GET /` - Service and system information
- `GET /health` - Health check

## Docker

Docker image can be built via CI or locally:

```
docker build -t sfedbro/app_go:latest ./app_go
docker build -t sfedbro/app_go:2026.02 ./app_go
```

https://hub.docker.com/repository/docker/sfedbro/app_go/general

## Test Coverage

Coverage generated via `go test -coverprofile=coverage.out`

Reports uploaded to Codecov\
https://app.codecov.io/github/sfedbro/devops-core-course/tree/lab03

Current coverage: 68.11%\
![Go Coverage](https://img.shields.io/codecov/c/github/sfedbro/devops-core-course/lab03?flag=go)

## Licence

MIT Licence
`To be made`
