# Lab 15 - StatefulSets and Persistent Storage

Raw command output is also saved in [lab15_runtime.txt](./docs/lab15_runtime.txt).

## Why StatefulSet

The previous chart modes are correct for stateless workloads:

- [templates/deployment.yaml](./mychart/templates/deployment.yaml) renders a Kubernetes `Deployment`.
- [templates/rollout.yaml](./mychart/templates/rollout.yaml) renders an Argo `Rollout`.
- [templates/pv.yaml](./mychart/templates/pv.yaml) and [templates/pvc.yaml](./mychart/templates/pvc.yaml) render one shared `PV/PVC` pair for the whole Helm release.

That model is not a good fit for several stateful replicas. If three pods share
one visits file, the replicas are no longer independently stateful and the app
cannot prove pod-specific persistence. A StatefulSet solves this with stable pod
identity and `volumeClaimTemplates`.

StatefulSet guarantees used in this lab:

- Stable pod identity: `lab15-mychart-0`, `lab15-mychart-1`, `lab15-mychart-2`.
- Stable network identity: each pod is reachable through the headless service.
- Stable per-pod storage: each pod gets its own PVC from `volumeClaimTemplates`.
- Ordered behavior: pods are created in ordinal order by default with `OrderedReady`.

Headless service purpose:

- `clusterIP: None` disables normal service load-balancing for this service.
- Kubernetes creates DNS records for individual StatefulSet pods.
- DNS pattern: `<pod-name>.<headless-service>.<namespace>.svc.cluster.local`.
- In this lab: `lab15-mychart-1.lab15-mychart-headless.devops-lab15.svc.cluster.local`.

## Chart Changes

Implemented files:

- [templates/statefulset.yaml](./mychart/templates/statefulset.yaml) - StatefulSet workload with `volumeClaimTemplates`.
- [templates/headless-service.yaml](./mychart/templates/headless-service.yaml) - headless service for stable pod DNS.
- [values-statefulset.yaml](./mychart/values-statefulset.yaml) - values file for Lab 15 stateful mode.

Render switch:

- `statefulset.enabled=false` by default, so old Deployment/Rollout modes remain usable.
- `values-statefulset.yaml` sets `statefulset.enabled=true`.
- Deployment renders only when `rollout.enabled=false` and `statefulset.enabled=false`.
- Rollout renders only when `rollout.enabled=true` and `statefulset.enabled=false`.
- Shared `PV/PVC` templates do not render when `statefulset.enabled=true`.
- Blue-green preview service is also disabled in stateful mode.

Stateful values:

```yaml
statefulset:
  enabled: true
  podManagementPolicy: OrderedReady
  updateStrategy:
    type: RollingUpdate

rollout:
  enabled: false

persistence:
  enabled: true
  mountPath: /data
  size: 100Mi
  accessModes:
    - ReadWriteOnce
  storageClass: standard
  hostPath:
    enabled: false
```

The local `kind` cluster has a dynamic `standard` storage class:

```text
COMMAND: kubectl get storageclass
NAME                 PROVISIONER             RECLAIMPOLICY   VOLUMEBINDINGMODE      ALLOWVOLUMEEXPANSION   AGE
standard (default)   rancher.io/local-path   Delete          WaitForFirstConsumer   false                  43d
```

## Render Evidence

Helm lint:

```text
COMMAND: helm lint k8s/mychart
==> Linting k8s/mychart
[INFO] Chart.yaml: icon is recommended

1 chart(s) linted, 0 chart(s) failed
```

Stateful mode render check:

```text
COMMAND: helm template lab15 k8s/mychart -f k8s/mychart/values-statefulset.yaml --namespace devops-lab15
kind: StatefulSet = 1
kind: Deployment = 0
kind: Rollout = 0
kind: PersistentVolume = 0
kind: PersistentVolumeClaim = 0
clusterIP: None = 1
volumeClaimTemplates: = 1
```

Rendered headless service excerpt:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: lab15-mychart-headless
spec:
  clusterIP: None
  selector:
    app.kubernetes.io/name: mychart
    app.kubernetes.io/instance: lab15
  ports:
    - name: http
      port: 80
      targetPort: http
