# Lab 14 - Progressive Delivery with Argo Rollouts

## Argo Rollouts Setup

Argo Rollouts was installed into the `argo-rollouts` namespace. The controller
manages `Rollout` custom resources and the dashboard is exposed through a
ClusterIP service on port `3100`.

Install commands used:

```powershell
kubectl create namespace argo-rollouts --dry-run=client -o yaml | kubectl apply -f -
kubectl apply -n argo-rollouts -f https://github.com/argoproj/argo-rollouts/releases/latest/download/install.yaml
kubectl apply -n argo-rollouts -f https://github.com/argoproj/argo-rollouts/releases/latest/download/dashboard-install.yaml
kubectl wait --for=condition=Available deployment/argo-rollouts -n argo-rollouts --timeout=180s
```

The `kubectl-argo-rollouts` plugin was installed locally on Windows as
`%USERPROFILE%\bin\kubectl-argo-rollouts.exe`.

Captured runtime evidence excerpt:

```text
COMMAND: kubectl get pods,svc -n argo-rollouts
NAME                                           READY   STATUS    RESTARTS   AGE
pod/argo-rollouts-5cf9b959f9-2cc7n             1/1     Running   0          16m
pod/argo-rollouts-dashboard-7546666c98-49cxv   1/1     Running   0          16m

NAME                              TYPE        CLUSTER-IP     EXTERNAL-IP   PORT(S)    AGE
service/argo-rollouts-dashboard   ClusterIP   10.96.138.60   <none>        3100/TCP   16m
service/argo-rollouts-metrics     ClusterIP   10.96.94.143   <none>        8090/TCP   16m
```

```text
COMMAND: kubectl argo rollouts version
kubectl-argo-rollouts: v1.9.0+838d4e7
  BuildDate: 2026-03-20T21:15:27Z
  GitCommit: 838d4e792be666ec11bd0c80331e0c5511b5010e
  GitTreeState: clean
  GoVersion: go1.24.13
  Compiler: gc
  Platform: windows/amd64
```

Dashboard access:

```powershell
kubectl port-forward svc/argo-rollouts-dashboard -n argo-rollouts 3100:3100
```

Open `http://localhost:3100`.

## Rollout vs Deployment

The Helm chart still supports a normal Kubernetes `Deployment` when
`rollout.enabled=false`. When `rollout.enabled=true`, the chart renders an
Argo `Rollout` instead.

Implemented files:

- [templates/deployment.yaml](./mychart/templates/deployment.yaml) - regular Deployment, disabled when Rollout is enabled
- [templates/rollout.yaml](./mychart/templates/rollout.yaml) - Argo Rollout with canary or blue-green strategy
- [templates/service.yaml](./mychart/templates/service.yaml) - active service
- [templates/preview-service.yaml](./mychart/templates/preview-service.yaml) - blue-green preview service
- [values-rollout-canary.yaml](./mychart/values-rollout-canary.yaml) - canary rollout values
- [values-rollout-bluegreen.yaml](./mychart/values-rollout-bluegreen.yaml) - blue-green rollout values

Key differences:

- `Deployment` supports rolling updates only.
- `Rollout` supports progressive delivery strategies such as canary and blue-green.
- `Rollout` can pause, promote, abort, and undo releases through the Argo Rollouts CLI.
- `Rollout` tracks stable and canary/preview ReplicaSets explicitly.
- Blue-green Rollouts mutate active and preview service selectors, so the Helm service templates preserve existing live selectors with `lookup`.

Template validation excerpt:

```text
COMMAND: helm lint k8s/mychart
==> Linting k8s/mychart
[INFO] Chart.yaml: icon is recommended

1 chart(s) linted, 0 chart(s) failed
```

## Canary Deployment

The canary strategy is configured in
[values-rollout-canary.yaml](./mychart/values-rollout-canary.yaml).

Configuration summary:

- replicas: `5`
- service type: `NodePort`
- NodePort: `30085`
- first step: `20%`
- first pause: manual promotion
- next steps: `40%`, `60%`, `80%`, each with a `30s` pause
- final step: `100%`

Rendered strategy:

```yaml
strategy:
  canary:
    steps:
      - setWeight: 20
      - pause: {}
      - setWeight: 40
      - pause:
          duration: 30s
      - setWeight: 60
      - pause:
          duration: 30s
      - setWeight: 80
      - pause:
          duration: 30s
      - setWeight: 100
```

Install command:

```powershell
helm upgrade --install rollout-canary k8s/mychart `
  -f k8s/mychart/values-rollout-canary.yaml `
  --namespace devops-rollouts `
  --create-namespace
