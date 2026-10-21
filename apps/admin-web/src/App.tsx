// The application shell (MVP-1 slice 10b): restores the session on load (GET /api/v1/auth/session), signs in and
// out, and shows the step-up dialog when a request needs a fresh authenticator code. The screens follow in 10c to
// 10f (docs/ROADMAP.md, Slice 10 steps).
import { useCallback, useEffect, useState } from "react";

import { type ApiError, loadSession, type SessionInfo, setStepUpHandler, signOut } from "./api";
import { Departments } from "./Departments";
import { SignIn } from "./SignIn";
import { StepUpDialog } from "./StepUpDialog";

type State = { kind: "loading" } | { kind: "signed-out" } | { kind: "signed-in"; session: SessionInfo }
  | { kind: "error"; error: ApiError };

export function App() {
  const [state, setState] = useState<State>({ kind: "loading" });
  const [stepUpPending, setStepUpPending] = useState<((confirmed: boolean) => void) | null>(null);

  const refresh = useCallback(() => {
    loadSession()
      .then((session) => setState(session ? { kind: "signed-in", session } : { kind: "signed-out" }))
      .catch((error: ApiError) => setState({ kind: "error", error }));
  }, []);

  useEffect(() => {
    refresh();
    setStepUpHandler(() => new Promise<boolean>((resolve) => setStepUpPending(() => resolve)));
    return () => setStepUpHandler(null);
  }, [refresh]);

  function stepUpDone(confirmed: boolean) {
    stepUpPending?.(confirmed);
    setStepUpPending(null);
  }

  async function doSignOut() {
    try {
      await signOut();
    } finally {
      setState({ kind: "signed-out" });
    }
  }

  return (
    <main>
      <h1>QMS OS Admin</h1>
      <p>Synthetic data only.</p>
      {state.kind === "loading" && <p>Loading…</p>}
      {state.kind === "signed-out" && (
        <>
          <p>Not signed in.</p>
          <SignIn onSignedIn={refresh} />
        </>
      )}
      {state.kind === "signed-in" && (
        <>
          <p>Signed in as {state.session.user.name}.</p>
          <button type="button" onClick={() => void doSignOut()}>Sign out</button>
          {state.session.hints.org_admin && <Departments />}
        </>
      )}
      {state.kind === "error" && <p role="alert">{state.error.detail}</p>}
      {stepUpPending && <StepUpDialog onDone={stepUpDone} />}
    </main>
  );
}
