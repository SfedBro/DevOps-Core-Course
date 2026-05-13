# Lab 17 - Cloudflare Workers Edge Deployment

## Deployment Summary

Worker project path: `labs/lab17/edge-api`

Worker name: `sfedbro-edge-api-lab17`

Public URL after deployment:

```text
https://sfedbro-edge-api-lab17.lab17sb.workers.dev
```

Main routes:

| Route | Purpose |
| --- | --- |
| `/` | Application metadata and route list |
| `/health` | Health check endpoint |
| `/edge` | Cloudflare edge request metadata |
| `/config` | Plaintext vars and secret-presence verification |
| `/counter` | Workers KV-backed persistent counter |

Configuration used:

- Plaintext vars in `wrangler.jsonc`: `APP_NAME`, `COURSE_NAME`, `APP_ENV`
- Secrets configured with Wrangler: `API_TOKEN`, `ADMIN_EMAIL`
- KV binding: `SETTINGS`
- `workers_dev: true` for the required `workers.dev` URL
- Observability enabled in `wrangler.jsonc`

Plaintext vars are acceptable for non-sensitive configuration because they are committed in `wrangler.jsonc`. Secrets are configured with `wrangler secret put` and are available only through the Worker runtime `env` object.

## Implementation

The Worker is implemented in TypeScript at `labs/lab17/edge-api/src/index.ts`.

The API preserves operational concerns from earlier labs without using Docker:

- routing with explicit HTTP paths
- health checks via `/health`
- runtime metadata via `/edge`
- configuration via environment variables
- secret handling through `env`
- persistence through Workers KV
- console logs for production observability

## Commands

Install and validate locally:

```powershell
cd labs\lab17\edge-api
npm install
Copy-Item .dev.vars.example .dev.vars
npm run typecheck
npm run dev
```

Local route checks:

```powershell
curl http://127.0.0.1:8787/
curl http://127.0.0.1:8787/health
curl http://127.0.0.1:8787/edge
curl http://127.0.0.1:8787/config
curl http://127.0.0.1:8787/counter
```

Cloudflare setup:

```powershell
cd labs\lab17\edge-api
npx wrangler login
npx wrangler whoami
npx wrangler kv namespace create SETTINGS
```

Wrangler created the KV namespace and updated `wrangler.jsonc` with this binding:

```json
"binding": "SETTINGS",
"id": "7966fb3d76094e8c875b19ea311d9e33"
```

Create secrets:

```powershell
npx wrangler secret put API_TOKEN
npx wrangler secret put ADMIN_EMAIL
```

Deploy and verify:

```powershell
npm run deploy
curl https://sfedbro-edge-api-lab17.lab17sb.workers.dev/health
curl https://sfedbro-edge-api-lab17.lab17sb.workers.dev/edge
curl https://sfedbro-edge-api-lab17.lab17sb.workers.dev/config
curl https://sfedbro-edge-api-lab17.lab17sb.workers.dev/counter
curl https://sfedbro-edge-api-lab17.lab17sb.workers.dev/counter
```

Operations:

```powershell
npm run tail
npm run deployments
npx wrangler rollback
```

## Evidence

Local evidence generated before Cloudflare deployment:

```powershell
PS C:\Users\Admin\Desktop\DevOps-Core-Course\labs\lab17\edge-api> npm run typecheck

> sfedbro-edge-api-lab17@1.0.0 typecheck
> tsc --noEmit
```

```powershell
PS C:\Users\Admin\Desktop\DevOps-Core-Course\labs\lab17\edge-api> npx wrangler --version
4.90.1
```

Local route checks through Wrangler dev:

```json
GET /health
{"status":"healthy","app":"sfedbro-edge-api-lab17","environment":"lab17","timestamp":"2026-05-13T20:57:06.703Z"}
```

```json
GET /edge
{"colo":"IAD","country":"US","city":"Manassas","asn":214996,"httpProtocol":"HTTP/1.1","tlsVersion":"TLSv1.3","timezone":"America/New_York"}
```

```json
GET /config
{"appName":"sfedbro-edge-api-lab17","courseName":"devops-core","environment":"lab17","apiTokenConfigured":false,"adminEmailConfigured":false,"note":"Secrets are consumed through env but never returned in plaintext."}
```

```json
GET /counter
{"key":"visits","visits":1,"persistedIn":"Workers KV"}
```

### Wrangler Authentication

```text
PS ...\labs\lab17\edge-api> npx wrangler whoami

Getting User settings...
You are logged in with an OAuth Token, associated with the email sfedbro@mail.ru.
Account Name: Sfedbro@mail.ru's Account
Account ID: 0b97c27106b0a784f10cdb0b9b59368a
```

### Local Type Check

```text
PS ...\labs\lab17\edge-api> npm run typecheck

> sfedbro-edge-api-lab17@1.0.0 typecheck
> tsc --noEmit
```

### Deployments

First deployment:

```text
Deployed sfedbro-edge-api-lab17 triggers (46.21 sec)
  https://sfedbro-edge-api-lab17.lab17sb.workers.dev
Current Version ID: 77980542-6179-40fa-98c7-c32c3d18724d
```

Second deployment after KV counter verification:

```text
Deployed sfedbro-edge-api-lab17 triggers (1.25 sec)
  https://sfedbro-edge-api-lab17.lab17sb.workers.dev
Current Version ID: 486a55f1-b3e4-46c9-b768-04ae0cdd79cd
```

### Public `/health`

