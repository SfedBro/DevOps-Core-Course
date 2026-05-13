# Lab 17 Edge API

Cloudflare Workers project for Lab 17.

## Local Development

```bash
npm install
cp .dev.vars.example .dev.vars
npm run typecheck
npm run dev
curl http://127.0.0.1:8787/health
curl http://127.0.0.1:8787/edge
```

## Cloudflare Setup

```bash
npx wrangler login
npx wrangler whoami
npx wrangler kv namespace create SETTINGS
```

The KV namespace is already bound in `wrangler.jsonc` as `SETTINGS`. Configure secrets:

```bash
npx wrangler secret put API_TOKEN
npx wrangler secret put ADMIN_EMAIL
```

Deploy:

```bash
npm run deploy
```

Useful production checks:

```bash
curl https://sfedbro-edge-api-lab17.lab17sb.workers.dev/health
curl https://sfedbro-edge-api-lab17.lab17sb.workers.dev/edge
curl https://sfedbro-edge-api-lab17.lab17sb.workers.dev/counter
npm run tail
npm run deployments
```
