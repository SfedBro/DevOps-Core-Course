# Lab 13 - ArgoCD GitOps

## Overview

This lab deploys the existing Helm chart from [mychart](./mychart) through
ArgoCD and verifies GitOps behavior on the local `kind-lab09` cluster.

Prepared manifests:

- [install-values.yaml](./argocd/install-values.yaml)
- [namespaces.yaml](./argocd/namespaces.yaml)
- [application.yaml](./argocd/application.yaml)
- [application-dev.yaml](./argocd/application-dev.yaml)
- [application-prod.yaml](./argocd/application-prod.yaml)
- [applicationset.yaml](./argocd/applicationset.yaml)

Runtime evidence:

- [lab13_runtime.txt](./docs/lab13_runtime.txt)

Repository source used by ArgoCD:

- `repoURL`: `https://github.com/SfedBro/DevOps-Core-Course.git`
- `targetRevision`: `lab13`
- `path`: `k8s/mychart`

Current Git revision verified in the cluster:

- `e903808133af42f46c3a2c4302e2d268f4a6dfed`

Before applying these manifests, the branch must be pushed:

```powershell
git push -u origin lab13
```

Without that push, ArgoCD cannot fetch the `lab13` revision from GitHub.

## ArgoCD Setup

Install ArgoCD with Helm:

```powershell
helm repo add argo https://argoproj.github.io/argo-helm
helm repo update
helm upgrade --install argocd argo/argo-cd `
  --namespace argocd `
  --create-namespace `
  -f k8s/argocd/install-values.yaml
kubectl wait --for=condition=Ready pod -l app.kubernetes.io/part-of=argocd -n argocd --timeout=180s
```

The custom values in [install-values.yaml](./argocd/install-values.yaml):

- keep `argocd-server` as `ClusterIP`
- enable `server.insecure`
- relax `repoServer` probes and resource requests for the local `kind` cluster

Access the UI:

```powershell
kubectl port-forward -n argocd svc/argocd-server 8080:80
```

Then open `http://127.0.0.1:8080`.

Retrieve the initial admin password:

```powershell
$ARGOCD_PASSWORD = [System.Text.Encoding]::UTF8.GetString(
  [System.Convert]::FromBase64String(
    (kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath='{.data.password}')
  )
)
$ARGOCD_PASSWORD
```

Install the CLI on Windows:

```powershell
winget install --id argoproj.argocd -e
argocd version --client
```

CLI login command for this setup:

```powershell
argocd login 127.0.0.1:8080 --username admin --password $ARGOCD_PASSWORD --plaintext --grpc-web
```

Observed setup state:

- ArgoCD Helm release is installed in namespace `argocd`
- all ArgoCD pods are `Running`
- local CLI version is `v3.3.8+7ae7d2c`
- Windows port-forward plus CLI login was unstable in this environment, so live
  sync and health checks were verified primarily through Kubernetes
  `Application` resources

Evidence:

```text
COMMAND: kubectl get pods -n argocd
NAME                                               READY   STATUS    RESTARTS   AGE
argocd-application-controller-0                    1/1     Running   0          57m
argocd-applicationset-controller-8dc7d4cb-ntk9m    1/1     Running   0          57m
argocd-dex-server-84878c988d-rthtj                 1/1     Running   0          57m
argocd-notifications-controller-6f8f8b54f8-gg578   1/1     Running   0          57m
argocd-redis-65f4b95795-mfncc                      1/1     Running   0          57m
argocd-repo-server-64894d6d97-45p4f                1/1     Running   0          48m
argocd-server-75cd4cd976-5lpjv                     1/1     Running   0          57m
```

## Application Configuration

### Single application

The base manifest [application.yaml](./argocd/application.yaml) deploys
`k8s/mychart` into namespace `devops-gitops`.

Key settings:

- Helm release name: `python-app`
- values file: `values.yaml`
- destination namespace: `devops-gitops`
- sync policy: manual
- overrides:
  - `service.type=ClusterIP`
  - `persistence.hostPath.path=/var/local/devops-info-service-gitops`

Apply it:

