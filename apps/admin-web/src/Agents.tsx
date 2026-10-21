// Agent profiles (MVP-1 slice 10d): list, enrol, view and revoke through /api/v1/org/agents (services/org.py;
// slice 4, R-48, R-49). Zero agents by default; revocation is final. The server refuses an agent for the org admin
// themselves, for an inactive person, or a second active agent for one person.
import { type FormEvent, useCallback, useEffect, useState } from "react";

import { type ApiError, get, post } from "./api";
import type { Person } from "./People";
import { ErrorMessage, LEVELS, plain, Select, useRows } from "./ui";

export type Agent = { id: number; label: string; person_id: number; max_classification: string; active: boolean;
  enrolled_at: string; enrolled_by_id: number; revoked_at: string | null; revoked_by_id: number | null;
  revoke_reason: string | null };

const PATH = "/api/v1/org/agents";

type Data = { agents: Agent[]; people: Person[] };

function Revoke({ agent, busy, onRevoke }: { agent: Agent; busy: boolean; onRevoke: (reason: string) => void }) {
  const [reason, setReason] = useState("");
  return (
    <form aria-label={`Revoke agent ${agent.id}`} onSubmit={(e) => { e.preventDefault(); onRevoke(reason); }}>
      <label>Reason<input value={reason} required maxLength={200} onChange={(e) => setReason(e.target.value)} /></label>
      <button type="submit" disabled={busy}>Revoke (final)</button>
    </form>
  );
}

export function Agents() {
  const load = useCallback(async (): Promise<Data> => {
    const agents = await get<Agent[]>(PATH);
    const people = await get<Person[]>("/api/v1/org/people");
    return { agents, people };
  }, []);
  const { rows, error, busy, reload, act } = useRows(load);
  const [person, setPerson] = useState("");
  const [label, setLabel] = useState("");
  const [ceiling, setCeiling] = useState("internal");
  const [viewed, setViewed] = useState<Agent | null>(null);
  const [viewError, setViewError] = useState<ApiError | null>(null);

  useEffect(() => { void reload(); }, [reload]);

  const nameOf = (id: number | null) => (id === null ? "—" : rows?.people.find((p) => p.id === id)?.name ?? `#${id}`);

  async function view(id: number) {
    setViewed(null);
    setViewError(null);
    try {
      setViewed(await get<Agent>(`${PATH}/${id}`));       // fresh from the server, not from the list
    } catch (err) {
      setViewError(err as ApiError);
    }
  }

  async function enrol(e: FormEvent) {
    e.preventDefault();
    if (await act(() => post(PATH, { person_id: Number(person), label, max_classification: ceiling }))) {
      setLabel("");
    }
  }

  async function revoke(id: number, reason: string) {
    if (await act(() => post(`${PATH}/${id}/revoke`, { reason }))) {
      setViewed(null);
    }
  }

  return (
    <section aria-label="Agents">
      <h2>Agents</h2>
      <button type="button" onClick={() => void reload()}>Refresh</button>
      <ErrorMessage error={error} />
      {rows && (
        <table>
          <thead><tr><th>Id</th><th>Label</th><th>Person</th><th>Ceiling</th><th>Status</th><th /></tr></thead>
          <tbody>
            {rows.agents.map((a) => (
              <tr key={a.id}>
                <td>{a.id}</td><td>{a.label}</td><td>{nameOf(a.person_id)}</td><td>{a.max_classification}</td>
                <td>{a.active ? "active" : "revoked"}</td>
                <td><button type="button" aria-label={`View agent ${a.id}`} onClick={() => void view(a.id)}>View</button></td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      <ErrorMessage error={viewError} />
      {viewed && (
        <article aria-label={`Agent ${viewed.id}`}>
          <h3>Agent {viewed.id}: {viewed.label}</h3>
          <dl>
            <dt>Person</dt><dd>{nameOf(viewed.person_id)}</dd>
            <dt>Ceiling</dt><dd>{viewed.max_classification}</dd>
            <dt>Enrolled</dt><dd>{viewed.enrolled_at} by {nameOf(viewed.enrolled_by_id)}</dd>
            <dt>Status</dt>
            <dd>{viewed.active ? "active" : `revoked ${viewed.revoked_at ?? ""} by ${nameOf(viewed.revoked_by_id)}: ${viewed.revoke_reason ?? ""}`}</dd>
          </dl>
          {viewed.active && <Revoke agent={viewed} busy={busy} onRevoke={(r) => void revoke(viewed.id, r)} />}
        </article>
      )}
      <form aria-label="Enrol agent" onSubmit={(e) => void enrol(e)}>
        <h3>Enrol agent</h3>
        <Select label="Person" value={person} allowNone="(choose)"
          options={(rows?.people ?? []).filter((p) => p.active).map((p) => ({ value: String(p.id), text: p.name }))}
          onChange={setPerson} />
        <label>Label<input value={label} required maxLength={120} onChange={(e) => setLabel(e.target.value)} /></label>
        <Select label="Ceiling" value={ceiling} options={plain(LEVELS)} onChange={setCeiling} />
        <button type="submit" disabled={busy || person === ""}>Enrol agent</button>
      </form>
    </section>
  );
}
