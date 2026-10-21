// The application shell (MVP-1 slice 10a-2): shows who is signed in. Sign-in, step-up and the screens follow in
// 10b to 10f (docs/adr/0007-admin-web-frontend.md).
import { useEffect, useState } from "react";

import { type ApiError, loadSession, type SessionInfo } from "./api";

type State = { kind: "loading" } | { kind: "signed-out" } | { kind: "signed-in"; session: SessionInfo }
  | { kind: "error"; error: ApiError };

export function App() {
  const [state, setState] = useState<State>({ kind: "loading" });

  useEffect(() => {
    loadSession()
      .then((session) => setState(session ? { kind: "signed-in", session } : { kind: "signed-out" }))
      .catch((error: ApiError) => setState({ kind: "error", error }));
  }, []);

  return (
    <main>
      <h1>QMS OS Admin</h1>
      <p>Synthetic data only.</p>
      {state.kind === "loading" && <p>Loading…</p>}
      {state.kind === "signed-out" && <p>Not signed in.</p>}
      {state.kind === "signed-in" && <p>Signed in as {state.session.user.name}.</p>}
      {state.kind === "error" && <p role="alert">{state.error.detail}</p>}
    </main>
  );
}
