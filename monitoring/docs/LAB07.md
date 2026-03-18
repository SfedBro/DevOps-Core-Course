# Lab 07 - Observability & Logging with Loki Stack

## Architecture

```text
Client -> Grafana (13000 -> 3000) -> Loki datasource -> Loki (3100) -> TSDB + filesystem storage
          ^
          |
          +-> provisioned dashboard + datasource

Promtail -> Docker socket + /var/lib/docker/containers -> Loki
   |
   +-> collects logs only from containers with label logging=promtail

app-python (18000 -> 5000) -> JSON logs -> Docker stdout/stderr -> Promtail
app-go     (18001 -> 8080) -> JSON logs -> Docker stdout/stderr -> Promtail
```

## Setup Guide

1. Copy the environment template:

```bash
cd monitoring
cp .env.example .env
```

2. Set a real Grafana password in `.env`.

3. Start the stack:

```bash
docker compose up -d --build
docker compose ps
```

4. Open Grafana at `http://localhost:13000` and log in with the credentials from `.env`.

5. Open `Dashboards -> Observability -> Lab 07 - Observability & Logging`.

## Configuration

### Loki

File: `monitoring/loki/config.yml`

Key decisions:

- `schema: v13` with `store: tsdb` for Loki 3.0 recommended single-binary storage.
- `object_store: filesystem` for a local lab-friendly deployment.
- `retention_period: 168h` to keep logs for 7 days.
- `compactor.retention_enabled: true` so expired data is cleaned up automatically.

```yaml
schema_config:
  configs:
    - from: 2024-01-01
      store: tsdb
      object_store: filesystem
      schema: v13
```

```yaml
storage_config:
  tsdb_shipper:
    active_index_directory: /loki/index
    cache_location: /loki/index_cache
  filesystem:
    directory: /loki/chunks
```

### Promtail

File: `monitoring/promtail/config.yml`

Key decisions:

- Docker service discovery through `/var/run/docker.sock`.
- Filtering by label `logging=promtail` so system containers are ignored.
- Relabeling `__meta_docker_container_name` and `__meta_docker_container_label_app` into Loki labels.

```yaml
docker_sd_configs:
  - host: unix:///var/run/docker.sock
    filters:
      - name: label
        values: ['logging=promtail']
```

## Application Logging

### Python app

File: `app_python/app.py`

Implemented:

- `JSONFormatter`
- startup and shutdown logs
- request middleware with `method`, `path`, `status_code`, `client_ip`, `duration_ms`
- exception logging for failed requests

Example log:

```json
{
	"timestamp": "2026-03-10T12:00:00+00:00",
	"level": "INFO",
	"message": "request completed",
	"service": "devops-python",
	"method": "GET",
	"path": "/health",
	"status_code": 200,
	"client_ip": "172.18.0.1",
	"duration_ms": 1.24
}
```

### Go app

File: `app_go/main.go`

Implemented:

- JSON logs to stdout
- startup log
- HTTP middleware for structured request logs
- error logs for runtime failures

## Dashboard

Dashboard file: `monitoring/grafana/dashboards/lab07-observability.json`

Provisioned panels:

1. `Logs Table` -> `{app=~"devops-.*"}`
2. `Request Rate` -> `sum by (app) (rate({app=~"devops-.*"}[1m]))`
3. `Error Logs` -> `{app=~"devops-.*"} | json | level="ERROR"`
4. `Log Level Distribution` -> `sum by (level) (count_over_time({app=~"devops-.*"} | json [5m]))`

Useful Explore queries:

```logql
{app="devops-python"}
{app="devops-python"} | json | method="GET"
{app="devops-go"} | json | status_code=500
sum by (app) (rate({app=~"devops-.*"}[5m]))
```

any time period other than 5 minutes may be used for monitoring

## Production Config

Implemented in `monitoring/docker-compose.yml`:

- resource limits and reservations for every service
- anonymous Grafana access disabled
- admin password moved to `.env`
- health checks for Loki and Grafana
- named volumes for Loki, Grafana, and Promtail positions
- host ports mapped as `13000` for Grafana, `18000` for Python app, `18001` for Go app

Important note:

- `deploy.resources` is included for Compose compatibility and documentation.
- Promtail needs Docker socket access, which is acceptable for the lab but should be restricted in production.
- Host ports were remapped from the assignment defaults to `13000`, `18000`, and `18001` because Docker Desktop with WSL had port-forwarding conflicts on the standard ports during testing.(or other reasons, because I could not launch app on these ports, even though they were shown as not occupied)

## Testing

Start the stack:

```bash
cd monitoring
docker compose up -d --build
docker compose ps
curl http://localhost:3100/ready
curl http://localhost:18000/
curl http://localhost:18001/health
```

if `cd monitoring` does not work, enter path to monitoring folder.\
Generate logs:

```bash
for i in {1..20}; do curl http://localhost:18000/ > /dev/null; done
for i in {1..20}; do curl http://localhost:18000/health > /dev/null; done
for i in {1..20}; do curl http://localhost:18001/health > /dev/null; done
```

Expected verification:

- Loki returns `ready`
- Promtail shows active targets
- both applications appear in Grafana Explore
- provisioned dashboard shows data in all four panels

## Challenges

1. Loki 3.0 uses TSDB and schema v13, so older `boltdb-shipper` examples were intentionally avoided.
2. Grafana security defaults for the lab were tightened by disabling anonymous access and moving credentials to `.env`.
3. Dashboard and datasource were provisioned automatically to remove manual setup steps and make the Ansible role idempotent.
4. Ports were changed due unavailability of testing on suggested ones.
5. Other troubles with Docker Desktop and WSL.

## Evidence To Capture

Saved screenshots:

- [lab7_01-docker-compose.png](./screenshots/lab7_01-docker-compose.png)
- [lab7_02-LoginGrafana.png](./screenshots/lab7_02-LoginGrafana.png)
- [lab7_03-explore-all.png](./screenshots/lab7_03-explore-all.png)
- [lab7_04-explore-json.png](./screenshots/lab7_04-explore-json.png)
- [lab7_05-explore-GET.png](./screenshots/lab7_05-explore-GET.png)
- [lab7_06-query_count.png](./screenshots/lab7_06-query_count.png)
- [lab7_07-statuses_all_up.png](./screenshots/lab7_07-statuses_all_up.png)
- [lab7_08-dashboard.png](./lab7_08-dashboard.png)