```powershell
kubectl apply -f k8s/argocd/namespaces.yaml
kubectl apply -f k8s/argocd/application.yaml
```

Manual sync can be triggered from the UI or by patching the `Application`
operation in Kubernetes.

### Multi-environment

The dev and prod environments use separate `Application` resources:

- [application-dev.yaml](./argocd/application-dev.yaml)
- [application-prod.yaml](./argocd/application-prod.yaml)

Apply both:

```powershell
kubectl apply -f k8s/argocd/namespaces.yaml
kubectl apply -f k8s/argocd/application-dev.yaml
kubectl apply -f k8s/argocd/application-prod.yaml
```

Environment differences:

| Environment | Values file | Namespace | Replicas | Service type | Extra overrides | Sync policy |
|-------------|-------------|-----------|----------|--------------|-----------------|-------------|
| dev | `values-dev.yaml` | `dev` | 1 | `NodePort` | `service.nodePort=30083`, dedicated hostPath | automated + prune + selfHeal |
| prod | `values-prod.yaml` | `prod` | 3 | `ClusterIP` | `service.type=ClusterIP`, dedicated hostPath | manual |

Why prod stays manual:

- controlled rollout timing
- explicit review before deployment
- safer production change management
- easier rollback planning

Observed application state:

```text
COMMAND: kubectl get applications -n argocd -o wide
NAME              SYNC STATUS   HEALTH STATUS   REVISION                                   PROJECT
python-app        Synced        Healthy         e903808133af42f46c3a2c4302e2d268f4a6dfed   default
python-app-dev    Synced        Healthy         e903808133af42f46c3a2c4302e2d268f4a6dfed   default
python-app-prod   Synced        Healthy         e903808133af42f46c3a2c4302e2d268f4a6dfed   default
```

Observed runtime resources:

```text
COMMAND: kubectl get deploy,svc in dev, prod, devops-gitops
deployment.apps/python-app-dev-mychart   1/1   1   1
service/python-app-dev-mychart           NodePort   80:30083/TCP

deployment.apps/python-app-prod-mychart  3/3   3   3
service/python-app-prod-mychart          ClusterIP  80/TCP

deployment.apps/python-app-mychart       3/3   3   3
service/python-app-mychart               ClusterIP  80/TCP
```

Application access was verified through a local port-forward to the dev service:

```powershell
kubectl port-forward -n dev svc/python-app-dev-mychart 18083:80
curl.exe -s http://127.0.0.1:18083/health
curl.exe -s http://127.0.0.1:18083/visits
```

Observed result:

```text
HEALTH={"status":"healthy","timestamp":"2026-04-22T22:40:36.582501+00:00","uptime_seconds":1677}
VISITS={"visits":0,"file":"/data/visits"}
```

## GitOps Workflow

The intended GitOps flow is:

1. Change the chart or values in Git.
2. Commit the change.
3. Push to `origin/lab13`.
4. ArgoCD detects the new revision.
5. Dev auto-syncs.
6. Prod stays manual until explicitly synced.

Example:

```powershell
git add k8s/mychart/values-dev.yaml
git commit -m "lab13: change dev replicas"
git push
```

What is verified in this cluster:

- ArgoCD is tracking branch `lab13`
- all three applications currently point to Git revision
  `e903808133af42f46c3a2c4302e2d268f4a6dfed`
- dev and prod are split into separate namespaces and separate `Application`
  resources

## Self-Healing Evidence

### Manual scale drift

Dev uses `automated.prune=true` and `selfHeal=true`, so it should reconcile
back to the Git-defined replica count.

Test:

```powershell
kubectl scale deployment python-app-dev-mychart -n dev --replicas=5
```

Observed result:

```text
before:
replicas=1
sync=Synced health=Healthy

after manual scale:
replicas=5
sync=Synced health=Healthy

after self-heal window:
replicas=1
sync=Synced health=Healthy
```

Important nuance:

- during the short observation window, `Application.status.sync.status` did not
  flip to `OutOfSync`
- however, the deployment spec was reconciled from `5` back to `1`, which is
  the actual Git-defined desired state from `values-dev.yaml`

