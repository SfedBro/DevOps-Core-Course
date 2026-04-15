# Lab 12 - ConfigMaps and Persistent Volumes

## Application Changes

The Python FastAPI service now keeps a persisted visit counter.

Implemented behavior:

- `GET /` increments the visit counter.
- `GET /visits` returns the current persisted count.
- The counter is stored in a plain text file configured by `VISITS_FILE`.
- Docker and Kubernetes use `/data/visits`.
- The app reads optional JSON configuration from `CONFIG_FILE`.
- Kubernetes mounts that file at `/config/config.json`.

The counter implementation uses a process-local lock and atomic file replacement
for safe read/increment/write behavior inside one application process.

Relevant files:

- [app.py](../app_python/app.py)
- [README.md](../app_python/README.md)
- [Dockerfile](../app_python/Dockerfile)
- [docker-compose.yml](../monitoring/docker-compose.yml)

Local Docker verification:

- [lab12_docker-runtime.txt](./docs/lab12_docker-runtime.txt)

The local Docker evidence shows:

- the container was started with a `/data` volume
- two requests to `/` incremented the counter to `2`
- the host visits file contained `2`
- after `docker restart`, `/visits` still returned `2`

Evidence:

```text
IMAGE=sfedbro/app_python:lab12

COMMAND: docker run -d --name devops-lab12-evidence -p 18090:5000 -e VISITS_FILE=/data/visits -v C:\Users\Admin\AppData\Local\Temp\devops-lab12-visits:/data sfedbro/app_python:lab12
1e7a327ee8a7149b1730e29d1c043f31062e8445c74ba6ee4136ee07f7b97793

COMMAND: curl.exe -s http://localhost:18090/

COMMAND: curl.exe -s http://localhost:18090/

COMMAND: curl.exe -s http://localhost:18090/visits
{"visits":2,"file":"/data/visits"}

COMMAND: Get-Content C:\Users\Admin\AppData\Local\Temp\devops-lab12-visits\visits
2

COMMAND: docker restart devops-lab12-evidence
devops-lab12-evidence

COMMAND: curl.exe -s http://localhost:18090/visits
{"visits":2,"file":"/data/visits"}

COMMAND: Get-Content C:\Users\Admin\AppData\Local\Temp\devops-lab12-visits\visits
2
```

## ConfigMap Implementation

The Helm chart creates two ConfigMaps.

File-based ConfigMap:

- Template: [configmap.yaml](./mychart/templates/configmap.yaml)
- Source file: [config.json](./mychart/files/config.json)
- Mounted path inside the pod: `/config/config.json`
- The template uses `.Files.Get` with `tpl` so values such as environment and
  log level are rendered from Helm values.

Environment variable ConfigMap:

- Template: [configmap.yaml](./mychart/templates/configmap.yaml)
- Name pattern: `<release>-mychart-env`
- Injected with `envFrom.configMapRef`
- Provides values such as `APP_CONFIG_MODE`, `LOG_LEVEL`, and `FEATURE_VISITS`

Values:

- [values.yaml](./mychart/values.yaml)
- [values-dev.yaml](./mychart/values-dev.yaml)
- [values-prod.yaml](./mychart/values-prod.yaml)

Verification commands:

```bash
kubectl get configmap,pvc -n devops-lab12
kubectl exec -n devops-lab12 lab12-mychart-78b7cbfc7b-mczkb -c mychart -- cat /config/config.json
kubectl exec -n devops-lab12 lab12-mychart-78b7cbfc7b-mczkb -c mychart -- printenv
```

Runtime evidence:

- [lab12_runtime.txt](./docs/lab12_runtime.txt)

Image used by the chart:

- `sfedbro/app_python:lab12`

The evidence shows:

- `lab12-mychart-config` and `lab12-mychart-env` exist
- `/config/config.json` is readable inside the pod
- `APP_CONFIG_MODE=configmap`, `LOG_LEVEL=debug`, and `FEATURE_VISITS=true`
  are injected into the container

Evidence:

