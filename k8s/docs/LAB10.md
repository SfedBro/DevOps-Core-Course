# Lab 10 - Helm Package Manager

## Chart Overview

The Kubernetes manifests from Lab 9 were converted into a Helm chart located in [mychart](../mychart).
For the bonus task, the chart was extended with a reusable library chart and a second application chart for the Go service.

Chart structure:

```text
k8s/
├── common-lib/
│   ├── Chart.yaml
│   └── templates/
│       └── _helpers.tpl
├── app2/
│   ├── Chart.yaml
│   ├── values.yaml
│   ├── values-dev.yaml
│   ├── values-prod.yaml
│   └── templates/
│       ├── _helpers.tpl
│       ├── deployment.yaml
│       ├── service.yaml
│       ├── NOTES.txt
│       └── hooks/
│           ├── pre-install-job.yaml
│           └── post-install-job.yaml
├── mychart/
│   ├── Chart.yaml
│   ├── values.yaml
│   ├── values-dev.yaml
│   ├── values-prod.yaml
│   └── templates/
│       ├── _helpers.tpl
│       ├── deployment.yaml
│       ├── service.yaml
│       ├── NOTES.txt
│       └── hooks/
│           ├── pre-install-job.yaml
│           └── post-install-job.yaml
```

Key template files:

- [Chart.yaml](../mychart/Chart.yaml)
  Chart metadata, chart version, app version, and type.

- [values.yaml](../mychart/values.yaml)
  Shared defaults for image, service, resources, probes, security context, and hooks.

- [values-dev.yaml](../mychart/values-dev.yaml)
  Development overrides with 1 replica, smaller resources, `NodePort`, and `DEBUG=true`.

- [values-prod.yaml](../mychart/values-prod.yaml)
  Production-style overrides with 3 replicas, larger resources, and `LoadBalancer`.

- [templates/_helpers.tpl](../mychart/templates/_helpers.tpl)
  Compatibility helpers under the `mychart.*` namespace. These now call the shared templates from `common-lib` so Labs 11-12 can continue using `mychart.*` names without duplicating logic.

- [templates/deployment.yaml](../mychart/templates/deployment.yaml)
  Templated Deployment with configurable image, resources, env vars, security context, and health probes.

- [templates/service.yaml](../mychart/templates/service.yaml)
  Templated Service with configurable type and ports.

- [templates/hooks/pre-install-job.yaml](../mychart/templates/hooks/pre-install-job.yaml)
  Validation hook that runs before install.

- [templates/hooks/post-install-job.yaml](../mychart/templates/hooks/post-install-job.yaml)
  Smoke-test hook that checks the application health endpoint after install.

Values organization strategy:

- top-level keys for major concerns: `image`, `service`, `resources`, `livenessProbe`, `readinessProbe`, `hooks`
- nested values for readability and clean overrides
- health checks preserved and configurable, never commented out
- helper templates centralize labels and names for easier extension in Labs 11-12
- `common-lib` keeps the shared naming and label logic in one place for both the Python and Go charts

## Configuration Guide

Important values:

- `replicaCount`
  Controls Deployment replica count.

- `image.repository`, `image.tag`, `image.pullPolicy`
  Configure the application image and pull behavior.

- `service.type`, `service.port`, `service.targetPort`, `service.nodePort`
  Control how the app is exposed.

- `resources.requests` and `resources.limits`
  Keep scheduling predictable and prevent runaway resource use.

- `env`
  Configures runtime variables like `HOST`, `PORT`, and `DEBUG`.

- `livenessProbe` and `readinessProbe`
  Keep probe behavior configurable while preserving safe defaults.

- `hooks.*`
  Controls hook images, weights, and smoke-test behavior.

Environment strategy:

- Dev:
  - 1 replica
  - smaller resources
  - `NodePort`
  - `DEBUG=true`
  - local testing friendly

- Prod:
  - 3 replicas
  - larger resources
  - `LoadBalancer`
  - `DEBUG=false`
  - closer to production deployment expectations

Example installations:

