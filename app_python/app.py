import json
import logging
import os
import platform
import socket
import sys
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.fromtimestamp(
                record.created,
                tz=timezone.utc,
            ).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "service": "devops-python",
        }

        for field in (
            "event",
            "method",
            "path",
            "status_code",
            "client_ip",
            "duration_ms",
            "host",
            "port",
            "debug",
        ):
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, ensure_ascii=True)


def configure_logging() -> logging.Logger:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(handler)

    app_logger = logging.getLogger("devops.python")
    app_logger.setLevel(logging.INFO)
    app_logger.propagate = True
    return app_logger


logger = configure_logging()
REQUEST_COUNTER = Counter(
    "http_requests_total",
    "Total HTTP requests.",
    ["method", "endpoint", "status_code"],
)
REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds.",
    ["method", "endpoint"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)
REQUESTS_IN_PROGRESS = Gauge(
    "http_requests_in_progress",
    "HTTP requests currently being processed.",
    ["method", "endpoint"],
)
ENDPOINT_CALLS = Counter(
    "devops_info_endpoint_calls_total",
    "Total calls to DevOps info service endpoints.",
    ["endpoint"],
)
SYSTEM_INFO_DURATION = Histogram(
    "devops_info_system_collection_seconds",
    "Time spent collecting system information.",
    buckets=(0.0005, 0.001, 0.0025, 0.005, 0.01, 0.025, 0.05),
)

# ======== Parameters ========
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", 5000))
DEBUG = os.getenv("DEBUG", "false").lower() == "true"

# ======== Setup ========
START_TIME = datetime.now(timezone.utc)


@asynccontextmanager
async def lifespan(_: FastAPI):
    logger.info(
        "application startup",
        extra={
            "event": "startup",
            "host": HOST,
            "port": PORT,
            "debug": DEBUG,
        },
    )
    yield
    logger.info("application shutdown", extra={"event": "shutdown"})


app = FastAPI(lifespan=lifespan)


def normalize_endpoint(path: str) -> str:
    if path in {"/", "/health", "/metrics"}:
        return path
    return "other"


@app.middleware("http")
async def log_requests(request: Request, call_next):
    started = time.perf_counter()
    client_ip = request.client.host if request.client else "unknown"
    endpoint = normalize_endpoint(request.url.path)
    in_progress = REQUESTS_IN_PROGRESS.labels(
        method=request.method,
        endpoint=endpoint,
    )
    in_progress.inc()

    try:
        response = await call_next(request)
    except Exception:
        duration_seconds = max(time.perf_counter() - started, 0)
        REQUEST_COUNTER.labels(
            method=request.method,
            endpoint=endpoint,
            status_code="500",
        ).inc()
        REQUEST_DURATION.labels(
            method=request.method,
            endpoint=endpoint,
        ).observe(duration_seconds)
        logger.exception(
            "request failed",
            extra={
                "event": "request_error",
                "method": request.method,
                "path": request.url.path,
                "client_ip": client_ip,
            },
        )
        raise
    finally:
        in_progress.dec()

    duration_ms = round((time.perf_counter() - started) * 1000, 2)
    duration_seconds = duration_ms / 1000
    REQUEST_COUNTER.labels(
        method=request.method,
        endpoint=endpoint,
        status_code=str(response.status_code),
    ).inc()
    REQUEST_DURATION.labels(
        method=request.method,
        endpoint=endpoint,
    ).observe(duration_seconds)
    log_level = (
        logging.ERROR if response.status_code >= 500
        else logging.WARNING if response.status_code >= 400
        else logging.INFO
    )
    logger.log(
        log_level,
        "request completed",
        extra={
            "event": "http_request",
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "client_ip": client_ip,
            "duration_ms": duration_ms,
        },
    )
    return response


# ======== Endpoints ========
@app.get("/")
def main_endpoint(request: Request):
    ENDPOINT_CALLS.labels(endpoint="/").inc()
    return {
        "service": {
            "name": "devops-info-service",
            "version": "1.0.0",
            "description": "DevOps course info service",
            "framework": "FastAPI",
        },
        "system": get_system_info(),
        "runtime": {
            "uptime_seconds": get_uptime()["seconds"],
            "uptime_human": get_uptime()["human"],
            "current_time": get_current_time(),
            "timezone": "UTC",      # Static for simplicity
        },
        "request": {
            "client_ip": request.client.host,
            "user_agent": request.headers.get("user-agent"),
            "method": request.method,
            "path": request.url.path,
        },
        "endpoints": [
            {"path": "/", "method": "GET",
             "description": "Service information"},
            {"path": "/health", "method": "GET",
             "description": "Health check"},
        ],
    }


@app.get("/health")
def health():
    ENDPOINT_CALLS.labels(endpoint="/health").inc()
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "uptime_seconds": get_uptime()["seconds"],
    }


@app.get("/metrics")
def metrics():
    ENDPOINT_CALLS.labels(endpoint="/metrics").inc()
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


# ======== Functions ========
def get_system_info():
    started = time.perf_counter()
    hostname = socket.gethostname()
    platform_name = platform.system()
    architecture = platform.machine()
    cpu_count = os.cpu_count()
    python_version = platform.python_version()
    SYSTEM_INFO_DURATION.observe(max(time.perf_counter() - started, 0))
    return {
        "hostname": hostname,
        "platform": platform_name,
        "architecture": architecture,
        "cpu_count": cpu_count,
        "python_version": python_version
    }


def get_uptime():
    delta = datetime.now(timezone.utc) - START_TIME
    seconds = int(delta.total_seconds())
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    return {
        'seconds': seconds,
        'human': f"{hours} hours, {minutes} minutes"
    }


def get_current_time():
    return datetime.now(timezone.utc).isoformat()


# ======== Launch ========
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=HOST,
        port=PORT,
        reload=DEBUG,
        access_log=False,
        log_config=None,
    )
