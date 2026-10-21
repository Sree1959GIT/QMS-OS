// A read-only list of departments (MVP-1 slice 10b): the first call to an /api/v1/org/ route, which needs a fresh
// step-up (R-41). Creating, changing and deactivating departments, and the people screens, follow in 10c.
import { useState } from "react";

import { type ApiError, get } from "./api";

type Department = { id: number; code: string; name: string; active: boolean };

export function Departments() {
  const [rows, setRows] = useState<Department[] | null>(null);
  const [error, setError] = useState<ApiError | null>(null);

  async function load() {
    setError(null);
    try {
      setRows(await get<Department[]>("/api/v1/org/departments"));
    } catch (err) {
      setRows(null);
      setError(err as ApiError);
    }
  }

  return (
    <section aria-label="Departments">
      <h2>Departments</h2>
      <button type="button" onClick={() => void load()}>Show departments</button>
      {error && <p role="alert">{error.detail}</p>}
      {rows && (
        <ul>
          {rows.map((d) => <li key={d.id}>{d.code} {d.name}{d.active ? "" : " (inactive)"}</li>)}
        </ul>
      )}
    </section>
  );
}