```bash
# Development
helm install myapp k8s/mychart -f k8s/mychart/values-dev.yaml --namespace devops-helm --create-namespace

# Production-style upgrade
helm upgrade myapp k8s/mychart -f k8s/mychart/values-prod.yaml --namespace devops-helm

# Override a single value
helm upgrade myapp k8s/mychart --namespace devops-helm --set replicaCount=5
```

## Hook Implementation

Implemented hooks:

- Pre-install hook
  - resource: Job
  - purpose: validate that critical values like image repository, image tag, and replica count are present before install

- Post-install hook
  - resource: Job
  - purpose: run a smoke test against the application `/health` endpoint using the in-cluster service name

Execution order and weights:

- pre-install weight: `-5`
- post-install weight: `5`

This ensures validation runs before install completes, and smoke testing runs after the app is created.

Deletion policy:

- `before-hook-creation,hook-succeeded`

Why:

- `hook-succeeded` keeps the namespace clean after successful execution
- `before-hook-creation` prevents stale hook resources from blocking repeated installs/upgrades

Runtime verification result:

- hook jobs executed successfully during install and upgrade
- `kubectl get jobs -n devops-helm` returned no remaining Jobs after completion, confirming the deletion policy worked

## Installation Evidence

Helm setup:

- Helm installed successfully
- verified version: `v4.1.3`

Repository exploration:

Commands run:

```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update
helm show chart prometheus-community/prometheus
```

Observed chart details from public repo:

- chart name: `prometheus`
- chart version: `28.14.1`
- app version: `v3.10.0`
- chart type: `application`
- several dependencies such as `alertmanager`, `kube-state-metrics`, and `prometheus-node-exporter`

Validation commands run:

```bash
helm lint k8s/mychart
helm template myapp k8s/mychart
helm install --dry-run --debug myapp k8s/mychart -f k8s/mychart/values-dev.yaml --namespace devops-helm --create-namespace
```

Observed validation result:

- `helm lint` passed
- `helm template` rendered Deployment, Service, and both hook Jobs correctly
- `--dry-run --debug` showed rendered manifests, hooks, values, and NOTES output

Installed release evidence:

```bash
helm install myapp k8s/mychart -f k8s/mychart/values-dev.yaml --namespace devops-helm --create-namespace --wait --wait-for-jobs
helm list -A
kubectl get all -n devops-helm
kubectl get jobs -n devops-helm
```

Observed dev release state:

- release `myapp` installed in namespace `devops-helm`
- revision `1`
- 1 running Pod
- Service type `NodePort`
- node port `30081`
- no remaining Jobs after hook completion

Upgrade evidence:

```bash
helm upgrade myapp k8s/mychart -f k8s/mychart/values-prod.yaml --namespace devops-helm --wait --wait-for-jobs
helm history myapp -n devops-helm
helm get values myapp -n devops-helm
kubectl get all -n devops-helm
```

Observed prod-style upgrade state:

- release revision increased after upgrade
- previous revision was marked `superseded`
- Deployment updated to 3 replicas
- Service type changed to `LoadBalancer`
- in `kind`, external IP remains `<pending>`, which is expected for local clusters without a real cloud load balancer

Saved evidence files:

- Helm version: [lab10_1_helm-version.png](./screenshots/lab10_1_helm-version.png)
- Public chart exploration: [lab10_2_helm-chart.png](./screenshots/lab10_2_helm-chart.png)
- Helm lint: [lab10_3_helm-lint.png](./screenshots/lab10_3_helm-lint.png)
- Dry-run debug output: [lab10_helm-dryrun.txt](./lab10_helm-dryrun.txt)
- Dev release installation: [lab10_4_dev-release.png](./screenshots/lab10_4_dev-release.png)
- Prod upgrade and revision history: [lab10_5_prod-upgrade.png](./screenshots/lab10_5_prod-upgrade.png)
- Hook evidence and deployment details: [lab10_6_hooks-evidence.png](./screenshots/lab10_6_hooks-evidence.png)
- Application health check: [lab10_7_app-health.png](./screenshots/lab10_7_app-health.png)

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

