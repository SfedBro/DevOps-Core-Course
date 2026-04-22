# Lab 13 - ArgoCD GitOps

## Overview

This lab adds GitOps deployment for the existing Helm chart in [mychart](./mychart).

Prepared artifacts:

- [argocd/install-values.yaml](./argocd/install-values.yaml)
- [argocd/namespaces.yaml](./argocd/namespaces.yaml)
- [argocd/application.yaml](./argocd/application.yaml)
- [argocd/application-dev.yaml](./argocd/application-dev.yaml)
- [argocd/application-prod.yaml](./argocd/application-prod.yaml)
- [argocd/applicationset.yaml](./argocd/applicationset.yaml)

Repository source used by ArgoCD:

- `repoURL`: `https://github.com/SfedBro/DevOps-Core-Course.git`
- `targetRevision`: `lab13`
- `path`: `k8s/mychart`

Important prerequisite:

- push the current branch before applying ArgoCD manifests:

```powershell
git push -u origin lab13
```

Without that push, ArgoCD cannot fetch the `lab13` revision from GitHub.

## ArgoCD Setup

Local environment note:

- on 2026-04-23 the configured Kubernetes context was `kind-lab09`
- the API endpoint `https://127.0.0.1:2068` was unavailable because the local Docker daemon was not running
- because of that, the repository setup and runbook are complete, but live sync evidence and screenshots must be regenerated after restarting Docker Desktop and the cluster

Install ArgoCD via Helm:

```powershell
helm repo add argo https://argoproj.github.io/argo-helm
helm repo update
helm upgrade --install argocd argo/argo-cd `
  --namespace argocd `
  --create-namespace `
  -f k8s/argocd/install-values.yaml
kubectl wait --for=condition=Ready pod -l app.kubernetes.io/part-of=argocd -n argocd --timeout=180s
```

The custom install values keep the server behind a `ClusterIP` service and enable insecure mode for simple local port-forwarding.

Access the UI:

```powershell
kubectl port-forward svc/argocd-server -n argocd 8080:80
```

Then open `http://localhost:8080`.

Retrieve the initial admin password in PowerShell:

```powershell
$ARGOCD_PASSWORD = [System.Text.Encoding]::UTF8.GetString(
  [System.Convert]::FromBase64String(
    (kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath='{.data.password}')
  )
)
$ARGOCD_PASSWORD
```

Install and configure the CLI on Windows:

```powershell
winget install --id argoproj.argocd -e
argocd login localhost:8080 --username admin --password $ARGOCD_PASSWORD --insecure
argocd app list
```

Verification checklist after startup:

- `kubectl get pods -n argocd`
- `argocd version`
- `argocd app list`

## Application Configuration

### Single application

The base manifest [argocd/application.yaml](./argocd/application.yaml) deploys the chart with `values.yaml` into namespace `devops-gitops`.

Apply and sync:

```powershell
kubectl apply -f k8s/argocd/application.yaml
argocd app get python-app
argocd app sync python-app
argocd app wait python-app --health --sync
```

What this manifest defines:

- source repo: this GitHub repository
- chart path: `k8s/mychart`
- Helm release name: `python-app`
- destination namespace: `devops-gitops`
- sync policy: manual

### Multi-environment

The dev/prod setup uses separate ArgoCD `Application` resources:

- [argocd/application-dev.yaml](./argocd/application-dev.yaml)
- [argocd/application-prod.yaml](./argocd/application-prod.yaml)

Create namespaces and apply both applications:

```powershell
kubectl apply -f k8s/argocd/namespaces.yaml
kubectl apply -f k8s/argocd/application-dev.yaml
kubectl apply -f k8s/argocd/application-prod.yaml
```

Environment differences:

| Environment | Values file | Namespace | Replicas | Service type | Sync policy |
|-------------|-------------|-----------|----------|--------------|-------------|
| dev | `values-dev.yaml` | `dev` | 1 | `NodePort` | auto-sync + prune + self-heal |
| prod | `values-prod.yaml` | `prod` | 3 | `LoadBalancer` | manual |

