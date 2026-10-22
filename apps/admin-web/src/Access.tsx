// Effective-access preview (MVP-1 slice 10d): for a person (GET /api/v1/org/access-preview/{user_id}) and for an
// agent (GET /api/v1/org/access-preview/agents/{agent_id}), both computed by the functions that enforce the reads
// (services/access.py; R-31, R-48, D11). For an agent, the screen loads its person's preview in the same step and
// shows, kind by kind, that the agent reads nothing its person cannot. Nothing is kept: every "Show" asks again.
import { useCallback, useEffect, useState } from "react";

import { type ApiError, get } from "./api";
import type { Agent } from "./Agents";
import type { Person } from "./People";
import { ErrorMessage, Select, useRows } from "./ui";

type Ids = (number | string)[];
type Matrix = { active: boolean; grants: Record<string, { max_classification: string; scope: string }>;
  member_projects: number[]; readable: Record<string, Ids>; denied: Record<string, Ids> };
export type PersonPreview = Matrix & { user_id: number; role: string; agents: number[] };
export type AgentPreview = Matrix & { agent_id: number; person_id: number; max_classification: string };

const PREVIEW = "/api/v1/org/access-preview";
const PREVIEW_KINDS = ["department", "person", "project", "evidence", "workflow"];   // workflow: guidelines (R-78)

type Data = { people: Person[]; agents: Agent[] };

/** Items the agent may read that its person may not, per kind; every list must be empty (D11). */
export function widerThanPerson(agent: AgentPreview, person: PersonPreview): Record<string, Ids> {
  const out: Record<string, Ids> = {};
  for (const kind of PREVIEW_KINDS) {
    const allowed = new Set(person.readable[kind] ?? []);
    out[kind] = (agent.readable[kind] ?? []).filter((id) => !allowed.has(id));
  }
  return out;
}

function Grants({ m }: { m: Matrix }) {
  const kinds = Object.keys(m.grants);
  return kinds.length === 0 ? <p>No active grants.</p> : (
    <ul aria-label="Grants">
      {kinds.map((k) => <li key={k}>{k}: up to {m.grants[k]?.max_classification} ({m.grants[k]?.scope})</li>)}
    </ul>
  );
}

function PersonResult({ p }: { p: PersonPreview }) {
  return (
    <article aria-label={`Access of person ${p.user_id}`}>
      <h3>Person {p.user_id} ({p.role}, {p.active ? "active" : "inactive"})</h3>
      <Grants m={p} />
      <p>Member of projects: {p.member_projects.length === 0 ? "none" : p.member_projects.join(", ")}</p>
      <table>
        <thead><tr><th>Kind</th><th>Readable</th><th>Denied</th></tr></thead>
        <tbody>
          {PREVIEW_KINDS.map((k) => (
            <tr key={k}><td>{k}</td><td>{p.readable[k]?.length ?? 0}</td><td>{p.denied[k]?.length ?? 0}</td></tr>
          ))}
        </tbody>
      </table>
      <p>Active agents: {p.agents.length === 0 ? "none" : p.agents.join(", ")}</p>
    </article>
  );
}

function AgentResult({ a, p }: { a: AgentPreview; p: PersonPreview }) {
  const wider = widerThanPerson(a, p);
  const extra = PREVIEW_KINDS.reduce((n, k) => n + (wider[k]?.length ?? 0), 0);
  return (
    <article aria-label={`Access of agent ${a.agent_id}`}>
      <h3>Agent {a.agent_id} for person {a.person_id} (ceiling {a.max_classification})</h3>
      <table>
        <thead><tr><th>Kind</th><th>Person reads</th><th>Agent reads</th><th>Agent only</th></tr></thead>
        <tbody>
          {PREVIEW_KINDS.map((k) => (
            <tr key={k}>
              <td>{k}</td><td>{p.readable[k]?.length ?? 0}</td><td>{a.readable[k]?.length ?? 0}</td>
              <td>{wider[k]?.length ?? 0}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {extra === 0
        ? <p role="status">Never wider than its person: every item the agent can read, person {a.person_id} can read
          too.</p>
        : <p role="alert">Wider than its person: the agent can read {extra} item(s) that person {a.person_id} cannot.
          This breaks the agent rule (D11); report it.</p>}
    </article>
  );
}

export function Access() {
  const load = useCallback(async (): Promise<Data> => {
    const people = await get<Person[]>("/api/v1/org/people");
    const agents = await get<Agent[]>("/api/v1/org/agents");
    return { people, agents };
  }, []);
  const { rows, error, reload } = useRows(load);
  const [person, setPerson] = useState("");
  const [agent, setAgent] = useState("");
  const [result, setResult] = useState<{ person: PersonPreview; agent?: AgentPreview } | null>(null);
  const [showError, setShowError] = useState<ApiError | null>(null);

  useEffect(() => { void reload(); }, [reload]);

  async function show(load: () => Promise<{ person: PersonPreview; agent?: AgentPreview }>) {
    setResult(null);
    setShowError(null);
    try {
      setResult(await load());
    } catch (err) {
      setShowError(err as ApiError);
    }
  }

  const showPerson = () => show(async () => ({ person: await get<PersonPreview>(`${PREVIEW}/${person}`) }));
  const showAgent = () => show(async () => {
    const a = await get<AgentPreview>(`${PREVIEW}/agents/${agent}`);
    return { agent: a, person: await get<PersonPreview>(`${PREVIEW}/${a.person_id}`) };
  });

  return (
    <section aria-label="Access preview">
      <h2>Access preview</h2>
      <ErrorMessage error={error} />
      <form aria-label="Preview a person" onSubmit={(e) => { e.preventDefault(); void showPerson(); }}>
        <Select label="Person" value={person} allowNone="(choose)" onChange={setPerson}
          options={(rows?.people ?? []).map((p) => ({ value: String(p.id), text: p.name }))} />
        <button type="submit" disabled={person === ""}>Show person</button>
      </form>
      <form aria-label="Preview an agent" onSubmit={(e) => { e.preventDefault(); void showAgent(); }}>
        <Select label="Agent" value={agent} allowNone="(choose)" onChange={setAgent}
          options={(rows?.agents ?? []).map((a) => ({ value: String(a.id), text: `${a.id} ${a.label}` }))} />
        <button type="submit" disabled={agent === ""}>Show agent</button>
      </form>
      <ErrorMessage error={showError} />
      {result?.agent ? <AgentResult a={result.agent} p={result.person} /> : result && <PersonResult p={result.person} />}
    </section>
  );
}
