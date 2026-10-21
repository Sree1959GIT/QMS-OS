// Shared pieces of the screens (MVP-1 slice 10). Errors show the status and the server's detail only (R-72; api.ts
// already makes 403 and 404 generic). The select lists only offer values; the server validates every one of them.
import { useCallback, useState } from "react";

import type { ApiError } from "./api";

export const ROLES = ["MA", "AUDITOR", "AUDITEE", "MD", "VIEWER"];
export const LEVELS = ["public", "internal", "confidential"];

export function ErrorMessage({ error }: { error: ApiError | null }) {
  return error ? <p role="alert">Error {error.status}: {error.detail}</p> : null;
}

/**
 * The screens' data: `rows` holds what the last response contained and nothing else; every successful action is
 * followed by a fresh load, so no data or permission is kept between requests.
 */
export function useRows<T>(load: () => Promise<T>) {
  const [rows, setRows] = useState<T | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [busy, setBusy] = useState(false);

  const reload = useCallback(async () => {
    try {
      setRows(await load());
      setError(null);
    } catch (err) {
      setRows(null);
      setError(err as ApiError);
    }
  }, [load]);

  const act = useCallback(async (action: () => Promise<unknown>): Promise<boolean> => {
    setBusy(true);
    setError(null);
    try {
      await action();
      await reload();
      return true;
    } catch (err) {
      setError(err as ApiError);          // no reload: a cancelled step-up must not open the dialog again
      return false;
    } finally {
      setBusy(false);
    }
  }, [reload]);

  return { rows, error, setError, busy, reload, act };
}

export function Select({ label, value, options, onChange, allowNone }: { label: string; value: string;
  options: { value: string; text: string }[]; onChange: (v: string) => void; allowNone?: string }) {
  return (
    <label>
      {label}
      <select value={value} onChange={(e) => onChange(e.target.value)}>
        {allowNone !== undefined && <option value="">{allowNone}</option>}
        {options.map((o) => <option key={o.value} value={o.value}>{o.text}</option>)}
      </select>
    </label>
  );
}

export const plain = (values: string[]) => values.map((v) => ({ value: v, text: v }));
