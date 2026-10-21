// The only place the UI talks to the API (docs/adr/0007-admin-web-frontend.md, R-67, R-68, R-72).
// Same origin only; the session cookie is HttpOnly and never visible here. The CSRF token is held in this module's
// memory only (never localStorage or sessionStorage) and recovered from GET /api/v1/auth/session after a reload.
// Hints decide nothing: every action is checked again by the server.
// Step-up (R-67): a 401 `step_up_required` asks the registered handler (the TOTP dialog) once and retries the
// request once; a second refusal is returned as an error. Nothing about the code is kept here.

export type Hints = { org_admin: boolean; account_admin: boolean; workflow_author: boolean };

export type SessionInfo = {
  user: { id: number; name: string; email: string; role: string };
  step_up_fresh: boolean;
  hints: Hints;
  csrf_token: string | null;
};

export type ApiError = { status: number; detail: string; reason?: string };

/** Shows the step-up dialog; resolves true once the server accepted a code, false if the person cancelled. */
export type StepUpHandler = () => Promise<boolean>;

let csrfToken: string | null = null;
let stepUpHandler: StepUpHandler | null = null;

/** Only for tests: forget the in-memory token, as a page reload would. */
export function forgetCsrfToken(): void {
  csrfToken = null;
}

export function setStepUpHandler(handler: StepUpHandler | null): void {
  stepUpHandler = handler;
}

async function errorOf(r: Response): Promise<ApiError> {
  // R-72: show the server's status and detail only; 403 and 404 are generic and reveal nothing more.
  if (r.status === 403 || r.status === 404) {
    return { status: r.status, detail: "Not available." };
  }
  try {
    const body = (await r.json()) as { detail?: unknown; reason?: unknown };
    const detail = typeof body.detail === "string" ? body.detail : "The request was not accepted.";
    return typeof body.reason === "string" ? { status: r.status, detail, reason: body.reason }
      : { status: r.status, detail };
  } catch {
    return { status: r.status, detail: "The request was not accepted." };
  }
}

function send(method: "GET" | "POST", path: string, body?: unknown): Promise<Response> {
  const headers: Record<string, string> = {};
  if (method !== "GET") {
    headers["Content-Type"] = "application/json";
    if (csrfToken) {
      headers["X-QMS-CSRF"] = csrfToken;
    }
  }
  return fetch(path, { method, credentials: "same-origin", headers,
    body: method === "GET" ? undefined : JSON.stringify(body ?? {}) });
}

async function request<T>(method: "GET" | "POST", path: string, body?: unknown): Promise<T> {
  let r = await send(method, path, body);
  if (r.status === 401) {
    const error = await errorOf(r);
    if (error.reason !== "step_up_required" || !stepUpHandler || !(await stepUpHandler())) {
      throw error;
    }
    r = await send(method, path, body);              // the one retry
  }
  if (!r.ok) {
    throw await errorOf(r);
  }
  return (await r.json()) as T;
}

/** The signed-in person, or null when nobody is signed in. Refreshes the in-memory CSRF token. */
export async function loadSession(): Promise<SessionInfo | null> {
  const r = await fetch("/api/v1/auth/session", { credentials: "same-origin" });
  if (r.status === 401) {
    csrfToken = null;
    return null;
  }
  if (!r.ok) {
    throw await errorOf(r);
  }
  const info = (await r.json()) as SessionInfo;
  csrfToken = info.csrf_token;
  return info;
}

/** Sign in with email, password and a current authenticator code (R-3). Keeps the CSRF token in memory. */
export async function signIn(email: string, password: string, code: string): Promise<void> {
  const r = await send("POST", "/api/v1/auth/login", { email, password, code });
  if (!r.ok) {
    throw await errorOf(r);
  }
  csrfToken = ((await r.json()) as { csrf_token: string }).csrf_token;
}

/** End the session on the server and forget the in-memory token, whatever the server answered. */
export async function signOut(): Promise<void> {
  try {
    const r = await send("POST", "/api/v1/auth/logout");
    if (!r.ok && r.status !== 401) {
      throw await errorOf(r);
    }
  } finally {
    csrfToken = null;
  }
}

/** Confirm with a current authenticator code; the code is sent once and not kept. */
export async function stepUp(code: string): Promise<void> {
  const r = await send("POST", "/api/v1/auth/step-up", { code });
  if (!r.ok) {
    throw await errorOf(r);
  }
}

export function get<T>(path: string): Promise<T> {
  return request<T>("GET", path);
}

/** An unsafe request with the in-memory CSRF token. */
export function post<T>(path: string, body: unknown): Promise<T> {
  return request<T>("POST", path, body);
}