```text
COMMAND: kubectl get configmap,pvc -n devops-lab12
NAME                             DATA   AGE
configmap/kube-root-ca.crt       1      6h23m
configmap/lab12-mychart-config   1      6h23m
configmap/lab12-mychart-env      3      6h23m

NAME                                       STATUS   VOLUME               CAPACITY   ACCESS MODES   STORAGECLASS   VOLUMEATTRIBUTESCLASS   AGE
persistentvolumeclaim/lab12-mychart-data   Bound    lab12-mychart-data   100Mi      RWO            manual         <unset>                 6h23m
```

```text
COMMAND: kubectl exec -n devops-lab12 lab12-mychart-78b7cbfc7b-mczkb -c mychart -- cat /config/config.json
{
  "application": {
    "name": "devops-info-service",
    "environment": "dev",
    "configSource": "kubernetes-configmap"
  },
  "features": {
    "visitsCounter": true,
    "configHotReload": true
  },
  "settings": {
    "logLevel": "debug",
    "visitsFile": "/data/visits",
    "configFile": "/config/config.json"
  }
}
```

```text
COMMAND: kubectl exec -n devops-lab12 lab12-mychart-78b7cbfc7b-mczkb -c mychart -- printenv | Select-String -Pattern 'APP_CONFIG_MODE|LOG_LEVEL|FEATURE_VISITS|VISITS_FILE|CONFIG_FILE|APP_ENV'
VISITS_FILE=/data/visits
APP_ENV=dev
CONFIG_FILE=/config/config.json
APP_CONFIG_MODE=configmap
FEATURE_VISITS=true
LOG_LEVEL=debug
```

## Persistent Volume

The chart creates persistent storage for `/data/visits`.

Implemented resources:

- [pv.yaml](./mychart/templates/pv.yaml)
- [pvc.yaml](./mychart/templates/pvc.yaml)
- [deployment.yaml](./mychart/templates/deployment.yaml)

PVC configuration:

- Size: `100Mi`
- Access mode: `ReadWriteOnce`
- Storage class: configurable with `persistence.storageClass`
- Default lab mode: static `hostPath` PV with storage class `manual`
- Mount path: `/data`

Why a static hostPath PV is included:

- `kind` does not always provide a default dynamic storage provisioner.
- The static PV keeps the lab reproducible locally.
- In a managed Kubernetes cluster, set `persistence.hostPath.enabled=false` and
  provide a real `storageClass`.

Permissions:

- The application runs as non-root UID/GID `1000`.
- An init container fixes `/data` ownership before the app starts.
- This is needed for local hostPath-backed storage.

Persistence test:

```bash
kubectl exec -n devops-lab12 lab12-mychart-78b7cbfc7b-mczkb -c mychart -- cat /data/visits
kubectl delete pod lab12-mychart-78b7cbfc7b-mczkb -n devops-lab12
kubectl wait --for=condition=Ready pod -n devops-lab12 -l app.kubernetes.io/instance=lab12
kubectl exec -n devops-lab12 lab12-mychart-78b7cbfc7b-qqfxp -c mychart -- cat /data/visits
```

Runtime evidence:

- [lab12_runtime.txt](./docs/lab12_runtime.txt)

The evidence shows:

- PVC `lab12-mychart-data` is `Bound`
- PV `lab12-mychart-data` is `Bound`
- before pod deletion, `/visits` returned `6`
- after pod deletion and replacement, `/visits` still returned `6`
- `/data/visits` also stayed `6`

Evidence:

```text
COMMAND: kubectl get pv lab12-mychart-data
NAME                 CAPACITY   ACCESS MODES   RECLAIM POLICY   STATUS   CLAIM                             STORAGECLASS   VOLUMEATTRIBUTESCLASS   REASON   AGE
lab12-mychart-data   100Mi      RWO            Retain           Bound    devops-lab12/lab12-mychart-data   manual         <unset>                          6h23m
```

