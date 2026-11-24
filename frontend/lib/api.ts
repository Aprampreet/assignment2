const prefix = "/api/medora/";

export class ApiError extends Error {
  constructor(public status: number, message: string, public fields: Record<string, string[] | string> = {}) {
    super(message);
  }
}

let csrfFlight: Promise<string> | undefined;
function token() {
  csrfFlight ??= fetch(prefix + "csrf", { cache: "no-store" }).then(async (response) => {
    if (!response.ok) throw new ApiError(response.status, "Request verification is unavailable.");
    return (await response.json()).token as string;
  }).finally(() => { csrfFlight = undefined; });
  return csrfFlight;
}

let refreshFlight: Promise<Response> | undefined;
async function withSessionLock(action: () => Promise<Response>): Promise<Response> {
  return navigator.locks ? await navigator.locks.request("medora-session", action) : action();
}

export function announceSessionChange() {
  if (typeof BroadcastChannel === "undefined") return;
  const channel = new BroadcastChannel("medora-account-changed");
  channel.postMessage("changed");
  channel.close();
}

function refreshSession(): Promise<Response> {
  refreshFlight ??= withSessionLock(() => send("auth/refresh", "POST"))
    .finally(() => { refreshFlight = undefined; });
  return refreshFlight;
}

async function send(path: string, method: string, data?: unknown) {
  const headers = new Headers();
  if (method !== "GET") headers.set("x-csrf-token", await token());
  if (data !== undefined) headers.set("Content-Type", "application/json");
  return fetch(prefix + path, { method, headers, body: data === undefined ? undefined : JSON.stringify(data), cache: "no-store" });
}

export async function api<T>(path: string, method = "GET", data?: unknown): Promise<T> {
  const publicRoute = /^auth\/(login|register)$/.test(path);
  let response: Response;
  if (path === "auth/logout") {
    response = await withSessionLock(async () => {
      await send("auth/refresh", "POST").catch(() => undefined);
      return send(path, method, data);
    });
  } else if (path === "auth/login") {
    response = await withSessionLock(() => send(path, method, data));
  } else {
    response = await send(path, method, data);
  }
  if (!publicRoute && path !== "auth/logout" && response.status === 401) {
    const rotated = await refreshSession();
    response = rotated.ok ? await send(path, method, data) : rotated.clone();
  }
  if ((path === "auth/login" && response.ok)
      || (path === "auth/logout" && (response.ok || response.status === 503))
      || (method === "PATCH" && response.ok && data && typeof data === "object" && "current_password" in data)) {
    announceSessionChange();
  }
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    if (response.status === 401 && !publicRoute) window.dispatchEvent(new Event("medora-session-ended"));
    throw new ApiError(response.status, body.message || "The request could not be completed.", body.field_errors || {});
  }
  return (response.status === 204 ? undefined : await response.json()) as T;
}
