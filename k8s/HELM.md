# Lab 10 - Helm Package Manager

## Chart Overview

This lab converts the Lab 9 Kubernetes manifests into Helm charts for reusable deployments.

Implemented charts:

- [mychart](./mychart)
  Main chart for the Python application
- [app2](./app2)
  Second application chart for the Go service, added for the bonus task
- [common-lib](./common-lib)
  Helm library chart with shared helper templates

Key template files:

- [mychart/Chart.yaml](./mychart/Chart.yaml)
  Main chart metadata and dependency on `common-lib`
- [mychart/values.yaml](./mychart/values.yaml)
  Shared defaults for image, service, resources, probes, security context, and hooks
- [mychart/values-dev.yaml](./mychart/values-dev.yaml)
  Development overrides
- [mychart/values-prod.yaml](./mychart/values-prod.yaml)
  Production-style overrides
- [mychart/templates/_helpers.tpl](./mychart/templates/_helpers.tpl)
  Compatibility wrappers under `mychart.*` that delegate to shared `common-lib` helpers
- [mychart/templates/deployment.yaml](./mychart/templates/deployment.yaml)
  Templated Deployment
- [mychart/templates/service.yaml](./mychart/templates/service.yaml)
  Templated Service
- [mychart/templates/hooks/pre-install-job.yaml](./mychart/templates/hooks/pre-install-job.yaml)
  Validation hook
- [mychart/templates/hooks/post-install-job.yaml](./mychart/templates/hooks/post-install-job.yaml)
  Smoke-test hook

Values organization strategy:

- top-level sections for `image`, `service`, `resources`, probes, and hooks
- environment-specific overrides in dedicated values files
- helper templates used for consistent naming and labels
- health checks kept active and configurable

## Configuration Guide

Important values:

- `replicaCount`
  Controls Deployment size
- `image.repository`, `image.tag`, `image.pullPolicy`
  Configure image source and pull behavior
- `service.type`, `service.port`, `service.targetPort`, `service.nodePort`
  Control exposure model and ports
- `resources`
  CPU and memory requests/limits
- `env`
  Application runtime variables
- `livenessProbe` and `readinessProbe`
  Health-check paths, ports, and timings
- `hooks`
  Hook images, weights, and smoke-test behavior

Environment differences:

- Dev:
  - 1 replica
  - smaller resources
  - `NodePort`
  - debug-friendly values
- Prod:
  - 3 replicas
  - larger resources
  - `LoadBalancer`
  - production-style defaults

Example commands:

```bash
helm install myapp k8s/mychart -f k8s/mychart/values-dev.yaml --namespace devops-helm --create-namespace
helm upgrade myapp k8s/mychart -f k8s/mychart/values-prod.yaml --namespace devops-helm
helm upgrade myapp k8s/mychart --namespace devops-helm --set replicaCount=5
```

## Hook Implementation

Implemented hooks:

- Pre-install Job
  - validates required values before installation
  - weight: `-5`
- Post-install Job
  - runs an in-cluster smoke test against `/health`
  - weight: `5`

Deletion policy:

- `before-hook-creation,hook-succeeded`

Why:

- prevents stale Jobs from accumulating between installs/upgrades
- keeps the namespace clean after successful hook execution

Observed result:

- hooks ran successfully during install and upgrade
- `kubectl get jobs -n devops-helm` showed no remaining Jobs after success

## Installation Evidence

Helm setup and exploration:

- [lab10_1_helm-version.png](./docs/screenshots/lab10_1_helm-version.png)
- [lab10_2_helm-chart.png](./docs/screenshots/lab10_2_helm-chart.png)

Validation evidence:

- [lab10_3_helm-lint.png](./docs/screenshots/lab10_3_helm-lint.png)
- [lab10_helm-dryrun.txt](./docs/lab10_helm-dryrun.txt)

Runtime evidence:

- [lab10_4_dev-release.png](./docs/screenshots/lab10_4_dev-release.png)
- [lab10_5_prod-upgrade.png](./docs/screenshots/lab10_5_prod-upgrade.png)
- [lab10_6_hooks-evidence.png](./docs/screenshots/lab10_6_hooks-evidence.png)
- [lab10_7_app-health.png](./docs/screenshots/lab10_7_app-health.png)

Observed deployment states:

- dev install produced a `NodePort` service and 1 running pod
- prod upgrade produced 3 running pods and a `LoadBalancer` service
- local `kind` cluster shows LoadBalancer external IP as `<pending>`, which is expected

## Operations

Install:

```bash
helm install myapp k8s/mychart -f k8s/mychart/values-dev.yaml --namespace devops-helm --create-namespace --wait --wait-for-jobs
```

Upgrade:

```bash
helm upgrade myapp k8s/mychart -f k8s/mychart/values-prod.yaml --namespace devops-helm --wait --wait-for-jobs
```

Inspect:

```bash
helm list -A
helm history myapp -n devops-helm
helm get values myapp -n devops-helm
helm get manifest myapp -n devops-helm
```

Rollback:

```bash
helm rollback myapp 1 -n devops-helm --wait --wait-for-jobs
```

Uninstall:

```bash
helm uninstall myapp -n devops-helm
kubectl delete namespace devops-helm
```

## Testing & Validation

Commands used:

```bash
helm version
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update
helm show chart prometheus-community/prometheus
helm lint k8s/mychart
helm template myapp k8s/mychart
helm install --dry-run --debug myapp k8s/mychart -f k8s/mychart/values-dev.yaml --namespace devops-helm --create-namespace
helm install myapp k8s/mychart -f k8s/mychart/values-dev.yaml --namespace devops-helm --create-namespace --wait --wait-for-jobs
helm upgrade myapp k8s/mychart -f k8s/mychart/values-prod.yaml --namespace devops-helm --wait --wait-for-jobs
```

Application accessibility verification:

```bash
kubectl port-forward svc/myapp-mychart 18081:80 -n devops-helm
curl http://localhost:18081/health
```

Validated:

- Helm installed and working
- public chart inspected
- chart linting passed
- templates rendered correctly
- dry-run showed the expected hooks and manifests
- install and upgrade worked
- hooks executed and were cleaned up
- app health endpoint responded successfully

## Bonus - Library Charts

Bonus implementation summary:

- [common-lib](./common-lib) created as a Helm library chart
- [app2](./app2) created for the Go application
- both [mychart/Chart.yaml](./mychart/Chart.yaml) and [app2/Chart.yaml](./app2/Chart.yaml) depend on `common-lib`
- dependency artifacts were generated in both charts

Shared templates extracted:

- `common.name`
- `common.fullname`
- `common.chart`
- `common.selectorLabels`
- `common.labels`

How the two application charts use the library:

- [mychart/templates/_helpers.tpl](./mychart/templates/_helpers.tpl)
  Wraps `common.*` helpers while preserving `mychart.*` compatibility for later labs
- [app2/templates/_helpers.tpl](./app2/templates/_helpers.tpl)
  Provides `app2.*` wrappers over the same shared helpers

Go chart details:

- image: `sfedbro/app_go:latest`
- port: `8080`
- health endpoint: `/health`
- dev node port: `30082`

Bonus evidence:

- [lab10_bonus_library.txt](./docs/lab10_bonus_library.txt)

It contains:

- `helm list -A` with both releases
- `kubectl get all -n devops-helm`
- successful `curl` response from the Go service via `port-forward`

Benefits:

- no duplicated naming/label logic between app charts
- easier maintenance
- consistent metadata across releases
- future shared changes only need to be made once

## Detailed Report

The longer, more walkthrough-style report is available in [docs/LAB10.md](./docs/LAB10.md).