### Pod deletion test

Test:

```powershell
kubectl delete pod -n dev -l app.kubernetes.io/instance=python-app-dev
```

Observed result:

```text
deleted pod:
python-app-dev-mychart-56ff9856f7-k2dqh

new pod list:
python-app-dev-mychart-56ff9856f7-hrgqc    Running
python-app-dev-mychart-pre-install-fgs5c   Completed
```

This is Kubernetes self-healing, not ArgoCD:

- Deployment or ReplicaSet restores the pod count
- ArgoCD is not required to recreate a deleted pod when the deployment already
  defines the desired replica count

### Configuration drift test

Test:

```powershell
kubectl label deployment python-app-dev-mychart -n dev drift=manual --overwrite
```

Observed result:

```text
drift=manual
sync=Synced
```

The manual label remained present during the observation window and was cleaned
up manually afterward. I am not claiming that this metadata-only drift
auto-healed in this run.

Difference between healing mechanisms:

- Kubernetes self-healing: recreates deleted or failed pods to satisfy the live
  Deployment or ReplicaSet
- ArgoCD self-healing: reconciles declarative cluster state back to Git

What triggers ArgoCD sync:

- a new Git revision
- manual sync from UI or CLI
- webhook-triggered refresh
- live-state drift when auto-sync and self-heal are enabled

Reconciliation behavior:

- ArgoCD polls Git periodically
- in this chart setup the configured reconciliation timeout is `120s` with
  jitter `60s`

## Bonus - ApplicationSet

The bonus manifest [applicationset.yaml](./argocd/applicationset.yaml) is
implemented with a List generator.

Implemented details:

- generator elements for `dev` and `prod`
- `goTemplate: true`
- `missingkey=error`
- `templatePatch` to enable automated sync only for `dev`
- `prod` remains manual

Validation performed:

```text
COMMAND: kubectl apply --dry-run=server -f k8s/argocd/applicationset.yaml
applicationset.argoproj.io/python-app-set created (server dry run)
```

Benefits of the ApplicationSet approach:

- less duplicated YAML
- one template for multiple environments
- simpler scaling to more environments or clusters
- better consistency for naming and destination rules

Practical note:

- the core lab was kept on individual `Application` resources because they were
  already deployed and healthy
- if you want to claim the bonus rigorously, replace the live dev/prod
  applications with the ApplicationSet and capture evidence of the generated
  applications in the ArgoCD UI

## Raw Evidence

This section embeds the live command output directly in the Markdown file.
The same data is also stored in [lab13_runtime.txt](./docs/lab13_runtime.txt).

