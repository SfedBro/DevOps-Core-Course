# Lab 11 - Kubernetes Secrets and HashiCorp Vault

## Kubernetes Secrets

Imperative secret creation:

```bash
kubectl create secret generic app-credentials \
  --from-literal=username=admin \
  --from-literal=password=secret123 \
  -n devops-helm
```

View the secret:

```bash
kubectl get secret app-credentials -n devops-helm -o yaml
```

Decode the values:

```bash
kubectl get secret app-credentials -n devops-helm -o jsonpath="{.data.username}"
kubectl get secret app-credentials -n devops-helm -o jsonpath="{.data.password}"

# PowerShell decode example
[System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String("<base64-value>"))
```

Encoding vs encryption:

- Kubernetes Secrets are base64-encoded for transport and storage in YAML/JSON
- base64 is not encryption and provides no confidentiality on its own
- anyone who can read the Secret object can decode it immediately

Security implications:

- Secrets are not encrypted at rest by default in a typical cluster
- real protection at rest requires etcd encryption
- etcd encryption should be enabled in production clusters when Kubernetes Secrets are used
- RBAC should restrict read access for secrets

## Helm Secret Integration

Lab 10 Helm chart was extended with native Kubernetes Secret support.

Implemented files:

- [mychart/templates/secrets.yaml](./mychart/templates/secrets.yaml)
  Creates an Opaque Secret using `stringData`
- [mychart/templates/serviceaccount.yaml](./mychart/templates/serviceaccount.yaml)
  Creates a dedicated service account for Vault binding
- [mychart/templates/deployment.yaml](./mychart/templates/deployment.yaml)
  Consumes secret values via `envFrom.secretRef`
- [mychart/templates/\_helpers.tpl](./mychart/templates/_helpers.tpl)
  Adds helper templates for secret naming, service account naming, named environment variables, and Vault annotations
- [mychart/values.yaml](./mychart/values.yaml)
  Adds placeholder secret values and Vault configuration
- [mychart/values-vault.yaml](./mychart/values-vault.yaml)
  Enables Vault annotations and disables the native Secret for Vault-based deployments

Secret values in `values.yaml`:

```yaml
secrets:
  enabled: true
  data:
    username: 'change-me'
    password: 'change-me'
```

Do not commit real values. Use overrides at deploy time:

```bash
helm upgrade --install myapp k8s/mychart
  -f k8s/mychart/values-dev.yaml
  --namespace devops-helm
  --set secrets.data.username=admin
  --set secrets.data.password=secret123
```

How secrets are consumed:

- the Deployment uses `envFrom` with `secretRef`
- all keys from the Secret become environment variables inside the container
- `kubectl describe pod` shows the secret reference, not the decoded values

Verification commands:

```bash
kubectl get secret -n devops-helm
kubectl exec -n devops-helm deploy/myapp-secret-mychart -- printenv | grep -E "username|password|APP_ENV"
kubectl describe pod -n devops-helm <pod-name>
```

Expected result:

- `username` and `password` are present inside the container
- `kubectl describe pod` does not print the actual secret values

## Resource Management

Configured in the chart:

```yaml
resources:
  requests:
    cpu: 100m
    memory: 128Mi
  limits:
    cpu: 250m
    memory: 256Mi
```

Requests vs limits:

- requests define the minimum resources Kubernetes uses for scheduling
- limits cap the maximum resources a container can use

How to choose values:

- start from observed runtime usage
- keep requests realistic for scheduling
- keep limits high enough to avoid unnecessary throttling but low enough to protect the node
- use separate dev/prod overrides when needed

## Vault Integration

Vault installation via Helm:

```bash
helm repo add hashicorp https://helm.releases.hashicorp.com
helm repo update
helm install vault hashicorp/vault
  --namespace vault
  --create-namespace
  --set "server.dev.enabled=true"
  --set "injector.enabled=true"
```

Verify Vault pods:

```bash
kubectl get pods -n vault
```

Configure Vault inside the pod:

```bash
kubectl exec -it -n vault vault-0 -- sh
```

Inside Vault:

```bash
export VAULT_ADDR='http://127.0.0.1:8200'
export VAULT_TOKEN='root'

vault secrets enable -path=secret kv-v2
vault kv put secret/myapp/config username="admin" password="secret123"
vault auth enable kubernetes
vault write auth/kubernetes/config
  kubernetes_host="https://$KUBERNETES_PORT_443_TCP_ADDR:443"
  token_reviewer_jwt="$(cat /var/run/secrets/kubernetes.io/serviceaccount/token)"
  kubernetes_ca_cert=@/var/run/secrets/kubernetes.io/serviceaccount/ca.crt
  disable_iss_validation=true
```

Example policy:

```hcl
path "secret/data/myapp/config" {
  capabilities = ["read"]
}
```

Apply the policy and role:

```bash
cat >/tmp/myapp-policy.hcl <<'EOF'
path "secret/data/myapp/config" {
  capabilities = ["read"]
}
EOF

vault policy write myapp /tmp/myapp-policy.hcl

vault write auth/kubernetes/role/myapp
  bound_service_account_names="myapp-mychart"
  bound_service_account_namespaces="devops-helm"
  policies="myapp"
  ttl="1h"
```

Deploy the chart with Vault injection enabled:

```bash
helm upgrade --install myapp k8s/mychart
  -f k8s/mychart/values-prod.yaml
  -f k8s/mychart/values-vault.yaml
  --namespace devops-helm
```

Implemented Vault chart behavior:

- pod annotations are added when `vault.enabled=true`
- the application service account is set explicitly
- Vault Agent Injector is configured to inject the secret path
- bonus template rendering creates a custom `.env`-style file

Verification commands:

```bash
kubectl get pod -n devops-helm
kubectl describe pod -n devops-helm <pod-name>
kubectl exec -n devops-helm <pod-name> -- ls -R /vault/secrets
kubectl exec -n devops-helm <pod-name> -- cat /vault/secrets/config.env
```

Expected result:

- a Vault sidecar/init container is present
- `/vault/secrets/config` and `/vault/secrets/config.env` appear in the pod
- the rendered file contains the injected values

Runtime note used in this repository:

- `myapp-secret` was used as a separate Helm release for native Secret verification
- `myapp` was kept as the Vault-enabled release for injector verification

## Security Analysis

Kubernetes Secrets:

- simple and built into Kubernetes
- good for basic cluster-native secret handling
- still need RBAC and etcd encryption for production

Vault:

- centralizes secret storage and access policy
- supports dynamic secrets, leasing, and rotation
- works well when multiple apps or clusters need managed access

When to use each:

- use Kubernetes Secrets for simple labs, local development, and small internal workloads
- use Vault for production-grade secret management, rotation, auditing, and stronger access control

Production recommendations:

- never commit real secrets
- enable etcd encryption at rest
- use RBAC to narrow secret access
- prefer external secret management such as Vault for sensitive workloads
- audit who can read secrets and who can impersonate service accounts

## Bonus - Vault Agent Templates

The chart implements a Vault Agent template annotation through `mychart.vaultAnnotations`.

Bonus behavior:

- `vault.hashicorp.com/agent-inject-template-config.env` renders a `.env`-style file
- multiple secret values are written into a single rendered file
- `mychart.envVars` is implemented as a named template in [\_helpers.tpl](./mychart/templates/_helpers.tpl)

How Vault Agent refresh works:

- Vault Agent periodically renews and refreshes secrets when supported
- rendered files are rewritten when leased data changes
- `vault.hashicorp.com/agent-inject-command` can trigger an app-specific reload command after file updates