```

Captured initial healthy canary evidence excerpt:

```text
COMMAND: kubectl argo rollouts get rollout rollout-canary-mychart -n devops-rollouts --no-color
Name:            rollout-canary-mychart
Namespace:       devops-rollouts
Status:          ✔ Healthy
Strategy:        Canary
  Step:          9/9
  SetWeight:     100
  ActualWeight:  100
Images:          sfedbro/app_python:lab12 (stable)
Replicas:
  Desired:       5
  Current:       5
  Updated:       5
  Ready:         5
  Available:     5
```

Canary update command:

```powershell
helm upgrade rollout-canary k8s/mychart `
  -f k8s/mychart/values-rollout-canary.yaml `
  --namespace devops-rollouts `
  --set logLevel=warn `
  --set configMap.env.data.LOG_LEVEL=warn
```

The update stopped at the first manual pause with one canary pod and four stable
pods. With five replicas, one updated pod represents the configured `20%`
canary step.

Captured evidence excerpt at the manual `20%` pause:

```text
COMMAND: kubectl argo rollouts get rollout rollout-canary-mychart -n devops-rollouts --no-color
Name:            rollout-canary-mychart
Namespace:       devops-rollouts
Status:          ॥ Paused
Message:         CanaryPauseStep
Strategy:        Canary
  Step:          1/9
  SetWeight:     20
  ActualWeight:  20
Images:          sfedbro/app_python:lab12 (canary, stable)
Replicas:
  Desired:       5
  Current:       5
  Updated:       1
  Ready:         5
  Available:     5
```

Manual promotion command:

```powershell
kubectl argo rollouts promote rollout-canary-mychart -n devops-rollouts
```

Captured promotion evidence excerpt:

```text
COMMAND: kubectl argo rollouts promote rollout-canary-mychart -n devops-rollouts
rollout 'rollout-canary-mychart' promoted

COMMAND: kubectl argo rollouts status rollout-canary-mychart -n devops-rollouts --timeout 180s
Progressing - more replicas need to be updated
Paused - CanaryPauseStep
Progressing - more replicas need to be updated
Paused - CanaryPauseStep
Progressing - more replicas need to be updated
Paused - CanaryPauseStep
Progressing - more replicas need to be updated
Progressing - updated replicas are still becoming available
Progressing - waiting for all steps to complete
Healthy
```

Captured evidence excerpt after automatic `40/60/80/100` progression:

```text
COMMAND: kubectl argo rollouts get rollout rollout-canary-mychart -n devops-rollouts --no-color
Name:            rollout-canary-mychart
Namespace:       devops-rollouts
Status:          ✔ Healthy
Strategy:        Canary
  Step:          9/9
  SetWeight:     100
  ActualWeight:  100
Images:          sfedbro/app_python:lab12 (stable)
Replicas:
  Desired:       5
  Current:       5
  Updated:       5
  Ready:         5
  Available:     5
```

Abort test:

```powershell
helm upgrade rollout-canary k8s/mychart `
  -f k8s/mychart/values-rollout-canary.yaml `
  --namespace devops-rollouts `
  --set logLevel=error `
  --set configMap.env.data.LOG_LEVEL=error

kubectl argo rollouts abort rollout-canary-mychart -n devops-rollouts
```

Captured abort evidence excerpt:

```text
COMMAND: kubectl argo rollouts abort rollout-canary-mychart -n devops-rollouts
rollout 'rollout-canary-mychart' aborted

COMMAND: kubectl argo rollouts get rollout rollout-canary-mychart -n devops-rollouts --no-color
Name:            rollout-canary-mychart
Namespace:       devops-rollouts
Status:          ✖ Degraded
Message:         RolloutAborted: Rollout aborted update to revision 3
Strategy:        Canary
  Step:          0/9
  SetWeight:     0
  ActualWeight:  0
Images:          sfedbro/app_python:lab12 (stable)
Replicas:
  Desired:       5
  Current:       5
  Updated:       0
```

The aborted canary ReplicaSet was scaled down and traffic returned to the stable
ReplicaSet. The rollout was then restored to a healthy stable revision:

```text
COMMAND: kubectl argo rollouts undo rollout-canary-mychart -n devops-rollouts
rollout 'rollout-canary-mychart' undo

COMMAND: kubectl argo rollouts get rollout rollout-canary-mychart -n devops-rollouts --no-color
Name:            rollout-canary-mychart
Namespace:       devops-rollouts
Status:          ✔ Healthy
Strategy:        Canary
  Step:          9/9
  SetWeight:     100
  ActualWeight:  100
Replicas:
  Desired:       5
  Current:       5
  Updated:       5
  Ready:         5
  Available:     5
