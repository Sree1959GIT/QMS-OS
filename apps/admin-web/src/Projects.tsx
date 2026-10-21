// Project membership (MVP-1 slice 10d): the org-level project list (GET /api/v1/org/projects) with each project's
// current members; add and remove through /api/v1/org/projects/{id}/members (services/org.py; slice 3). The server
// refuses an org admin adding themselves; the screen offers every active person and lets the server decide.
import { useCallback, useEffect, useState } from "react";

import { get, post } from "./api";
import type { Person } from "./People";
import { ErrorMessage, Select, useRows } from "./ui";

export type Project = { id: number; code: string; name: string; department_id: number; manager_user_id: number;
  classification: string; members: number[] };

const PATH = "/api/v1/org/projects";

type Data = { projects: Project[]; people: Person[] };

function AddMember({ project, people, busy, onAdd }: { project: Project; people: Person[]; busy: boolean;
  onAdd: (userId: number) => void }) {
  const [person, setPerson] = useState("");
  const options = people.filter((p) => p.active && !project.members.includes(p.id))
    .map((p) => ({ value: String(p.id), text: p.name }));
  return (
    <form aria-label={`Add member to ${project.code}`}
      onSubmit={(e) => { e.preventDefault(); if (person !== "") onAdd(Number(person)); }}>
      <Select label="Person" value={person} options={options} onChange={setPerson} allowNone="(choose)" />
      <button type="submit" disabled={busy || person === ""}>Add member</button>
    </form>
  );
}

export function Projects() {
  const load = useCallback(async (): Promise<Data> => {
    const projects = await get<Project[]>(PATH);
    const people = await get<Person[]>("/api/v1/org/people");
    return { projects, people };
  }, []);
  const { rows, error, busy, reload, act } = useRows(load);

  useEffect(() => { void reload(); }, [reload]);

  const nameOf = (id: number) => rows?.people.find((p) => p.id === id)?.name ?? `#${id}`;

  return (
    <section aria-label="Projects">
      <h2>Projects</h2>
      <button type="button" onClick={() => void reload()}>Refresh</button>
      <ErrorMessage error={error} />
      {rows && (
        <table>
          <thead><tr><th>Code</th><th>Name</th><th>Manager</th><th>Classification</th><th>Members</th><th /></tr></thead>
          <tbody>
            {rows.projects.map((p) => (
              <tr key={p.id}>
                <td>{p.code}</td><td>{p.name}</td><td>{nameOf(p.manager_user_id)}</td><td>{p.classification}</td>
                <td>
                  <ul aria-label={`Members of ${p.code}`}>
                    {p.members.map((m) => (
                      <li key={m}>
                        {nameOf(m)}{" "}
                        <button type="button" aria-label={`Remove ${nameOf(m)} from ${p.code}`} disabled={busy}
                          onClick={() => void act(() => post(`${PATH}/${p.id}/members/${m}/remove`, {}))}>Remove</button>
                      </li>
                    ))}
                  </ul>
                </td>
                <td>
                  <AddMember project={p} people={rows.people} busy={busy}
                    onAdd={(userId) => void act(() => post(`${PATH}/${p.id}/members`, { user_id: userId }))} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}