Why prod stays manual:

- explicit review before rollout
- controlled deployment timing
- safer rollback planning
- avoids applying unreviewed commits directly to production

Verify both environments:

```powershell
argocd app list
argocd app get python-app-dev
argocd app get python-app-prod
kubectl get pods -n dev
kubectl get pods -n prod
```

## GitOps Workflow

Expected workflow:

1. Make a change in `k8s/mychart` or one of its values files.
2. Commit the change.
3. Push to `origin/lab13`.
4. ArgoCD detects a new Git revision.
5. Dev auto-syncs automatically.
6. Prod remains `OutOfSync` until a manual sync is approved.

Example change:

```powershell
git add k8s/mychart/values-dev.yaml
git commit -m "lab13: change dev replica count"
git push
argocd app get python-app-dev
argocd app get python-app-prod
```

Expected result:

- `python-app-dev` should move back to `Synced` automatically
- `python-app-prod` should show the new revision but stay manual until `argocd app sync python-app-prod`

## Self-Healing Evidence

### 1. Manual scale test

Dev has `selfHeal: true`, so ArgoCD should revert drift created directly in the cluster.

Commands:

```powershell
kubectl scale deployment python-app-dev -n dev --replicas=5
argocd app diff python-app-dev
argocd app get python-app-dev
kubectl get deploy -n dev -w
```

Expected behavior:

- deployment becomes `OutOfSync`
- ArgoCD re-applies the Git state
- replica count returns to `1` from `values-dev.yaml`

### 2. Pod deletion test

```powershell
kubectl delete pod -n dev -l app.kubernetes.io/instance=python-app-dev
kubectl get pods -n dev -w
```

Expected behavior:

- Kubernetes recreates the deleted pod through the ReplicaSet
- this is Kubernetes self-healing, not ArgoCD sync logic

### 3. Configuration drift test

```powershell
kubectl label deployment python-app-dev-mychart -n dev drift=manual --overwrite
argocd app diff python-app-dev
argocd app get python-app-dev
```

Expected behavior:

- ArgoCD shows the label diff
- the label is removed on the next self-heal reconciliation

Difference between healing mechanisms:

- Kubernetes self-healing recreates failed or deleted Pods to satisfy Deployment or ReplicaSet state
- ArgoCD self-healing restores declarative configuration so live resources match Git

ArgoCD sync trigger summary:

- new Git commit detected during repository polling
- manual `argocd app sync`
- webhook event from Git provider
- live-state drift when `selfHeal` is enabled

ArgoCD reconciliation interval:

- repository reconciliation is configured by ArgoCD and commonly defaults to a few minutes
- in the chart defaults inspected for this lab, `timeout.reconciliation` is `120s` and jitter is `60s`

## Bonus - ApplicationSet

The bonus manifest [argocd/applicationset.yaml](./argocd/applicationset.yaml) uses a List generator to create both environments from one template.

Implementation details:

- `dev` and `prod` are defined as generator elements
- `goTemplate` is enabled with `missingkey=error`
- `templatePatch` conditionally enables automated sync only for `dev`
- `prod` remains manual because the patch is not applied there

Apply the ApplicationSet instead of the two individual environment applications:

```powershell
kubectl delete application python-app-dev -n argocd --ignore-not-found
kubectl delete application python-app-prod -n argocd --ignore-not-found
kubectl apply -f k8s/argocd/applicationset.yaml
```

Benefits of ApplicationSet:

- one template for many environments
- less duplicated YAML
- simpler scaling when adding `qa`, `stage`, or extra clusters
- easier enforcement of naming and destination conventions

When to use which approach:

- individual `Application` manifests are simpler for a small number of apps
- `ApplicationSet` is better once environment count or cluster count starts growing

## Suggested Screenshots

After the local cluster is back online, capture:

- ArgoCD UI with both `python-app-dev` and `python-app-prod`
- application details page for `python-app-dev`
- sync history or diff view showing drift detection

Suggested location:

- `k8s/docs/screenshots/`