```

## Blue-Green Deployment

The blue-green strategy is configured in
[values-rollout-bluegreen.yaml](./mychart/values-rollout-bluegreen.yaml).

Configuration summary:

- replicas: `3`
- active service: `rollout-bluegreen-mychart`
- preview service: `rollout-bluegreen-mychart-preview`
- `autoPromotionEnabled: false`
- `scaleDownDelaySeconds: 30`
- service type: `ClusterIP`

Rendered strategy:

```yaml
strategy:
  blueGreen:
    activeService: rollout-bluegreen-mychart
    previewService: rollout-bluegreen-mychart-preview
    autoPromotionEnabled: false
    scaleDownDelaySeconds: 30
```

Install command:

```powershell
helm upgrade --install rollout-bluegreen k8s/mychart `
  -f k8s/mychart/values-rollout-bluegreen.yaml `
  --namespace devops-rollouts `
  --create-namespace
```

Update command:

```powershell
helm upgrade rollout-bluegreen k8s/mychart `
  -f k8s/mychart/values-rollout-bluegreen.yaml `
  --namespace devops-rollouts `
  --set logLevel=debug `
  --set configMap.env.data.LOG_LEVEL=debug
```

Captured preview waiting evidence excerpt:

```text
COMMAND: kubectl argo rollouts get rollout rollout-bluegreen-mychart -n devops-rollouts --no-color
Name:            rollout-bluegreen-mychart
Namespace:       devops-rollouts
Status:          ॥ Paused
Message:         BlueGreenPause
Strategy:        BlueGreen
Images:          sfedbro/app_python:lab12 (active, preview, stable)
Replicas:
  Desired:       3
  Current:       6
  Updated:       3
  Ready:         3
  Available:     3
```

Before promotion, the active service selected the stable ReplicaSet and the
preview service selected the new ReplicaSet:

```text
COMMAND: kubectl get svc -n devops-rollouts rollout-bluegreen-mychart rollout-bluegreen-mychart-preview -o wide
NAME                                TYPE        CLUSTER-IP     EXTERNAL-IP   PORT(S)   AGE   SELECTOR
rollout-bluegreen-mychart           ClusterIP   10.96.128.2    <none>        80/TCP    92s   app.kubernetes.io/instance=rollout-bluegreen,app.kubernetes.io/name=mychart,rollouts-pod-template-hash=7988cbf8d6
rollout-bluegreen-mychart-preview   ClusterIP   10.96.229.42   <none>        80/TCP    92s   app.kubernetes.io/instance=rollout-bluegreen,app.kubernetes.io/name=mychart,rollouts-pod-template-hash=56cbc5dbb
```

Promotion command:

```powershell
kubectl argo rollouts promote rollout-bluegreen-mychart -n devops-rollouts
```

After promotion, the active service switched to the new ReplicaSet hash:

```text
COMMAND: kubectl argo rollouts promote rollout-bluegreen-mychart -n devops-rollouts
rollout 'rollout-bluegreen-mychart' promoted

COMMAND: kubectl get svc -n devops-rollouts rollout-bluegreen-mychart rollout-bluegreen-mychart-preview -o wide
NAME                                TYPE        CLUSTER-IP     EXTERNAL-IP   PORT(S)   AGE    SELECTOR
rollout-bluegreen-mychart           ClusterIP   10.96.128.2    <none>        80/TCP    103s   app.kubernetes.io/instance=rollout-bluegreen,app.kubernetes.io/name=mychart,rollouts-pod-template-hash=56cbc5dbb
rollout-bluegreen-mychart-preview   ClusterIP   10.96.229.42   <none>        80/TCP    103s   app.kubernetes.io/instance=rollout-bluegreen,app.kubernetes.io/name=mychart,rollouts-pod-template-hash=56cbc5dbb
```

Rollback command:

```powershell
kubectl argo rollouts undo rollout-bluegreen-mychart -n devops-rollouts
```

Captured rollback evidence excerpt:

```text
COMMAND: kubectl argo rollouts undo rollout-bluegreen-mychart -n devops-rollouts
rollout 'rollout-bluegreen-mychart' undo

COMMAND: kubectl argo rollouts get rollout rollout-bluegreen-mychart -n devops-rollouts --no-color
Name:            rollout-bluegreen-mychart
Namespace:       devops-rollouts
Status:          ✔ Healthy
Strategy:        BlueGreen
Images:          sfedbro/app_python:lab12 (active, stable)
Replicas:
  Desired:       3
  Current:       6
  Updated:       3
  Ready:         3
  Available:     3

NAME                                                   KIND        STATUS     AGE   INFO
⟳ rollout-bluegreen-mychart                            Rollout     ✔ Healthy  113s
├──# revision:3
│  └──⧉ rollout-bluegreen-mychart-7988cbf8d6           ReplicaSet  ✔ Healthy  113s  stable,active
└──# revision:2
   └──⧉ rollout-bluegreen-mychart-56cbc5dbb            ReplicaSet  ✔ Healthy  100s  delay:19s
```

