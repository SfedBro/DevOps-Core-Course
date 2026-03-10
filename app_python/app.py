import json
import logging
import os
import platform
import socket
import sys
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, Request


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


@app.middleware("http")
async def log_requests(request: Request, call_next):
    started = time.perf_counter()
    client_ip = request.client.host if request.client else "unknown"

    try:
        response = await call_next(request)
    except Exception:
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

    duration_ms = round((time.perf_counter() - started) * 1000, 2)
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
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "uptime_seconds": get_uptime()["seconds"],
    }


# ======== Functions ========
def get_system_info():
    hostname = socket.gethostname()
    platform_name = platform.system()
    architecture = platform.machine()
    cpu_count = os.cpu_count()
    python_version = platform.python_version()
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
        "app:app",
        host=HOST,
        port=PORT,
        reload=DEBUG,
        access_log=False,
        log_config=None,
    )