```text
COMMAND: kubectl exec -n devops-lab12 lab12-mychart-78b7cbfc7b-mczkb -c mychart -- python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:5000/').read().decode())"

COMMAND: kubectl exec -n devops-lab12 lab12-mychart-78b7cbfc7b-mczkb -c mychart -- python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:5000/').read().decode())"

COMMAND: kubectl exec -n devops-lab12 lab12-mychart-78b7cbfc7b-mczkb -c mychart -- python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:5000/visits').read().decode())"
{"visits":6,"file":"/data/visits"}

COMMAND: kubectl exec -n devops-lab12 lab12-mychart-78b7cbfc7b-mczkb -c mychart -- cat /data/visits
6

COMMAND: kubectl delete pod lab12-mychart-78b7cbfc7b-mczkb -n devops-lab12
pod "lab12-mychart-78b7cbfc7b-mczkb" deleted from devops-lab12 namespace

COMMAND: kubectl exec -n devops-lab12 lab12-mychart-78b7cbfc7b-qqfxp -c mychart -- python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:5000/visits').read().decode())"
{"visits":6,"file":"/data/visits"}

COMMAND: kubectl exec -n devops-lab12 lab12-mychart-78b7cbfc7b-qqfxp -c mychart -- cat /data/visits
6
```

## ConfigMap vs Secret

Use ConfigMaps for:

- non-sensitive application settings
- feature flags
- log levels
- configuration files

Use Secrets for:

- passwords
- API tokens
- private keys
- credentials

Key differences:

- ConfigMaps are not intended for sensitive data.
- Secrets are also only base64-encoded by default, but Kubernetes treats them as
  sensitive objects and can restrict access separately with RBAC.
- Production clusters should combine Secrets with RBAC and encryption at rest.

## Bonus - ConfigMap Reload Behavior

The chart implements two reload-friendly patterns.

Mounted directory pattern:

- The ConfigMap is mounted as the full `/config` directory.
- It does not use `subPath`.
- This allows Kubernetes to update mounted ConfigMap files after kubelet sync.

Application read pattern:

- The application reads `CONFIG_FILE` when serving `/`.
- This makes updated file content visible without rebuilding the image.

Helm checksum pattern:

- [deployment.yaml](./mychart/templates/deployment.yaml) includes:

```yaml
checksum/config: {{ include (print $.Template.BasePath "/configmap.yaml") . | sha256sum }}
```

This causes a Deployment rollout when the ConfigMap template changes during
`helm upgrade`.

subPath limitation:

- A ConfigMap mounted with `subPath` is copied as a single file mount.
- It does not receive live updates from Kubernetes.
- Use a full directory mount when update visibility matters.

Validation outputs:

- [lab12_helm-lint.txt](./docs/lab12_helm-lint.txt)
- [lab12_helm-template.txt](./docs/lab12_helm-template.txt)
- [lab12_pytest.txt](./docs/lab12_pytest.txt)

Validation evidence:

```text
pytest:
10 passed in 1.11s

helm lint:
1 chart(s) linted, 0 chart(s) failed

runtime image:
sfedbro/app_python:lab12
```

## Raw Evidence

This section keeps the important command outputs directly in this Markdown file.
The full raw logs are also stored in `k8s/docs/lab12_*.txt`.

### Local Docker Persistence