## Strategy Comparison

Canary is best when:

- changes are risky and should be exposed gradually
- there is enough traffic to evaluate behavior at partial rollout stages
- slow rollout is acceptable
- partial blast radius is more important than instant switching

Blue-green is best when:

- the new version needs a full preview environment before production traffic
- rollback must be an instant service selector switch
- the cluster can temporarily run both old and new ReplicaSets
- all-or-nothing cutover is acceptable

Tradeoffs:

- Canary uses less extra capacity than blue-green but rollback is progressive and the service may temporarily send traffic to mixed versions.
- Blue-green gives the cleanest cutover and rollback behavior but temporarily doubles application capacity requirements.
- For this app, canary is safer for normal feature releases, while blue-green is better for config/schema-sensitive changes that must be tested through a preview service before switching active traffic.

## CLI Commands Reference

Controller and dashboard:

```powershell
kubectl get pods,svc -n argo-rollouts
kubectl argo rollouts version
kubectl port-forward svc/argo-rollouts-dashboard -n argo-rollouts 3100:3100
```

Render and validate:

```powershell
helm lint k8s/mychart
helm template rollout-canary k8s/mychart -f k8s/mychart/values-rollout-canary.yaml --namespace devops-rollouts
helm template rollout-bluegreen k8s/mychart -f k8s/mychart/values-rollout-bluegreen.yaml --namespace devops-rollouts
```

Canary:

```powershell
helm upgrade --install rollout-canary k8s/mychart -f k8s/mychart/values-rollout-canary.yaml --namespace devops-rollouts --create-namespace
kubectl argo rollouts get rollout rollout-canary-mychart -n devops-rollouts --watch
kubectl argo rollouts promote rollout-canary-mychart -n devops-rollouts
kubectl argo rollouts abort rollout-canary-mychart -n devops-rollouts
kubectl argo rollouts undo rollout-canary-mychart -n devops-rollouts
```

Blue-green:

```powershell
helm upgrade --install rollout-bluegreen k8s/mychart -f k8s/mychart/values-rollout-bluegreen.yaml --namespace devops-rollouts --create-namespace
kubectl get svc -n devops-rollouts rollout-bluegreen-mychart rollout-bluegreen-mychart-preview -o wide
kubectl argo rollouts promote rollout-bluegreen-mychart -n devops-rollouts
kubectl argo rollouts undo rollout-bluegreen-mychart -n devops-rollouts
```

Troubleshooting notes:

- Avoid relying only on `helm --wait` for paused Rollout resources. A paused canary or blue-green rollout can make Helm wait until timeout even though the rollout is behaving correctly.
- Use `kubectl argo rollouts get rollout ...` as the source of truth for Rollout phase, current step, stable ReplicaSet, canary ReplicaSet, and preview ReplicaSet.
- For blue-green, Argo Rollouts owns the active/preview service selectors after installation. The chart uses `lookup` to avoid Helm fighting controller-managed selector changes.

## Dashboard Screenshots

Screenshots were captured from the local Argo Rollouts dashboard at
`http://localhost:3100/rollouts/devops-rollouts`.

Captured screenshots:

- [lab14_1_dashboard-rollouts.png](./docs/screenshots/lab14_1_dashboard-rollouts.png) - namespace `devops-rollouts` with both `rollout-canary-mychart` and `rollout-bluegreen-mychart`.
- [lab14_2_canary-rollout.png](./docs/screenshots/lab14_2_canary-rollout.png) - canary rollout details and ReplicaSet revisions.
- [lab14_3_bluegreen-rollout.png](./docs/screenshots/lab14_3_bluegreen-rollout.png) - blue-green rollout details and active/stable ReplicaSet.

Rollback evidence is captured in the CLI output above: the canary abort shows
`RolloutAborted`, and the blue-green rollback shows `revision:3` returned to the
previous ReplicaSet as `stable,active`.

Raw command output is also saved in:

- [lab14_setup_runtime.txt](./docs/lab14_setup_runtime.txt)
- [lab14_runtime_continue.txt](./docs/lab14_runtime_continue.txt)
- [lab14_bluegreen_runtime_fixed.txt](./docs/lab14_bluegreen_runtime_fixed.txt)
