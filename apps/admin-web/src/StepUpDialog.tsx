// The step-up dialog (R-67): asks for a current authenticator code when the server answers 401 `step_up_required`.
// It caches nothing: no "remember" option, the code is cleared after every attempt and on close, and it is never
// written to web storage. The request that needed the step-up is retried once by api.ts.
import { type FormEvent, useState } from "react";

import { type ApiError, stepUp } from "./api";
import { ErrorMessage } from "./ui";

export function StepUpDialog({ onDone }: { onDone: (confirmed: boolean) => void }) {
  const [code, setCode] = useState("");
  const [error, setError] = useState<ApiError | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await stepUp(code);
      setCode("");
      onDone(true);
    } catch (err) {
      setCode("");
      setError(err as ApiError);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div role="dialog" aria-modal="true" aria-labelledby="step-up-title">
      <form onSubmit={(e) => void submit(e)}>
        <h2 id="step-up-title">Confirm with your authenticator</h2>
        <label>
          Authenticator code
          <input name="step-up-code" inputMode="numeric" autoComplete="off" required value={code}
            onChange={(e) => setCode(e.target.value)} />
        </label>
        <button type="submit" disabled={busy}>Confirm</button>
        <button type="button" onClick={() => { setCode(""); onDone(false); }}>Cancel</button>
        <ErrorMessage error={error} />
      </form>
    </div>
  );
}
