// Workflow grants (ADR 0008; R-74, R-75): list, add and revoke through /api/v1/org/workflow-grants. A grant lets
// every person with the QMS role read the workflow guidelines classified at or below its ceiling, with their
// templates, versions and cases. The server refuses a change to the grants of the org admin's own QMS role; the screen
// does not guess it. The guidelines listed are the ones the signed-in person can read, with their classification.
import { type FormEvent, useCallback, useEffect, useState } from "react";

import { get, post } from "./api";
import { ErrorMessage, LEVELS, plain, ROLES, Select, useRows } from "./ui";

export type WorkflowGrant = { id: number; role: string; max_classification: string; active: boolean };
export type Guideline = { id: number; title: string; department_id: number; classification: string; active: boolean };

const PATH = "/api/v1/org/workflow-grants";

type Data = { grants: WorkflowGrant[]; guidelines: Guideline[] };

export function WorkflowGrants() {
  const load = useCallback(async (): Promise<Data> => {
    const grants = await get<WorkflowGrant[]>(PATH);
    const guidelines = await get<Guideline[]>("/api/v1/workflow/guidelines");
    return { grants, guidelines };
  }, []);
  const { rows, error, busy, reload, act } = useRows(load);
  const [role, setRole] = useState("VIEWER");
  const [ceiling, setCeiling] = useState("internal");

  useEffect(() => { void reload(); }, [reload]);

  async function add(e: FormEvent) {
    e.preventDefault();
    await act(() => post(PATH, { role, max_classification: ceiling }));
  }

  return (
    <section aria-label="Workflow grants">
      <h2>Workflow grants</h2>
      <button type="button" onClick={() => void reload()}>Refresh</button>
      <ErrorMessage error={error} />
      {rows && (
        <>
          <table aria-label="Grants">
            <thead><tr><th>Id</th><th>Role</th><th>Ceiling</th><th>Status</th><th /></tr></thead>
            <tbody>
              {rows.grants.map((g) => (
                <tr key={g.id}>
                  <td>{g.id}</td><td>{g.role}</td><td>{g.max_classification}</td>
                  <td>{g.active ? "active" : "revoked"}</td>
                  <td>
                    {g.active && <button type="button" aria-label={`Revoke workflow grant ${g.id}`} disabled={busy}
                      onClick={() => void act(() => post(`${PATH}/${g.id}/revoke`, {}))}>Revoke</button>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <h3>Guidelines you can read</h3>
          <table aria-label="Guidelines">
            <thead><tr><th>Id</th><th>Title</th><th>Classification</th></tr></thead>
            <tbody>
              {rows.guidelines.map((g) => (
                <tr key={g.id}><td>{g.id}</td><td>{g.title}</td><td>{g.classification}</td></tr>
              ))}
            </tbody>
          </table>
        </>
      )}
      <form aria-label="New workflow grant" onSubmit={(e) => void add(e)}>
        <h3>New workflow grant</h3>
        <Select label="Role" value={role} options={plain(ROLES)} onChange={setRole} />
        <Select label="Ceiling" value={ceiling} options={plain(LEVELS)} onChange={setCeiling} />
        <button type="submit" disabled={busy}>Add workflow grant</button>
      </form>
    </section>
  );
}