```

Rendered StatefulSet excerpt:

```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: lab15-mychart
spec:
  serviceName: lab15-mychart-headless
  replicas: 3
  podManagementPolicy: OrderedReady
  updateStrategy:
    type: RollingUpdate
  volumeClaimTemplates:
    - metadata:
        name: app-data
      spec:
        accessModes:
          - ReadWriteOnce
        resources:
          requests:
            storage: 100Mi
        storageClassName: "standard"
```

## Resource Evidence

Install command:

```powershell
helm upgrade --install lab15 k8s/mychart `
  -f k8s/mychart/values-statefulset.yaml `
  --namespace devops-lab15 `
  --create-namespace `
  --wait `
  --wait-for-jobs `
  --timeout 5m
```

Install evidence:

```text
Release "lab15" does not exist. Installing it now.
NAME: lab15
LAST DEPLOYED: Thu May  7 21:22:13 2026
NAMESPACE: devops-lab15
STATUS: deployed
REVISION: 1
DESCRIPTION: Install complete
```

Kubernetes resources:

```text
COMMAND: kubectl get po,sts,svc,pvc -n devops-lab15 -o wide
NAME                  READY   STATUS    RESTARTS   AGE     IP            NODE
pod/lab15-mychart-0   1/1     Running   0          2m16s   10.244.0.42   lab09-control-plane
pod/lab15-mychart-1   1/1     Running   0          2m4s    10.244.0.44   lab09-control-plane
pod/lab15-mychart-2   1/1     Running   0          108s    10.244.0.46   lab09-control-plane

NAME                             READY   AGE     CONTAINERS   IMAGES
statefulset.apps/lab15-mychart   3/3     2m16s   mychart      sfedbro/app_python:lab12

NAME                             TYPE        CLUSTER-IP      PORT(S)   SELECTOR
service/lab15-mychart            ClusterIP   10.96.109.152   80/TCP    app.kubernetes.io/instance=lab15,app.kubernetes.io/name=mychart
service/lab15-mychart-headless   ClusterIP   None            80/TCP    app.kubernetes.io/instance=lab15,app.kubernetes.io/name=mychart

NAME                                             STATUS   VOLUME                                     CAPACITY   ACCESS MODES   STORAGECLASS
persistentvolumeclaim/app-data-lab15-mychart-0   Bound    pvc-2ea07d22-556a-4317-aea1-a384d236f8c8   100Mi      RWO            standard
persistentvolumeclaim/app-data-lab15-mychart-1   Bound    pvc-ad2adc75-9873-4254-a513-eff0e2daa5a1   100Mi      RWO            standard
persistentvolumeclaim/app-data-lab15-mychart-2   Bound    pvc-aa068c90-9c88-4db3-a4fd-e6d226241cac   100Mi      RWO            standard
```

StatefulSet describe excerpt:

```text
COMMAND: kubectl describe statefulset lab15-mychart -n devops-lab15
Name:               lab15-mychart
Namespace:          devops-lab15
Replicas:           3 desired | 3 total
Update Strategy:    RollingUpdate
Pods Status:        3 Running / 0 Waiting / 0 Succeeded / 0 Failed
Volume Claims:
  Name:          app-data
  StorageClass:  standard
  Capacity:      100Mi
  Access Modes:  [ReadWriteOnce]
Events:
  Normal  SuccessfulCreate  create Claim app-data-lab15-mychart-0 Pod lab15-mychart-0 in StatefulSet lab15-mychart success
  Normal  SuccessfulCreate  create Claim app-data-lab15-mychart-1 Pod lab15-mychart-1 in StatefulSet lab15-mychart success
  Normal  SuccessfulCreate  create Claim app-data-lab15-mychart-2 Pod lab15-mychart-2 in StatefulSet lab15-mychart success
```

## Identity and Storage Proof

DNS resolution from pod `0` to pod `1`:

```text
COMMAND: kubectl exec -n devops-lab15 lab15-mychart-0 -- python -c "import socket; print(socket.gethostbyname('lab15-mychart-1.lab15-mychart-headless.devops-lab15.svc.cluster.local'))"
10.244.0.44
```

Pod-specific traffic test:

```text
COMMAND: kubectl exec -n devops-lab15 lab15-mychart-0 -- python -c "import urllib.request; urls=['http://lab15-mychart-0.lab15-mychart-headless.devops-lab15.svc.cluster.local:5000/','http://lab15-mychart-0.lab15-mychart-headless.devops-lab15.svc.cluster.local:5000/','http://lab15-mychart-1.lab15-mychart-headless.devops-lab15.svc.cluster.local:5000/']; [print(urllib.request.urlopen(u).read().decode()) for u in urls]"

