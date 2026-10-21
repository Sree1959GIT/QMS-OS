// Departments (MVP-1 slice 10c): list, create, update, deactivate and reactivate through /api/v1/org/departments
// (services/org.py; slice 2 rules). Org admin with a fresh step-up only (R-30, R-41): the server decides every action.
import { type FormEvent, useCallback, useEffect, useState } from "react";

import { get, patch, post } from "./api";
import { ErrorMessage, LEVELS, plain, Select, useRows } from "./ui";

export type Department = { id: number; code: string; name: string; head_user_id: number | null; active: boolean;
  classification: string };

const PATH = "/api/v1/org/departments";

function EditDepartment({ d, onSave, onCancel }: { d: Department;
  onSave: (changes: Partial<Department>) => void; onCancel: () => void }) {
  const [name, setName] = useState(d.name);
  const [classification, setClassification] = useState(d.classification);
  const [head, setHead] = useState(d.head_user_id === null ? "" : String(d.head_user_id));

  function submit(e: FormEvent) {
    e.preventDefault();
    onSave({ name, classification, head_user_id: head === "" ? null : Number(head) });
  }

  return (
    <form aria-label={`Edit department ${d.code}`} onSubmit={submit}>
      <label>Name<input value={name} required onChange={(e) => setName(e.target.value)} /></label>
      <Select label="Classification" value={classification} options={plain(LEVELS)} onChange={setClassification} />
      <label>Head (person id)<input value={head} inputMode="numeric" onChange={(e) => setHead(e.target.value)} />
      </label>
      <button type="submit">Save</button>
      <button type="button" onClick={onCancel}>Cancel</button>
    </form>
  );
}

export function Departments() {
  const load = useCallback(() => get<Department[]>(PATH), []);
  const { rows, error, busy, reload, act } = useRows(load);
  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [editing, setEditing] = useState<number | null>(null);

  useEffect(() => { void reload(); }, [reload]);

  async function create(e: FormEvent) {
    e.preventDefault();
    if (await act(() => post(PATH, { code, name }))) {
      setCode("");
      setName("");
    }
  }

  async function save(id: number, changes: Partial<Department>) {
    if (await act(() => patch(`${PATH}/${id}`, changes))) {
      setEditing(null);
    }
  }

  return (
    <section aria-label="Departments">
      <h2>Departments</h2>
      <button type="button" onClick={() => void reload()}>Refresh</button>
      <ErrorMessage error={error} />
      {rows && (
        <table>
          <thead><tr><th>Code</th><th>Name</th><th>Head</th><th>Classification</th><th>Status</th><th /></tr></thead>
          <tbody>
            {rows.map((d) => (
              <tr key={d.id}>
                <td>{d.code}</td><td>{d.name}</td><td>{d.head_user_id ?? "—"}</td><td>{d.classification}</td>
                <td>{d.active ? "active" : "inactive"}</td>
                <td>
                  {editing === d.id
                    ? <EditDepartment d={d} onSave={(c) => void save(d.id, c)} onCancel={() => setEditing(null)} />
                    : <button type="button" aria-label={`Edit ${d.code}`} onClick={() => setEditing(d.id)}>Edit</button>}
                  {d.active
                    ? <button type="button" aria-label={`Deactivate ${d.code}`} disabled={busy}
                      onClick={() => void act(() => post(`${PATH}/${d.id}/deactivate`, {}))}>Deactivate</button>
                    : <button type="button" aria-label={`Reactivate ${d.code}`} disabled={busy}
                      onClick={() => void act(() => post(`${PATH}/${d.id}/reactivate`, {}))}>Reactivate</button>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      <form aria-label="New department" onSubmit={(e) => void create(e)}>
        <h3>New department</h3>
        <label>Code<input value={code} required onChange={(e) => setCode(e.target.value)} /></label>
        <label>Name<input value={name} required onChange={(e) => setName(e.target.value)} /></label>
        <button type="submit" disabled={busy}>Create department</button>
      </form>
    </section>
  );
}