## Bonus - Library Charts

Bonus implementation summary:

- [common-lib](../common-lib) was added as a Helm library chart
- [app2](../app2) was added as a second application chart for the Go service
- both [mychart/Chart.yaml](../mychart/Chart.yaml) and [app2/Chart.yaml](../app2/Chart.yaml) now declare `common-lib` as a file dependency
- `helm dependency update` generated [mychart/Chart.lock](../mychart/Chart.lock) and [app2/Chart.lock](../app2/Chart.lock)

Shared templates extracted into the library chart:

- `common.name`
- `common.fullname`
- `common.chart`
- `common.selectorLabels`
- `common.labels`

How both charts use the library:

- [mychart/templates/_helpers.tpl](../mychart/templates/_helpers.tpl)
  Keeps `mychart.*` wrappers for forward compatibility, but each helper delegates to `common.*`

- [app2/templates/_helpers.tpl](../app2/templates/_helpers.tpl)
  Defines thin `app2.*` wrappers over the same `common.*` helpers

Go application chart details:

- image: `sfedbro/app_go:latest`
- container port: `8080`
- health endpoint: `/health`
- dev service type: `NodePort`
- dev node port: `30082`

Bonus verification commands:

```bash
helm dependency update k8s/mychart
helm dependency update k8s/app2
helm lint k8s/mychart
helm lint k8s/app2
helm template myapp k8s/mychart -f k8s/mychart/values-prod.yaml
helm template mygoapp k8s/app2 -f k8s/app2/values-dev.yaml
helm upgrade myapp k8s/mychart -f k8s/mychart/values-prod.yaml --namespace devops-helm --wait --wait-for-jobs
helm install mygoapp k8s/app2 -f k8s/app2/values-dev.yaml --namespace devops-helm --wait --wait-for-jobs
helm list -A
kubectl get all -n devops-helm
kubectl port-forward svc/mygoapp-app2 18082:80 -n devops-helm
curl http://localhost:18082/health
```

Observed runtime result:

- `myapp` stayed deployed successfully after switching to the shared library templates
- `mygoapp` installed successfully as a separate Helm release
- `helm list -A` shows both releases in `devops-helm`
- `kubectl get all -n devops-helm` shows both Deployments and Services
- the Go application returned a healthy response through `port-forward`

Saved bonus evidence:

- [lab10_bonus_library.txt](./lab10_bonus_library.txt)
  Contains `helm list -A`, `kubectl get all -n devops-helm`, and the Go `/health` response captured after `port-forward`

Benefits of the library chart approach:

- shared labels and naming logic are defined once
- both app charts stay consistent
- future changes to common metadata only need to be made in one place
- `mychart.*` helper compatibility is preserved for later labs

## Testing & Validation

Commands executed:

```bash
helm version
helm lint k8s/mychart
helm template myapp k8s/mychart
helm install --dry-run --debug myapp k8s/mychart -f k8s/mychart/values-dev.yaml --namespace devops-helm --create-namespace
helm install myapp k8s/mychart -f k8s/mychart/values-dev.yaml --namespace devops-helm --create-namespace --wait --wait-for-jobs
helm upgrade myapp k8s/mychart -f k8s/mychart/values-prod.yaml --namespace devops-helm --wait --wait-for-jobs
```

Application verification:

For the dev deployment, local access can be checked with:

```bash
kubectl port-forward svc/myapp-mychart 18081:80 -n devops-helm
curl http://localhost:18081/health
```

What was validated:

- Helm CLI installed and working
- public repo exploration completed
- chart structure is valid
- Deployment and Service template correctly from values
- hooks render and execute successfully
- environment-specific values change runtime behavior
- health probes remain active in all rendered manifests

## Notes For Next Labs

The chart keeps helper names under `mychart.*` on purpose, but they are now wrappers around `common-lib`.

Why:

- Labs 11 and 12 already reference helper calls like `include "mychart.fullname" .`
- keeping this naming avoids unnecessary refactors in later labs
- the shared implementation still lives in `common-lib`, so the bonus remains DRY