```text
Lab 12 local Docker persistence evidence - 2026-04-15T23:25:30

IMAGE=sfedbro/app_python:lab12
DATA_DIR=C:\Users\Admin\AppData\Local\Temp\devops-lab12-visits

=== Docker image ===
COMMAND: docker image inspect sfedbro/app_python:lab12 --format '{{.RepoTags}} {{.Id}}'
[devops-course/app-python:lab12 sfedbro/app_python:lab12] sha256:e9c3a692264f78ab9b86f85a0d3023bb6e759d6e8f834a53b88eb7f76076881e


=== Start container with persistent volume ===
COMMAND: docker run -d --name devops-lab12-evidence -p 18090:5000 -e VISITS_FILE=/data/visits -v C:\Users\Admin\AppData\Local\Temp\devops-lab12-visits:/data sfedbro/app_python:lab12
1e7a327ee8a7149b1730e29d1c043f31062e8445c74ba6ee4136ee07f7b97793


=== First root request ===
COMMAND: curl.exe -s http://localhost:18090/
{"service":{"name":"devops-info-service","version":"1.0.0","description":"DevOps course info service","framework":"FastAPI"},"system":{"hostname":"1e7a327ee8a7","platform":"Linux","architecture":"x86_64","cpu_count":16,"python_version":"3.12.13"},"configuration":{"application":{"name":"devops-info-service","environment":"local","configSource":"default"},"features":{"visitsCounter":true}},"runtime":{"uptime_seconds":2,"uptime_human":"0 hours, 0 minutes","current_time":"2026-04-15T20:25:34.092987+00:00","timezone":"UTC"},"visits":{"count":1,"file":"/data/visits"},"request":{"client_ip":"172.17.0.1","user_agent":"curl/8.13.0","method":"GET","path":"/"},"endpoints":[{"path":"/","method":"GET","description":"Service information"},{"path":"/health","method":"GET","description":"Health check"},{"path":"/visits","method":"GET","description":"Current persisted visits count"}]}


=== Second root request ===
COMMAND: curl.exe -s http://localhost:18090/
{"service":{"name":"devops-info-service","version":"1.0.0","description":"DevOps course info service","framework":"FastAPI"},"system":{"hostname":"1e7a327ee8a7","platform":"Linux","architecture":"x86_64","cpu_count":16,"python_version":"3.12.13"},"configuration":{"application":{"name":"devops-info-service","environment":"local","configSource":"default"},"features":{"visitsCounter":true}},"runtime":{"uptime_seconds":2,"uptime_human":"0 hours, 0 minutes","current_time":"2026-04-15T20:25:34.170951+00:00","timezone":"UTC"},"visits":{"count":2,"file":"/data/visits"},"request":{"client_ip":"172.17.0.1","user_agent":"curl/8.13.0","method":"GET","path":"/"},"endpoints":[{"path":"/","method":"GET","description":"Service information"},{"path":"/health","method":"GET","description":"Health check"},{"path":"/visits","method":"GET","description":"Current persisted visits count"}]}


=== Visits before restart ===
COMMAND: curl.exe -s http://localhost:18090/visits
{"visits":2,"file":"/data/visits"}


=== Host visits file before restart ===
COMMAND: Get-Content C:\Users\Admin\AppData\Local\Temp\devops-lab12-visits\visits
2


=== Restart container ===
COMMAND: docker restart devops-lab12-evidence
devops-lab12-evidence


=== Visits after restart ===
COMMAND: curl.exe -s http://localhost:18090/visits
{"visits":2,"file":"/data/visits"}


=== Host visits file after restart ===
COMMAND: Get-Content C:\Users\Admin\AppData\Local\Temp\devops-lab12-visits\visits
2


=== Remove evidence container ===
COMMAND: docker rm -f devops-lab12-evidence
devops-lab12-evidence
```

### Kubernetes Runtime

