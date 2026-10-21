// The application shell (MVP-1 slice 10): restores the session on load (GET /api/v1/auth/session), signs in and
// out, shows the step-up dialog when a request needs a fresh authenticator code, and opens one screen at a time.
// The hints from the session only hide the org screens' menu; the server decides every request (R-68). Each screen
// loads its data when it opens and keeps nothing after it closes (docs/ROADMAP.md, Slice 10 steps).
import { useCallback, useEffect, useState } from "react";

import { type ApiError, loadSession, type SessionInfo, setStepUpHandler, signOut } from "./api";
import { Access } from "./Access";
import { Agents } from "./Agents";
import { Departments } from "./Departments";
import { Grants } from "./Grants";
import { People } from "./People";
import { Projects } from "./Projects";
import { SignIn } from "./SignIn";
import { StepUpDialog } from "./StepUpDialog";
import { ErrorMessage } from "./ui";
import { WorkflowGrants } from "./WorkflowGrants";

type State = { kind: "loading" } | { kind: "signed-out" } | { kind: "signed-in"; session: SessionInfo }
  | { kind: "error"; error: ApiError };

const SCREENS = {
  departments: { title: "Departments", view: Departments },
  people: { title: "People", view: People },
  grants: { title: "Role grants", view: Grants },
  workflowGrants: { title: "Workflow grants", view: WorkflowGrants },
  projects: { title: "Projects", view: Projects },
  access: { title: "Access preview", view: Access },
  agents: { title: "Agents", view: Agents },
};
type Screen = keyof typeof SCREENS;

export function App() {
  const [state, setState] = useState<State>({ kind: "loading" });
  const [screen, setScreen] = useState<Screen | null>(null);
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
      setScreen(null);
      setState({ kind: "signed-out" });
    }
  }

  const View = screen ? SCREENS[screen].view : null;

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
          {state.session.hints.org_admin && (
            <nav aria-label="Organisation">
              {(Object.keys(SCREENS) as Screen[]).map((key) => (
                <button key={key} type="button" aria-pressed={screen === key} onClick={() => setScreen(key)}>
                  {SCREENS[key].title}
                </button>
              ))}
            </nav>
          )}
          {View && <View key={screen} />}
        </>
      )}
      {state.kind === "error" && <ErrorMessage error={state.error} />}
      {stepUpPending && <StepUpDialog onDone={stepUpDone} />}
    </main>
  );
}
