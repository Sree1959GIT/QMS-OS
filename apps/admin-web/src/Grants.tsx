// Role grants (MVP-1 slice 10d): list, add and revoke through /api/v1/org/role-grants (services/org.py; slice 3,
// R-31, R-43). The server refuses a change to the grants of the org admin's own QMS role; the screen does not guess it.
import { type FormEvent, useCallback, useEffect, useState } from "react";

import { get, post } from "./api";
import { ErrorMessage, KINDS, LEVELS, plain, ROLES, SCOPES, Select, useRows } from "./ui";

export type RoleGrant = { id: number; role: string; resource_kind: string; max_classification: string;
  scope: string; active: boolean };

const PATH = "/api/v1/org/role-grants";

export function Grants() {
  const load = useCallback(() => get<RoleGrant[]>(PATH), []);
  const { rows, error, busy, reload, act } = useRows(load);
  const [role, setRole] = useState("VIEWER");
  const [kind, setKind] = useState("department");
  const [ceiling, setCeiling] = useState("internal");
  const [scope, setScope] = useState("all");

  useEffect(() => { void reload(); }, [reload]);

  async function add(e: FormEvent) {
    e.preventDefault();
    await act(() => post(PATH, { role, resource_kind: kind, max_classification: ceiling, scope }));
  }

  return (
    <section aria-label="Role grants">
      <h2>Role grants</h2>
      <button type="button" onClick={() => void reload()}>Refresh</button>
      <ErrorMessage error={error} />
      {rows && (
        <table>
          <thead><tr><th>Id</th><th>Role</th><th>Resource</th><th>Ceiling</th><th>Scope</th><th>Status</th><th /></tr></thead>
          <tbody>
            {rows.map((g) => (
              <tr key={g.id}>
                <td>{g.id}</td><td>{g.role}</td><td>{g.resource_kind}</td><td>{g.max_classification}</td>
                <td>{g.scope}</td><td>{g.active ? "active" : "revoked"}</td>
                <td>
                  {g.active && <button type="button" aria-label={`Revoke grant ${g.id}`} disabled={busy}
                    onClick={() => void act(() => post(`${PATH}/${g.id}/revoke`, {}))}>Revoke</button>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      <form aria-label="New role grant" onSubmit={(e) => void add(e)}>
        <h3>New role grant</h3>
        <Select label="Role" value={role} options={plain(ROLES)} onChange={setRole} />
        <Select label="Resource" value={kind} options={plain(KINDS)} onChange={setKind} />
        <Select label="Ceiling" value={ceiling} options={plain(LEVELS)} onChange={setCeiling} />
        <Select label="Scope" value={scope} options={plain(SCOPES)} onChange={setScope} />
        <button type="submit" disabled={busy}>Add grant</button>
      </form>
    </section>
  );
}