```text
Lab 12 runtime evidence - 2026-04-15T23:24:56

=== Helm release ===
COMMAND: helm status lab12 -n devops-lab12
NAME: lab12
LAST DEPLOYED: Wed Apr 15 23:22:55 2026
NAMESPACE: devops-lab12
STATUS: deployed
REVISION: 5
DESCRIPTION: Upgrade complete
RESOURCES:
==> v1/ServiceAccount
NAME            SECRETS   AGE
lab12-mychart   0         6h23m

==> v1/Secret
NAME                   TYPE     DATA   AGE
lab12-mychart-secret   Opaque   2      6h23m

==> v1/ConfigMap
NAME                   DATA   AGE
lab12-mychart-config   1      6h23m
lab12-mychart-env   3     6h23m

==> v1/PersistentVolume
NAME                 CAPACITY   ACCESS MODES   RECLAIM POLICY   STATUS   CLAIM                             STORAGECLASS   VOLUMEATTRIBUTESCLASS   REASON   AGE
lab12-mychart-data   100Mi      RWO            Retain           Bound    devops-lab12/lab12-mychart-data   manual         <unset>                          6h23m

==> v1/PersistentVolumeClaim
NAME                 STATUS   VOLUME               CAPACITY   ACCESS MODES   STORAGECLASS   VOLUMEATTRIBUTESCLASS   AGE
lab12-mychart-data   Bound    lab12-mychart-data   100Mi      RWO            manual         <unset>                 6h23m

==> v1/Service
NAME            TYPE        CLUSTER-IP     EXTERNAL-IP   PORT(S)   AGE
lab12-mychart   ClusterIP   10.96.139.11   <none>        80/TCP    6h23m

==> v1/Deployment
NAME            READY   UP-TO-DATE   AVAILABLE   AGE
lab12-mychart   1/1     1            1           6h23m

==> v1/Pod(related)
NAME                             READY   STATUS    RESTARTS        AGE
lab12-mychart-78b7cbfc7b-mczkb   1/1     Running   1 (2m40s ago)   6h3m


TEST SUITE: None
NOTES:
Thank you for installing mychart.

Release name: lab12
Namespace: devops-lab12
The service type is ClusterIP.

Check the service:
  kubectl get svc -n devops-lab12 lab12-mychart


=== Deployment image ===
COMMAND: kubectl get deployment lab12-mychart -n devops-lab12 -o jsonpath='{.spec.template.spec.containers[0].image}'
sfedbro/app_python:lab12


=== ConfigMaps and PVC ===
COMMAND: kubectl get configmap,pvc -n devops-lab12
NAME                             DATA   AGE
configmap/kube-root-ca.crt       1      6h23m
configmap/lab12-mychart-config   1      6h23m
configmap/lab12-mychart-env      3      6h23m

NAME                                       STATUS   VOLUME               CAPACITY   ACCESS MODES   STORAGECLASS   VOLUMEATTRIBUTESCLASS   AGE
persistentvolumeclaim/lab12-mychart-data   Bound    lab12-mychart-data   100Mi      RWO            manual         <unset>                 6h23m


=== PersistentVolume ===
COMMAND: kubectl get pv lab12-mychart-data
NAME                 CAPACITY   ACCESS MODES   RECLAIM POLICY   STATUS   CLAIM                             STORAGECLASS   VOLUMEATTRIBUTESCLASS   REASON   AGE
lab12-mychart-data   100Mi      RWO            Retain           Bound    devops-lab12/lab12-mychart-data   manual         <unset>                          6h23m


=== Selected pod ===
COMMAND: kubectl get pods -n devops-lab12 -l app.kubernetes.io/instance=lab12,app.kubernetes.io/name=mychart -o jsonpath='{.items[0].metadata.name}'
lab12-mychart-78b7cbfc7b-mczkb


=== ConfigMap file mounted in pod ===
COMMAND: kubectl exec -n devops-lab12 lab12-mychart-78b7cbfc7b-mczkb -c mychart -- cat /config/config.json
{
  "application": {
    "name": "devops-info-service",
    "environment": "dev",
    "configSource": "kubernetes-configmap"
  },
  "features": {
    "visitsCounter": true,
    "configHotReload": true
  },
  "settings": {
    "logLevel": "debug",
    "visitsFile": "/data/visits",
    "configFile": "/config/config.json"
  }
}


=== ConfigMap env vars in pod ===
COMMAND: kubectl exec -n devops-lab12 lab12-mychart-78b7cbfc7b-mczkb -c mychart -- printenv | Select-String -Pattern 'APP_CONFIG_MODE|LOG_LEVEL|FEATURE_VISITS|VISITS_FILE|CONFIG_FILE|APP_ENV'

VISITS_FILE=/data/visits
APP_ENV=dev
CONFIG_FILE=/config/config.json
APP_CONFIG_MODE=configmap
FEATURE_VISITS=true
LOG_LEVEL=debug



=== Root request increments visits - request 1 ===
COMMAND: kubectl exec -n devops-lab12 lab12-mychart-78b7cbfc7b-mczkb -c mychart -- python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:5000/').read().decode())"
{"service":{"name":"devops-info-service","version":"1.0.0","description":"DevOps course info service","framework":"FastAPI"},"system":{"hostname":"lab12-mychart-78b7cbfc7b-mczkb","platform":"Linux","architecture":"x86_64","cpu_count":16,"python_version":"3.12.13"},"configuration":{"application":{"name":"devops-info-service","environment":"dev","configSource":"kubernetes-configmap"},"features":{"visitsCounter":true,"configHotReload":true},"settings":{"logLevel":"debug","visitsFile":"/data/visits","configFile":"/config/config.json"}},"runtime":{"uptime_seconds":142,"uptime_human":"0 hours, 2 minutes","current_time":"2026-04-15T20:24:58.458689+00:00","timezone":"UTC"},"visits":{"count":5,"file":"/data/visits"},"request":{"client_ip":"127.0.0.1","user_agent":"Python-urllib/3.12","method":"GET","path":"/"},"endpoints":[{"path":"/","method":"GET","description":"Service information"},{"path":"/health","method":"GET","description":"Health check"},{"path":"/visits","method":"GET","description":"Current persisted visits count"}]}


=== Root request increments visits - request 2 ===
COMMAND: kubectl exec -n devops-lab12 lab12-mychart-78b7cbfc7b-mczkb -c mychart -- python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:5000/').read().decode())"
{"service":{"name":"devops-info-service","version":"1.0.0","description":"DevOps course info service","framework":"FastAPI"},"system":{"hostname":"lab12-mychart-78b7cbfc7b-mczkb","platform":"Linux","architecture":"x86_64","cpu_count":16,"python_version":"3.12.13"},"configuration":{"application":{"name":"devops-info-service","environment":"dev","configSource":"kubernetes-configmap"},"features":{"visitsCounter":true,"configHotReload":true},"settings":{"logLevel":"debug","visitsFile":"/data/visits","configFile":"/config/config.json"}},"runtime":{"uptime_seconds":142,"uptime_human":"0 hours, 2 minutes","current_time":"2026-04-15T20:24:59.150555+00:00","timezone":"UTC"},"visits":{"count":6,"file":"/data/visits"},"request":{"client_ip":"127.0.0.1","user_agent":"Python-urllib/3.12","method":"GET","path":"/"},"endpoints":[{"path":"/","method":"GET","description":"Service information"},{"path":"/health","method":"GET","description":"Health check"},{"path":"/visits","method":"GET","description":"Current persisted visits count"}]}


=== Visits before pod deletion ===
COMMAND: kubectl exec -n devops-lab12 lab12-mychart-78b7cbfc7b-mczkb -c mychart -- python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:5000/visits').read().decode())"
{"visits":6,"file":"/data/visits"}


=== Visits file before pod deletion ===
COMMAND: kubectl exec -n devops-lab12 lab12-mychart-78b7cbfc7b-mczkb -c mychart -- cat /data/visits
6


=== Delete pod ===
COMMAND: kubectl delete pod lab12-mychart-78b7cbfc7b-mczkb -n devops-lab12
pod "lab12-mychart-78b7cbfc7b-mczkb" deleted from devops-lab12 namespace


=== New pod after deletion ===
COMMAND: kubectl get pods -n devops-lab12 -l app.kubernetes.io/instance=lab12,app.kubernetes.io/name=mychart -o jsonpath='{.items[0].metadata.name}'
lab12-mychart-78b7cbfc7b-qqfxp


=== Visits after pod recreation ===
COMMAND: kubectl exec -n devops-lab12 lab12-mychart-78b7cbfc7b-qqfxp -c mychart -- python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:5000/visits').read().decode())"
{"visits":6,"file":"/data/visits"}


=== Visits file after pod recreation ===
COMMAND: kubectl exec -n devops-lab12 lab12-mychart-78b7cbfc7b-qqfxp -c mychart -- cat /data/visits
6
```
