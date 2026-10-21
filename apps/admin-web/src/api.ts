// The only place the UI talks to the API (docs/adr/0007-admin-web-frontend.md, R-67, R-68, R-72).
// Same origin only; the session cookie is HttpOnly and never visible here. The CSRF token is held in this module's
// memory only (never localStorage or sessionStorage) and recovered from GET /api/v1/auth/session after a reload.
// Hints decide nothing: every action is checked again by the server.

export type Hints = { org_admin: boolean; account_admin: boolean; workflow_author: boolean };

export type SessionInfo = {
  user: { id: number; name: string; email: string; role: string };
  step_up_fresh: boolean;
  hints: Hints;
  csrf_token: string | null;
};

export type ApiError = { status: number; detail: string; reason?: string };

let csrfToken: string | null = null;

/** Only for tests: forget the in-memory token, as a page reload would. */
export function forgetCsrfToken(): void {
  csrfToken = null;
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

/** An unsafe request with the in-memory CSRF token. */
export async function post<T>(path: string, body: unknown): Promise<T> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (csrfToken) {
    headers["X-QMS-CSRF"] = csrfToken;
  }
  const r = await fetch(path, { method: "POST", credentials: "same-origin", headers, body: JSON.stringify(body) });
  if (!r.ok) {
    throw await errorOf(r);
  }
  return (await r.json()) as T;
}
