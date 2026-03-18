# Lab 08 - Metrics & Monitoring with Prometheus

## Architecture

```text
Client -> Grafana (13000 -> 3000)
          |-> Loki datasource -> Loki (3100)
          |-> Prometheus datasource -> Prometheus (9090)

app-python (18000 -> 5000) -> /metrics -> Prometheus
         \-> JSON logs -> Docker stdout -> Promtail -> Loki

app-go (18001 -> 8080) -> JSON logs -> Docker stdout -> Promtail -> Loki

Prometheus also scrapes:
- itself on localhost:9090
- Loki on loki:3100/metrics
- Grafana on grafana:3000/metrics
```

## Application Instrumentation

Python app instrumentation lives in [app.py](../../app_python/app.py).

Added metrics:

- `http_requests_total` - Counter for total requests with labels `method`, `endpoint`, `status_code`
- `http_request_duration_seconds` - Histogram for request latency
- `http_requests_in_progress` - Gauge for current in-flight requests
- `devops_info_endpoint_calls_total` - Counter for endpoint usage
- `devops_info_system_collection_seconds` - Histogram for system info collection duration

Metric choices:

- Counter is used for request volume and endpoint usage because these values only increase.
- Gauge is used for in-progress requests because concurrency goes up and down.
- Histogram is used for duration so Prometheus can calculate latency distributions and p95.

Available endpoint:

- `GET /metrics`

## Prometheus Configuration

Prometheus config lives in [prometheus.yml](../prometheus/prometheus.yml).

Key settings:

- scrape interval: `15s`
- self-scrape job: `prometheus`
- application scrape job: `app-python`
- infrastructure jobs: `loki`, `grafana`
- retention is configured in compose flags:
  - `--storage.tsdb.retention.time=15d`
  - `--storage.tsdb.retention.size=10GB`

Scrape targets:

- `localhost:9090`
- `app-python:5000`
- `loki:3100`
- `grafana:3000`

## Dashboard Walkthrough

Dashboard file:

- [lab08-metrics.json](../grafana/dashboards/lab08-metrics.json)

Provisioned panels:

1. `Request Rate` - requests/sec by endpoint
2. `Error Rate` - 5xx rate
3. `Request Duration p95` - 95th percentile latency by endpoint
4. `Request Duration Heatmap` - latency distribution
5. `Active Requests` - in-flight requests gauge
6. `Status Code Distribution` - request rate by status code
7. `App Uptime` - Prometheus `up` value for the Python app

Grafana datasources:

- [loki.yml](../grafana/provisioning/datasources/loki.yml)
- [prometheus.yml](../grafana/provisioning/datasources/prometheus.yml)

## PromQL Examples

Request rate by endpoint:

```promql
sum by (endpoint) (rate(http_requests_total[5m]))
```

Error rate:

```promql
sum(rate(http_requests_total{status_code=~"5.."}[5m]))
```

P95 latency:

```promql
histogram_quantile(0.95, sum by (le, endpoint) (rate(http_request_duration_seconds_bucket[5m])))
```

Status code breakdown:

```promql
sum by (status_code) (rate(http_requests_total[5m]))
```

In-flight requests:

```promql
sum(http_requests_in_progress)
```

Application uptime:

```promql
up{job="app-python"}
```

These queries demonstrate the RED method:

- Rate -> `rate(http_requests_total[5m])`
- Errors -> `rate(http_requests_total{status_code=~"5.."}[5m])`
- Duration -> `http_request_duration_seconds_bucket`

## Production Setup

Implemented in [docker-compose.yml](../docker-compose.yml):

- health checks for Prometheus, Loki, Grafana, Python app, and Go app
- resource limits and reservations for all services
- Prometheus retention by time and size
- persistent volumes:
  - `prometheus-data`
  - `loki-data`
  - `grafana-data`
  - `promtail-positions`
- Grafana authentication kept enabled, anonymous access disabled

Current host ports:

- Grafana: `13000`
- Prometheus: `9090`
- Loki: `3100`
- Python app: `18000`
- Go app: `18001`

## Testing Results

Start the stack:

```bash
cd monitoring
docker compose up -d --build
docker compose ps
```

Check service health:

```bash
curl http://localhost:9090/-/healthy
curl http://localhost:3100/ready
curl http://localhost:18000/health
curl http://localhost:18000/metrics
```

Generate traffic:

```bash
for i in {1..20}; do curl http://localhost:18000/ > /dev/null; done
for i in {1..20}; do curl http://localhost:18000/health > /dev/null; done
```

Prometheus UI:

- open `http://localhost:9090/targets`
- all configured targets should be `UP`

Grafana:

- open `http://localhost:13000`
- folder: `Observability`
- dashboards:
  - `Lab 07 - Observability & Logging`
  - `Lab 08 - Metrics & Monitoring`

Persistence test:

1. Create or open dashboards in Grafana.
2. Run `docker compose down`.
3. Run `docker compose up -d`.
4. Dashboard data should still be present because Grafana and Prometheus use named volumes.

## Challenges & Solutions

1. Lab 7 already used non-default host ports due Windows 10 + WSL2 Docker port-forwarding issues, so Lab 8 was integrated into the same working port layout.
2. Grafana needed a second datasource for Prometheus while keeping Loki available for log dashboards, so datasource provisioning was split by backend.
3. Prometheus scraping requires low-cardinality labels, so endpoints were normalized to `/`, `/health`, `/metrics`, and `other`.
4. RED method metrics required both middleware timing and request counting, so metrics were recorded centrally in FastAPI middleware rather than inside each route only.

## Metrics vs Logs

Use metrics when you need:

- trends over time
- request rate
- error rate
- latency percentiles
- quick health overview

Use logs when you need:

- request details
- exceptions and stack traces
- exact payload/context at failure time
- debugging of one specific event

Together:

- Prometheus answers "how much/how often?"
- Loki answers "what exactly happened?"

## Evidence

Collected evidence:

- [lab08_metrics.txt](./lab08_metrics.txt) - raw `/metrics` endpoint output from the Python app
- [lab08_1-targets-up.png](./screenshots/lab08_1-targets-up.png) - Prometheus targets page with targets in `UP`
- [lab08_2-targets-up-query.png](./screenshots/lab08_2-targets-up-query.png) - Prometheus query UI with successful query result
- [lab08_3-endpoints-metrics-query.png](./screenshots/lab08_3-endpoints-metrics-query.png) - PromQL request-rate query grouped by endpoint
- [lab08_4-request-rate-endpoints-grafana.png](./screenshots/lab08_4-request-rate-endpoints-grafana.png) - Grafana metrics dashboard / panel showing live metrics
- [lab08_5-docker-compose-ps-powershell.png](./screenshots/lab08_5-docker-compose-ps-powershell.png) - Docker Compose services and health states