Captured response excerpts:
GET http://lab15-mychart-0.lab15-mychart-headless.devops-lab15.svc.cluster.local:5000/
visits.count = 1, hostname = lab15-mychart-0

GET http://lab15-mychart-0.lab15-mychart-headless.devops-lab15.svc.cluster.local:5000/
visits.count = 2, hostname = lab15-mychart-0

GET http://lab15-mychart-1.lab15-mychart-headless.devops-lab15.svc.cluster.local:5000/
visits.count = 1, hostname = lab15-mychart-1
```

Different `/visits` values prove per-pod storage isolation:

```text
COMMAND: kubectl exec -n devops-lab15 lab15-mychart-0 -- python -c "import urllib.request; urls=['http://lab15-mychart-0.lab15-mychart-headless.devops-lab15.svc.cluster.local:5000/visits','http://lab15-mychart-1.lab15-mychart-headless.devops-lab15.svc.cluster.local:5000/visits']; [print(u, urllib.request.urlopen(u).read().decode()) for u in urls]"
http://lab15-mychart-0.lab15-mychart-headless.devops-lab15.svc.cluster.local:5000/visits {"visits":2,"file":"/data/visits"}
http://lab15-mychart-1.lab15-mychart-headless.devops-lab15.svc.cluster.local:5000/visits {"visits":1,"file":"/data/visits"}
```

Persistence after deleting one pod:

```text
COMMAND: kubectl exec -n devops-lab15 lab15-mychart-0 -- cat /data/visits
2

COMMAND: kubectl delete pod lab15-mychart-0 -n devops-lab15
pod "lab15-mychart-0" deleted from devops-lab15 namespace

COMMAND: kubectl wait --for=condition=Ready pod/lab15-mychart-0 -n devops-lab15 --timeout=180s
pod/lab15-mychart-0 condition met

COMMAND: kubectl exec -n devops-lab15 lab15-mychart-0 -- cat /data/visits
2

COMMAND: kubectl get pod lab15-mychart-0 -n devops-lab15 -o wide
NAME              READY   STATUS    RESTARTS   AGE   IP            NODE
lab15-mychart-0   1/1     Running   0          13s   10.244.0.48   lab09-control-plane
```

The pod IP changed from `10.244.0.42` to `10.244.0.48`, but the pod name
`lab15-mychart-0` and `/data/visits` value stayed stable. That proves the new
pod reused the same ordinal-specific PVC.

## Reflection

I would still choose a Deployment or Argo Rollout when:

- replicas are interchangeable
- state is externalized to a database, cache, object storage, or queue
- rollout speed and operational simplicity matter more than pod identity
- progressive delivery features such as canary or blue-green are required

I would choose a StatefulSet when:

- pod identity matters
- each replica owns persistent data
- per-pod DNS discovery is required
- ordered startup, scaling, and updates reduce operational risk

Production tradeoffs:

- StatefulSets are more operationally sensitive than Deployments.
- Storage class behavior and reclaim policies must be understood before production use.
- Backups and restore procedures become mandatory because data is tied to PVCs.
- Scaling down does not automatically delete PVCs, which protects data but can leave storage behind.
- Rolling updates are ordered and safer, but slower than stateless Deployment updates.

## Useful Commands

```powershell
helm lint k8s/mychart
helm template lab15 k8s/mychart -f k8s/mychart/values-statefulset.yaml --namespace devops-lab15
helm upgrade --install lab15 k8s/mychart -f k8s/mychart/values-statefulset.yaml --namespace devops-lab15 --create-namespace --wait --wait-for-jobs --timeout 5m
kubectl get po,sts,svc,pvc -n devops-lab15 -o wide
kubectl describe statefulset lab15-mychart -n devops-lab15
kubectl exec -n devops-lab15 lab15-mychart-0 -- cat /data/visits
kubectl delete pod lab15-mychart-0 -n devops-lab15
kubectl wait --for=condition=Ready pod/lab15-mychart-0 -n devops-lab15 --timeout=180s
```
