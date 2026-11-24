import { randomBytes, timingSafeEqual } from "node:crypto";
import { NextRequest, NextResponse } from "next/server";

const uuid = "[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}";
const routes: [RegExp, string[]][] = [
  [/^auth\/(login|register|refresh|logout)$/, ["POST"]],
  [/^auth\/me$/, ["GET"]],
  [/^(patients|doctors|mappings|users)$/, ["GET", "POST"]],
  [new RegExp(`^(patients|doctors)/${uuid}$`, "i"), ["GET", "PUT", "DELETE"]],
  [new RegExp(`^mappings/${uuid}$`, "i"), ["GET", "DELETE"]],
  [new RegExp(`^users/${uuid}$`, "i"), ["PATCH"]],
  [/^v1\/(dashboard|audit-logs)$/, ["GET"]],
  [/^v1\/assistant\/chat$/, ["POST"]],
];

const secure = process.env.NODE_ENV === "production" && process.env.MEDORA_LOCAL_HTTP !== "1";
const names = {
  access: secure ? "__Host-medora_access" : "medora_access",
  refresh: secure ? "__Host-medora_refresh" : "medora_refresh",
  csrf: secure ? "__Host-medora_csrf" : "medora_csrf",
};
const cookies = { secure, path: "/", sameSite: "lax" as const };
const cache = { "Cache-Control": "no-store" };
const failure = (status: number, message: string) => NextResponse.json(
  { code: status === 401 ? "authentication_failed" : "gateway_error", message, field_errors: {}, request_id: null },
  { status, headers: cache },
);
const empty = () => new NextResponse(null, { status: 204, headers: cache });

function clear(response: NextResponse) {
  for (const name of [names.access, names.refresh]) {
    response.cookies.set(name, "", { ...cookies, httpOnly: true, maxAge: 0 });
  }
  return response;
}

function csrf(request: NextRequest) {
  const host = request.headers.get("host");
  const protocol = request.headers.get("x-forwarded-proto") || request.nextUrl.protocol.slice(0, -1);
  const origin = host ? `${protocol}://${host}` : "";
  const cookie = request.cookies.get(names.csrf)?.value || "";
  const header = request.headers.get("x-csrf-token") || "";
  return !!host && request.headers.get("origin") === origin &&
    /^[a-f0-9]{64}$/.test(cookie) && /^[a-f0-9]{64}$/.test(header) &&
    timingSafeEqual(Buffer.from(cookie), Buffer.from(header));
}

async function upstream(path: string, method: string, token?: string, body?: string, query = "") {
  const backend = process.env.DJANGO_API_ORIGIN;
  if (!backend) throw new Error("Missing upstream");
  const url = new URL(`/api/${path}/${query}`, backend);
  return fetch(url, {
    method, body, headers: {
      Accept: "application/json",
      ...(body === undefined ? {} : { "Content-Type": "application/json" }),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    cache: "no-store", redirect: "error", signal: AbortSignal.timeout(9000),
  });
}

async function relay(response: Response) {
  if (response.status === 204) return empty();
  if (!response.headers.get("content-type")?.includes("application/json")) {
    return failure(response.ok ? 502 : response.status, "The workspace could not complete the request.");
  }
  const body = await response.json();
  if (body && typeof body === "object") {
    // DRF pagination includes absolute upstream URLs. The client only needs presence.
    if ("results" in body) {
      if (typeof body.next === "string") body.next = true;
      if (typeof body.previous === "string") body.previous = true;
    }
  }
  const headers = new Headers(cache);
  for (const name of ["x-request-id", "retry-after"]) {
    const value = response.headers.get(name);
    if (value) headers.set(name, value);
  }
  return NextResponse.json(body, { status: response.status, headers });
}

function saveTokens(response: NextResponse, data: { access: string; refresh: string }) {
  response.cookies.set(names.access, data.access, { ...cookies, httpOnly: true, maxAge: 300 });
  response.cookies.set(names.refresh, data.refresh, { ...cookies, httpOnly: true, maxAge: 86400 });
  return response;
}

type Context = { params: Promise<{ parts: string[] }> };
async function handle(request: NextRequest, context: Context) {
  const { parts } = await context.params;
  const path = parts.join("/");
  const method = request.method;
  if (method === "GET" && path === "csrf") {
    const current = request.cookies.get(names.csrf)?.value || "";
    const token = /^[a-f0-9]{64}$/.test(current) ? current : randomBytes(32).toString("hex");
    const response = NextResponse.json({ token }, { headers: cache });
    response.cookies.set(names.csrf, token, { ...cookies, httpOnly: true });
    return response;
  }
  if (!routes.some(([pattern, methods]) => pattern.test(path) && methods.includes(method))) {
    return failure(404, "Resource not found.");
  }
  if (method !== "GET" && !csrf(request)) return failure(403, "Request verification failed.");
  const access = request.cookies.get(names.access)?.value;
  const refresh = request.cookies.get(names.refresh)?.value;
  try {
    if (path === "auth/refresh") {
      if (!refresh) return clear(failure(401, "Sign in to continue."));
      if (access && (await upstream("auth/me", "GET", access)).ok) return empty();
      const response = await upstream(path, "POST", undefined, JSON.stringify({ refresh }));
      if (response.ok) return saveTokens(empty(), await response.json());
      return response.status === 401 ? clear(await relay(response)) : relay(response);
    }
    if (path === "auth/logout") {
      if (access && refresh) {
        try {
          const revoked = await upstream(path, "POST", access, JSON.stringify({ refresh }));
          if (!revoked.ok && revoked.status !== 401) {
            return clear(failure(503, "Signed out here. Server revocation could not be confirmed."));
          }
        } catch {
          return clear(failure(503, "Signed out here. Server revocation could not be confirmed."));
        }
      } else if (refresh) {
        return clear(failure(503, "Signed out here. Server revocation could not be confirmed."));
      }
      return clear(empty());
    }
    const isPublic = path === "auth/login" || path === "auth/register";
    if (!isPublic && !access) return failure(401, "Sign in to continue.");
    let body: string | undefined;
    if (method === "POST" || method === "PUT" || method === "PATCH") {
      if (!request.headers.get("content-type")?.startsWith("application/json")) return failure(415, "Send a JSON body.");
      const reader = request.body?.getReader();
      const chunks: Uint8Array[] = [];
      let size = 0;
      if (reader) {
        for (;;) {
          const { done, value } = await reader.read();
          if (done) break;
          size += value.byteLength;
          if (size > 32768) {
            await reader.cancel();
            return failure(413, "Request body is too large.");
          }
          chunks.push(value);
        }
      }
      body = Buffer.concat(chunks).toString("utf8");
    }
    const response = await upstream(path, method, isPublic ? undefined : access, body, request.nextUrl.search);
    if (path === "auth/login") {
      return response.ok ? saveTokens(empty(), await response.json()) : clear(await relay(response));
    }
    const result = await relay(response);
    if (method === "PATCH" && path.startsWith("users/") && response.ok && body) {
      try { if ("current_password" in JSON.parse(body)) return clear(result); } catch { /* Invalid bodies are rejected upstream. */ }
    }
    return result;
  } catch {
    return failure(503, "The workspace is temporarily unavailable. Try again.");
  }
}

export const GET = handle;
export const POST = handle;
export const PUT = handle;
export const PATCH = handle;
export const DELETE = handle;