```json
{"status":"healthy","app":"sfedbro-edge-api-lab17","environment":"lab17","timestamp":"2026-05-13T21:13:20.027Z"}
```

### Public `/edge`

```json
{"colo":"IAD","country":"US","city":"Manassas","asn":214996,"httpProtocol":"HTTP/2","tlsVersion":"TLSv1.3","timezone":"America/New_York"}
```

### Public `/config`

```json
{"appName":"sfedbro-edge-api-lab17","courseName":"devops-core","environment":"lab17","apiTokenConfigured":true,"adminEmailConfigured":true,"note":"Secrets are consumed through env but never returned in plaintext."}
```

### KV Persistence

Call `/counter` twice, redeploy, then call `/counter` again.

```json
Before redeploy:
{"key":"visits","visits":1,"persistedIn":"Workers KV"}
{"key":"visits","visits":2,"persistedIn":"Workers KV"}

After redeploy:
{"key":"visits","visits":3,"persistedIn":"Workers KV"}
```

### Logs

```json
{
  "outcome": "ok",
  "scriptVersion": {
    "id": "486a55f1-b3e4-46c9-b768-04ae0cdd79cd"
  },
  "scriptName": "sfedbro-edge-api-lab17",
  "logs": [
    {
      "message": [
        "{\"event\":\"request\",\"path\":\"/edge\",\"method\":\"GET\",\"colo\":\"IAD\",\"country\":\"US\"}"
      ],
      "level": "log",
      "timestamp": 1778706823946
    }
  ]
}
```

### Deployment History

```text
Created:     2026-05-13T21:09:47.807Z
Author:      sfedbro@mail.ru
Source:      Unknown (deployment)
Version(s):  (100%) 77980542-6179-40fa-98c7-c32c3d18724d

Created:     2026-05-13T21:13:07.587Z
Author:      sfedbro@mail.ru
Source:      Unknown (deployment)
Version(s):  (100%) 486a55f1-b3e4-46c9-b768-04ae0cdd79cd
```

Rollback was not required because the latest version was healthy. If rollback were needed, the operational command would be:

```powershell
npx wrangler rollback
```

### Screenshots

Store screenshots in `labs/lab17/screenshots/`:

- `lab17_1_cloudflare_worker_dashboard.png` - Worker dashboard page
- `lab17_2_worker_metrics.png` - metrics showing requests/errors/execution data
- `lab17_3_worker_logs_or_tail.png` - logs from dashboard or terminal
- `lab17_4_deployments.png` - deployment history or rollback screen

## Edge Behavior

Cloudflare Workers run on Cloudflare's global edge network. The same Worker code is deployed globally and runs close to the user based on Cloudflare routing. The `/edge` endpoint reads `request.cf` metadata such as `colo`, `country`, `city`, `asn`, `httpProtocol`, and `tlsVersion`.

This differs from VM or PaaS platforms where I usually choose one or more regions manually. With Workers, there is no separate "deploy to 3 regions" step because global distribution is part of the Workers platform. The platform decides where a request executes based on the incoming request path through Cloudflare's network.

Routing concepts:

- `workers.dev` gives a quick public URL for a Worker without owning a domain.
- Routes attach a Worker to paths on an existing Cloudflare-managed zone.
- Custom Domains map a domain or subdomain directly to a Worker.

This lab uses `workers.dev` because it is the required and simplest deployment path.

## Kubernetes vs Cloudflare Workers

| Aspect | Kubernetes | Cloudflare Workers |
| --- | --- | --- |
| Setup complexity | Requires cluster, manifests, networking, image registry, and runtime resources | Requires account, Wrangler config, and deployment command |
| Deployment speed | Slower because images must be built, pushed, pulled, and rolled out | Fast because source is bundled and deployed to Workers |
| Global distribution | Manual multi-region clusters or external load balancing | Global edge distribution is built in |
| Cost for small apps | Cluster overhead exists even for small workloads | Free or low-cost for lightweight request-driven APIs |
| State/persistence model | Uses volumes, databases, Secrets, ConfigMaps, and operators | Uses platform bindings such as KV, D1, R2, Durable Objects, vars, and secrets |
| Control/flexibility | Very high control over runtime, networking, sidecars, probes, and workloads | More constrained runtime with no arbitrary long-running containers |
| Best use case | Complex services, long-running processes, internal platforms, custom networking | Lightweight APIs, edge logic, redirects, request enrichment, globally distributed functions |

## When To Use Each

Use Kubernetes when the application needs containers, custom runtimes, background workers, service mesh, complex networking, persistent volumes, or strict control over deployment topology.

Use Cloudflare Workers when the workload is HTTP-driven, latency-sensitive, globally distributed, and can fit the serverless edge runtime model.

My recommendation is to use Workers for small edge APIs and request-processing logic, and Kubernetes for larger systems where container control and platform flexibility matter more than deployment simplicity.

## Reflection

Cloudflare Workers felt simpler than Kubernetes because there are no Pods, Services, Deployments, ingress controllers, image pulls, or cluster capacity planning. A working API can be deployed with Wrangler and immediately exposed through `workers.dev`.

The constrained part is that Workers is not a Docker host. I cannot deploy the existing container image directly, run arbitrary daemons, or rely on Kubernetes-native patterns such as sidecars and volumes. The application must be written for the Workers runtime and use platform bindings for secrets, configuration, and persistence.

The biggest conceptual change is that infrastructure becomes less about managing nodes and more about declaring bindings and routes. That is useful for this lab because the app is a small HTTP API, but it would not replace Kubernetes for every workload from the previous labs.
