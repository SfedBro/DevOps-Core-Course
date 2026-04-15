# devops-info-service (Python)

[![Python CI + Docker Build](https://github.com/SfedBro/DevOps-Core-Course/actions/workflows/python-ci.yml/badge.svg?branch=lab03)](https://github.com/SfedBro/DevOps-Core-Course/actions/workflows/python-ci.yml)

## Overview

This is the Python implementation of the DevOps Info Service.  
It provides endpoints to get detailed information about the service, system, runtime, and health status.

## Prerequisites

- Python 3.11 or higher
- Dependencies listed in `requirements.txt`

## Installation

```bash
python -m venv venv

# Windows PowerShell
.\venv\Scripts\Activate.ps1

# Unix or Git Bash
source venv/bin/activate

pip install -r requirements.txt
```

## Run

```
# Run with default host and port (0.0.0.0:5000)
python app.py

# Or specify host and port via environment variables
# Windows PowerShell
$env:HOST=127.0.0.1
$env:PORT=8080
python app.py

# Unix / Bash
HOST=127.0.0.1 PORT=8080 python app.py
```

## API Endpoints

- `GET /` - Service and system information
- `GET /health` - Health check
- `GET /metrics` - Prometheus metrics
- `GET /visits` - Current persisted visits count

## Visits Counter

The root endpoint increments a persisted visits counter on every request. The
counter is stored as a plain text integer.

Configuration:

- `VISITS_FILE` - path to the visits counter file. Docker and Kubernetes use
  `/data/visits`.
- `CONFIG_FILE` - optional JSON configuration file path. Kubernetes mounts this
  from a ConfigMap at `/config/config.json`.

Local example:

```bash
VISITS_FILE=./data/visits python app.py
curl http://localhost:5000/
curl http://localhost:5000/visits
cat ./data/visits
```

## Troubleshooting

If the server does not start or you get errors about execution policy on Windows PowerShell, try:

```
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

If the port is busy, find and kill the process:

```
netstat -ano | findstr :5000
taskkill /PID <pid> /F
```

## Docker

This application is containerized using Docker for easy deployment and consistency across environments.

### Build Docker Image Locally

```
docker build -t sfedbro/app_python:lab12 .
```

### Run Container Locally

```
docker run -p 5000:5000 -v ${PWD}/data:/data sfedbro/app_python:lab12
```

Access the app at http://localhost:5000 .

The `-v ${PWD}/data:/data` mount keeps `/data/visits` on the host, so the count
survives container restarts.

### Pull and Run from Docker Hub

```
docker pull sfedbro/app_python:lab12
docker run -p 5000:5000 -v ${PWD}/data:/data sfedbro/app_python:lab12
```

## Testing

This project uses pytest for unit testing.

To run tests locally:

```bash
pytest -v
```

## Licence

MIT Licence

```

```
