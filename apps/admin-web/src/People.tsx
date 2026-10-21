// People (MVP-1 slice 10c): list, create, update, deactivate and reactivate through /api/v1/org/people
// (services/org.py; slice 2 rules: no change to one's own record, no deactivation while a login account or an agent
// is active). Org admin with a fresh step-up only (R-30, R-41): the server decides every action.
import { type FormEvent, useCallback, useEffect, useState } from "react";

import { get, patch, post } from "./api";
import type { Department } from "./Departments";
import { ErrorMessage, LEVELS, plain, ROLES, Select, useRows } from "./ui";

export type Person = { id: number; name: string; email: string; role: string; department_id: number | null;
  trained_auditor: boolean; active: boolean; classification: string; agents: number[] };

const PATH = "/api/v1/org/people";

type Data = { people: Person[]; departments: Department[] };

function departmentOptions(departments: Department[]) {
  return departments.filter((d) => d.active).map((d) => ({ value: String(d.id), text: `${d.code} ${d.name}` }));
}

function EditPerson({ p, departments, onSave, onCancel }: { p: Person; departments: Department[];
  onSave: (changes: Partial<Person>) => void; onCancel: () => void }) {
  const [name, setName] = useState(p.name);
  const [email, setEmail] = useState(p.email);
  const [role, setRole] = useState(p.role);
  const [department, setDepartment] = useState(p.department_id === null ? "" : String(p.department_id));
  const [classification, setClassification] = useState(p.classification);
  const [trained, setTrained] = useState(p.trained_auditor);

  function submit(e: FormEvent) {
    e.preventDefault();
    onSave({ name, email, role, department_id: department === "" ? null : Number(department), classification,
      trained_auditor: trained });
  }

  return (
    <form aria-label={`Edit person ${p.id}`} onSubmit={submit}>
      <label>Name<input value={name} required onChange={(e) => setName(e.target.value)} /></label>
      <label>Email<input type="email" value={email} required onChange={(e) => setEmail(e.target.value)} /></label>
      <Select label="Role" value={role} options={plain(ROLES)} onChange={setRole} />
      <Select label="Department" value={department} options={departmentOptions(departments)} onChange={setDepartment}
        allowNone="(none)" />
      <Select label="Classification" value={classification} options={plain(LEVELS)} onChange={setClassification} />
      <label>Trained auditor
        <input type="checkbox" checked={trained} onChange={(e) => setTrained(e.target.checked)} /></label>
      <button type="submit">Save</button>
      <button type="button" onClick={onCancel}>Cancel</button>
    </form>
  );
}

export function People() {
  const load = useCallback(async (): Promise<Data> => {
    const people = await get<Person[]>(PATH);
    const departments = await get<Department[]>("/api/v1/org/departments");
    return { people, departments };
  }, []);
  const { rows, error, busy, reload, act } = useRows(load);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [role, setRole] = useState("VIEWER");
  const [department, setDepartment] = useState("");
  const [editing, setEditing] = useState<number | null>(null);

  useEffect(() => { void reload(); }, [reload]);

  const deptName = (id: number | null) => rows?.departments.find((d) => d.id === id)?.code ?? "—";

  async function create(e: FormEvent) {
    e.preventDefault();
    const body = { name, email, role, department_id: department === "" ? null : Number(department) };
    if (await act(() => post(PATH, body))) {
      setName("");
      setEmail("");
    }
  }

  async function save(id: number, changes: Partial<Person>) {
    if (await act(() => patch(`${PATH}/${id}`, changes))) {
      setEditing(null);
    }
  }

  return (
    <section aria-label="People">
      <h2>People</h2>
      <button type="button" onClick={() => void reload()}>Refresh</button>
      <ErrorMessage error={error} />
      {rows && (
        <table>
          <thead>
            <tr><th>Id</th><th>Name</th><th>Email</th><th>Role</th><th>Department</th><th>Classification</th>
              <th>Status</th><th /></tr>
          </thead>
          <tbody>
            {rows.people.map((p) => (
              <tr key={p.id}>
                <td>{p.id}</td><td>{p.name}</td><td>{p.email}</td><td>{p.role}</td><td>{deptName(p.department_id)}</td>
                <td>{p.classification}</td><td>{p.active ? "active" : "inactive"}</td>
                <td>
                  {editing === p.id
                    ? <EditPerson p={p} departments={rows.departments} onSave={(c) => void save(p.id, c)}
                      onCancel={() => setEditing(null)} />
                    : <button type="button" aria-label={`Edit ${p.name}`} onClick={() => setEditing(p.id)}>Edit</button>}
                  {p.active
                    ? <button type="button" aria-label={`Deactivate ${p.name}`} disabled={busy}
                      onClick={() => void act(() => post(`${PATH}/${p.id}/deactivate`, {}))}>Deactivate</button>
                    : <button type="button" aria-label={`Reactivate ${p.name}`} disabled={busy}
                      onClick={() => void act(() => post(`${PATH}/${p.id}/reactivate`, {}))}>Reactivate</button>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      <form aria-label="New person" onSubmit={(e) => void create(e)}>
        <h3>New person</h3>
        <label>Name<input value={name} required onChange={(e) => setName(e.target.value)} /></label>
        <label>Email<input type="email" value={email} required onChange={(e) => setEmail(e.target.value)} /></label>
        <Select label="Role" value={role} options={plain(ROLES)} onChange={setRole} />
        <Select label="Department" value={department} options={departmentOptions(rows?.departments ?? [])}
          onChange={setDepartment} allowNone="(none)" />
        <button type="submit" disabled={busy}>Create person</button>
      </form>
    </section>
  );
}
