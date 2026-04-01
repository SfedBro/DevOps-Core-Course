# Lab 09 - Kubernetes Fundamentals

## Architecture Overview

The application is deployed into a dedicated namespace `devops-lab9`.

Traffic flow:

```text
Client -> NodePort Service (port 30080 on node) -> Deployment -> 3 Pods -> container port 5000
```

Resources used:

- `Namespace` for logical isolation
- `Deployment` with 3 replicas for high availability
- `Service` of type `NodePort` for local cluster access

Resource strategy:

- requests are set low enough for local clusters
- limits protect the node from runaway resource usage
- liveness and readiness probes both use `/health`

## Manifest Files

- [namespace.yml](./namespace.yml)
  Creates isolated namespace `devops-lab9`.

- [deployment.yml](./deployment.yml)
  Deploys `sfedbro/app_python:latest` with:
  - 3 replicas
  - rolling update strategy
  - readiness and liveness probes
  - CPU and memory requests/limits
  - non-root container security settings

- [service.yml](./service.yml)
  Exposes the Deployment through a `NodePort` Service on node port `30080`.

Key choices:

- `replicas: 3` satisfies the lab minimum and demonstrates redundancy.
- `maxUnavailable: 0` keeps the service available during rolling updates.
- `readinessProbe` prevents traffic from reaching unready Pods.
- `livenessProbe` ensures Kubernetes restarts unhealthy Pods.
- `NodePort` is used because the lab targets local clusters without cloud load balancers.

## Deployment Evidence

This repository contains the manifests, documentation, and runtime evidence captured from the local `kind` cluster.

Current evidence already captured:

- `kubectl cluster-info`
- `kubectl get nodes`
- `kubectl get pods,svc -n devops-lab9 -o wide`
- `kubectl get all -n devops-lab9`
- `kubectl describe deployment devops-info-service -n devops-lab9`
- scaling output for 5 replicas
- rollout history and rollback output
- curl output showing the app working through port-forward
- screenshot: [lab09_get-nodes-pods.png](./docs/screenshots/lab09_get-nodes-pods.png)
- screenshot: [lab09_kubectl-get.png](./docs/screenshots/lab09_kubectl-get.png)
- screenshot: [lab09_endpoints-respond.png](./docs/screenshots/lab09_endpoints-respond.png)
- screenshot: [lab09_scalability.png](./docs/screenshots/lab09_scalability.png)
- screenshot: [lab09_scale-rollback-2.png](./docs/screenshots/lab09_scale-rollback-2.png)

Recommended commands to capture evidence:

```bash
kubectl get all -n devops-lab9
kubectl get pods,svc -n devops-lab9 -o wide
kubectl describe deployment devops-info-service -n devops-lab9
kubectl logs deployment/devops-info-service -n devops-lab9
```

## Operations Performed

### 1. Create local cluster

Chosen tool: `kind`

Why:
- works well with Docker Desktop on this machine
- lightweight local cluster for iterative testing
- good fit for local Kubernetes labs without needing a separate VM

```bash
kind create cluster --name lab09 --image kindest/node:v1.34.0
```

### 2. Verify cluster

```bash
kubectl cluster-info
kubectl get nodes
kubectl get namespaces
```

### 3. Apply manifests

```bash
kubectl apply -f k8s/namespace.yml
kubectl apply -f k8s/deployment.yml
kubectl apply -f k8s/service.yml
```

### 4. Verify rollout

```bash
kubectl rollout status deployment/devops-info-service -n devops-lab9
kubectl get pods -n devops-lab9
kubectl get svc -n devops-lab9
```

### 5. Access service

For minikube:

```bash
minikube service devops-info-service -n devops-lab9 --url
```

For kind or generic local setup:

```bash
kubectl port-forward service/devops-info-service 18081:80 -n devops-lab9
curl http://localhost:18081/
curl http://localhost:18081/health
```

### 6. Scale to 5 replicas

Commands:

```bash
kubectl scale deployment devops-info-service --replicas=5 -n devops-lab9
kubectl get pods -n devops-lab9
kubectl rollout status deployment/devops-info-service -n devops-lab9
```

### 7. Rolling update

Safe demo option without changing the image:

```bash
kubectl set env deployment/devops-info-service LAB09_ROLLOUT=demo -n devops-lab9
kubectl rollout status deployment/devops-info-service -n devops-lab9
kubectl rollout history deployment/devops-info-service -n devops-lab9
```

### 8. Rollback

```bash
kubectl rollout undo deployment/devops-info-service -n devops-lab9
kubectl rollout status deployment/devops-info-service -n devops-lab9
kubectl rollout history deployment/devops-info-service -n devops-lab9
```

Optional cleanup after scaling demo:

```bash
kubectl scale deployment devops-info-service --replicas=3 -n devops-lab9
kubectl rollout status deployment/devops-info-service -n devops-lab9
```

## Production Considerations

Health checks:

- `/health` is used for both readiness and liveness because the app already exposes a stable health endpoint.
- readiness starts earlier than liveness so traffic can be gated before restart logic kicks in.

Resource limits:

- requests:
  - CPU `100m`
  - memory `128Mi`
- limits:
  - CPU `250m`
  - memory `256Mi`

Why:

- reasonable for a lightweight local FastAPI service
- enough for local Kubernetes scheduling
- prevents one Pod from consuming excessive resources

What I would improve for production:

- use pinned immutable image tags instead of `latest`
- add HPA based on CPU or custom metrics
- use Ingress instead of plain NodePort
- add PodDisruptionBudget and anti-affinity
- externalize configuration with ConfigMaps/Secrets
- integrate Prometheus and Loki dashboards from Labs 7-8

Monitoring strategy:

- metrics via Prometheus
- logs via Loki
- dashboards via Grafana
- readiness/liveness provide platform-level health visibility

## Challenges & Solutions

1. Kubernetes manifests need clear label consistency.
   Solution:
   The Deployment selector and Service selector both use `app: devops-info-service`.

2. Rolling updates can cause downtime if Pods are removed too aggressively.
   Solution:
   `maxUnavailable: 0` and readiness probes were configured.

3. Local clusters differ by tool.
   Solution:
   The lab documentation includes both `minikube` and `kind` access patterns.

4. Image availability may differ across environments.
   Solution:
   The manifest uses Docker Hub image `sfedbro/app_python:latest`; if another tag is available, update the image field before applying.

## Current Status

The local Kubernetes cluster is running with `kind`, and the manifests are applied successfully.

Current runtime status:

- namespace `devops-lab9` created
- Deployment available with `3/3` replicas
- Service defined as `NodePort` on `30080`
- Application verified locally through `kubectl port-forward` on `localhost:18081`
- scaling to `5` replicas demonstrated
- rollout history and rollback demonstrated

Why both `30080` and `18081` appear:

- `30080` is the actual Kubernetes `NodePort` configured in [service.yml](./service.yml)
- `18081` is only the local port used for `kubectl port-forward` on the Windows host
- they are different access methods and do not conflict with each other
