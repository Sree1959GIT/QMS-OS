// Sign-in with email, password and a current authenticator code (R-3, R-67). The fields live in this form's state
// only and are cleared after every attempt; nothing is written to web storage.
import { type FormEvent, useState } from "react";

import { type ApiError, signIn } from "./api";
import { ErrorMessage } from "./ui";

export function SignIn({ onSignedIn }: { onSignedIn: () => void }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [code, setCode] = useState("");
  const [error, setError] = useState<ApiError | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await signIn(email, password, code);
      onSignedIn();
    } catch (err) {
      setError(err as ApiError);
    } finally {
      setPassword("");
      setCode("");
      setBusy(false);
    }
  }

  return (
    <form aria-label="Sign in" onSubmit={(e) => void submit(e)}>
      <h2>Sign in</h2>
      <label>
        Email
        <input type="email" name="email" autoComplete="username" required value={email}
          onChange={(e) => setEmail(e.target.value)} />
      </label>
      <label>
        Password
        <input type="password" name="password" autoComplete="current-password" required value={password}
          onChange={(e) => setPassword(e.target.value)} />
      </label>
      <label>
        Authenticator code
        <input name="code" inputMode="numeric" autoComplete="off" required value={code}
          onChange={(e) => setCode(e.target.value)} />
      </label>
      <button type="submit" disabled={busy}>Sign in</button>
      <ErrorMessage error={error} />
    </form>
  );
}
