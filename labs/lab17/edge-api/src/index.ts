export interface Env {
  APP_NAME: string;
  COURSE_NAME: string;
  APP_ENV: string;
  API_TOKEN?: string;
  ADMIN_EMAIL?: string;
  SETTINGS?: KVNamespace;
}

type JsonBody = Record<string, unknown>;

const json = (body: JsonBody, init: ResponseInit = {}) =>
  Response.json(body, {
    headers: {
      "cache-control": "no-store",
      ...init.headers,
    },
    status: init.status ?? 200,
  });

const notFound = (path: string) =>
  json(
    {
      error: "not_found",
      path,
      routes: ["/", "/health", "/edge", "/config", "/counter"],
    },
    { status: 404 },
  );

async function handleCounter(env: Env): Promise<Response> {
  if (!env.SETTINGS) {
    return json(
      {
        error: "kv_not_configured",
        message: "Bind a Workers KV namespace named SETTINGS in wrangler.jsonc.",
      },
      { status: 503 },
    );
  }

  const key = "visits";
  const currentValue = await env.SETTINGS.get(key);
  const visits = Number(currentValue ?? "0") + 1;
  await env.SETTINGS.put(key, String(visits));

  return json({
    key,
    visits,
    persistedIn: "Workers KV",
  });
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);

    console.log(
      JSON.stringify({
        event: "request",
        path: url.pathname,
        method: request.method,
        colo: request.cf?.colo ?? "local",
        country: request.cf?.country ?? "local",
      }),
    );

    if (request.method !== "GET") {
      return json(
        {
          error: "method_not_allowed",
          allowedMethods: ["GET"],
        },
        { status: 405 },
      );
    }

    if (url.pathname === "/") {
      return json({
        app: env.APP_NAME,
        course: env.COURSE_NAME,
        environment: env.APP_ENV,
        message: "Hello from Cloudflare Workers",
        routes: ["/", "/health", "/edge", "/config", "/counter"],
        timestamp: new Date().toISOString(),
      });
    }

    if (url.pathname === "/health") {
      return json({
        status: "healthy",
        app: env.APP_NAME,
        environment: env.APP_ENV,
        timestamp: new Date().toISOString(),
      });
    }

    if (url.pathname === "/edge") {
      return json({
        colo: request.cf?.colo ?? "local",
        country: request.cf?.country ?? "local",
        city: request.cf?.city ?? "local",
        asn: request.cf?.asn ?? "local",
        httpProtocol: request.cf?.httpProtocol ?? "local",
        tlsVersion: request.cf?.tlsVersion ?? "local",
        timezone: request.cf?.timezone ?? "local",
      });
    }

    if (url.pathname === "/config") {
      return json({
        appName: env.APP_NAME,
        courseName: env.COURSE_NAME,
        environment: env.APP_ENV,
        apiTokenConfigured: Boolean(env.API_TOKEN),
        adminEmailConfigured: Boolean(env.ADMIN_EMAIL),
        note: "Secrets are consumed through env but never returned in plaintext.",
      });
    }

    if (url.pathname === "/counter") {
      return handleCounter(env);
    }

    return notFound(url.pathname);
  },
} satisfies ExportedHandler<Env>;