```text
Lab 13 runtime evidence - 2026-04-23T01:40:30

=== Git revision ===
COMMAND: git rev-parse HEAD
e903808133af42f46c3a2c4302e2d268f4a6dfed


=== ArgoCD CLI version ===
COMMAND: argocd version --client
argocd: v3.3.8+7ae7d2c
  BuildDate: 2026-04-21T17:45:55Z
  GitCommit: 7ae7d2cc723f5408b080a31263e705198af08613
  GitTreeState: clean
  GoVersion: go1.25.5
  Compiler: gc
  Platform: windows/amd64


=== ArgoCD applications ===
COMMAND: kubectl get applications -n argocd -o wide
NAME              SYNC STATUS   HEALTH STATUS   REVISION                                   PROJECT
python-app        Synced        Healthy         e903808133af42f46c3a2c4302e2d268f4a6dfed   default
python-app-dev    Synced        Healthy         e903808133af42f46c3a2c4302e2d268f4a6dfed   default
python-app-prod   Synced        Healthy         e903808133af42f46c3a2c4302e2d268f4a6dfed   default


=== Argocd pods ===
COMMAND: kubectl get pods -n argocd
NAME                                               READY   STATUS    RESTARTS   AGE
argocd-application-controller-0                    1/1     Running   0          57m
argocd-applicationset-controller-8dc7d4cb-ntk9m    1/1     Running   0          57m
argocd-dex-server-84878c988d-rthtj                 1/1     Running   0          57m
argocd-notifications-controller-6f8f8b54f8-gg578   1/1     Running   0          57m
argocd-redis-65f4b95795-mfncc                      1/1     Running   0          57m
argocd-repo-server-64894d6d97-45p4f                1/1     Running   0          48m
argocd-server-75cd4cd976-5lpjv                     1/1     Running   0          57m


=== Environment deployments and services ===
COMMAND: kubectl get deploy,svc in dev, prod, devops-gitops
NAME                                     READY   UP-TO-DATE   AVAILABLE   AGE
deployment.apps/python-app-dev-mychart   1/1     1            1           47m

NAME                             TYPE       CLUSTER-IP     EXTERNAL-IP   PORT(S)        AGE
service/python-app-dev-mychart   NodePort   10.96.92.165   <none>        80:30083/TCP   47m

NAME                                      READY   UP-TO-DATE   AVAILABLE   AGE
deployment.apps/python-app-prod-mychart   3/3     3            3           36m

NAME                              TYPE        CLUSTER-IP      EXTERNAL-IP   PORT(S)   AGE
service/python-app-prod-mychart   ClusterIP   10.96.169.234   <none>        80/TCP    36m

NAME                                 READY   UP-TO-DATE   AVAILABLE   AGE
deployment.apps/python-app-mychart   3/3     3            3           44m

NAME                         TYPE        CLUSTER-IP     EXTERNAL-IP   PORT(S)   AGE
service/python-app-mychart   ClusterIP   10.96.96.228   <none>        80/TCP    44m


=== App access via port-forward ===
COMMAND: kubectl port-forward -n dev svc/python-app-dev-mychart 18083:80; curl /health; curl /visits
HEALTH={"status":"healthy","timestamp":"2026-04-22T22:40:36.582501+00:00","uptime_seconds":1677}
VISITS={"visits":0,"file":"/data/visits"}


=== Self-heal before scale ===
COMMAND: kubectl get deployment and application status before scale
replicas=1
sync=Synced health=Healthy


=== Manual scale drift ===
COMMAND: kubectl scale deployment python-app-dev-mychart -n dev --replicas=5
deployment.apps/python-app-dev-mychart scaled


=== Status after manual scale ===
COMMAND: kubectl get deployment and application status after manual scale
replicas=5
sync=Synced health=Healthy


=== Status after self-heal window ===
COMMAND: kubectl get deployment and application status after waiting for self-heal
replicas=1
sync=Synced health=Healthy


=== Pod before deletion ===
COMMAND: kubectl get pod in dev before deletion
python-app-dev-mychart-56ff9856f7-k2dqh


=== Delete pod ===
COMMAND: kubectl delete pod python-app-dev-mychart-56ff9856f7-k2dqh -n dev
pod "python-app-dev-mychart-56ff9856f7-k2dqh" deleted from dev namespace


=== Pod after recreation ===
COMMAND: kubectl get pods -n dev -l app.kubernetes.io/instance=python-app-dev
NAME                                       READY   STATUS      RESTARTS   AGE
python-app-dev-mychart-56ff9856f7-hrgqc    0/1     Running     0          5s
python-app-dev-mychart-pre-install-fgs5c   0/1     Completed   0          16s


=== Manual label drift ===
COMMAND: kubectl label deployment python-app-dev-mychart -n dev drift=manual --overwrite
deployment.apps/python-app-dev-mychart not labeled


=== Label drift immediate status ===
COMMAND: kubectl get deployment label drift and application sync status
drift=manual
sync=Synced


=== Label drift after self-heal window ===
COMMAND: kubectl get deployment label drift and application sync status after wait
drift=manual
sync=Synced


=== ApplicationSet validation ===
COMMAND: kubectl apply --dry-run=server -f k8s/argocd/applicationset.yaml
applicationset.argoproj.io/python-app-set created (server dry run)
```

## Screenshots

These screenshots are still manual and should be captured from the real ArgoCD
UI:

- application list showing `python-app-dev` and `python-app-prod`
- details page for `python-app-dev`
- sync history, diff view, or health view showing reconciliation

Suggested location:

- `k8s/docs/screenshots/`
