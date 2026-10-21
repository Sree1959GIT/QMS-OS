// The proposal form and validator results (MVP-1 slice step 10e; R-33, R-60, R-62): a request in plain words becomes
// a proposal by rules, with questions for every fact the rules cannot know; answers fill them; the proposal becomes a
// draft version of a chosen template; the draft is checked by the completeness validator (findings with their codes)
// and edited until the server accepts its submission. The server refuses a submission while errors remain (422); the
// screen shows the refusal, it does not decide it. Reads are grant-governed (R-74 to R-77): the list holds only what
// the server returns. Nothing is kept between requests.
import { type FormEvent, useCallback, useEffect, useState } from "react";

import { type ApiError, get, patch, post } from "./api";
import { ErrorMessage, Select, useRows } from "./ui";
import {
  errorCount, Findings, type Proposal, templateOptions, type Validation, type Version, WF,
} from "./workflow";

const NUMERIC = /(^department_id$|^target_days$|\.sla_days$)/;

/** An answer as the server expects it: whole numbers for departments and days, text otherwise. */
export function answerValue(path: string, raw: string): number | string {
  return NUMERIC.test(path) && /^\d+$/.test(raw.trim()) ? Number(raw.trim()) : raw;
}

function ProposalView({ id, onDrafted }: { id: number; onDrafted: (versionId: number) => void }) {
  const load = useCallback(async () => {
    const proposal = await get<Proposal>(`${WF}/proposals/${id}`);
    const templates = proposal.status === "open" ? await templateOptions() : [];
    return { proposal, templates };
  }, [id]);
  const { rows, error, busy, reload, act } = useRows(load);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [template, setTemplate] = useState("");
  const [title, setTitle] = useState("");

  useEffect(() => { void reload(); }, [reload]);

  async function answer(e: FormEvent) {
    e.preventDefault();
    const body = Object.fromEntries(Object.entries(answers).filter(([, v]) => v.trim() !== "")
      .map(([k, v]) => [k, answerValue(k, v)]));
    if (await act(() => post(`${WF}/proposals/${id}/answers`, { answers: body }))) {
      setAnswers({});
    }
  }

  async function draft(e: FormEvent) {
    e.preventDefault();
    const out: { id?: number } = {};
    const done = await act(async () => {
      out.id = (await post<Version>(`${WF}/proposals/${id}/draft`, { template_id: Number(template), title })).id;
    });
    if (done && out.id !== undefined) {
      onDrafted(out.id);
    }
  }

  const p = rows?.proposal;
  return (
    <article aria-label={`Proposal ${id}`}>
      <h3>Proposal {id}</h3>
      <ErrorMessage error={error} />
      {p && (
        <>
          <p>Rule: {p.rule ?? "none matched"}. Status: {p.status}.
            {p.version_id !== null && ` Drafted as version ${p.version_id}.`}</p>
          {p.status === "open" && p.questions.length > 0 && (
            <form aria-label="Answer questions" onSubmit={(e) => void answer(e)}>
              <h4>Questions</h4>
              {p.questions.map((q) => (
                <label key={q.path}>
                  {q.question}
                  <input aria-description={q.path} value={answers[q.path] ?? ""} maxLength={200}
                    onChange={(e) => setAnswers({ ...answers, [q.path]: e.target.value })} />
                </label>
              ))}
              <button type="submit" disabled={busy}>Send answers</button>
            </form>
          )}
          {p.status === "open" && p.questions.length === 0 && <p>No open questions.</p>}
          <Findings findings={p.findings} label="Validator results for the proposal" />
          {p.status === "open" && p.graph !== null && (
            <form aria-label="Draft a version" onSubmit={(e) => void draft(e)}>
              <h4>Draft a version</h4>
              <Select label="Template" value={template} allowNone="(choose)" options={rows?.templates ?? []}
                onChange={setTemplate} />
              <label>Title<input value={title} required maxLength={200} onChange={(e) => setTitle(e.target.value)} />
              </label>
              <button type="submit" disabled={busy || template === ""}>Create draft</button>
            </form>
          )}
        </>
      )}
    </article>
  );
}

/** A version as an author works on it: the graph of a draft can be edited, checked and submitted. */
export function DraftVersion({ id }: { id: number }) {
  const load = useCallback(async () => {
    const version = await get<Version>(`${WF}/versions/${id}`);
    const validation = await post<Validation>(`${WF}/versions/${id}/validate`, {});
    return { version, validation };
  }, [id]);
  const { rows, error, busy, reload, act } = useRows(load);
  const [graph, setGraph] = useState<string | null>(null);
  const [parseError, setParseError] = useState<ApiError | null>(null);

  useEffect(() => { void reload(); }, [reload]);

  async function save(e: FormEvent) {
    e.preventDefault();
    setParseError(null);
    let parsed: unknown;
    try {
      parsed = JSON.parse(graph ?? "");
    } catch {
      setParseError({ status: 0, detail: "The graph is not valid JSON; nothing was sent." });
      return;
    }
    if (await act(() => patch(`${WF}/versions/${id}`, { graph: parsed }))) {
      setGraph(null);
    }
  }

  const v = rows?.version;
  const errors = rows ? errorCount(rows.validation.findings) : 0;
  return (
    <article aria-label={`Version ${id}`}>
      <h3>Version {id}</h3>
      <ErrorMessage error={error} />
      {v && rows && (
        <>
          <p>{v.title}, version {v.version_no}, status {v.status}.{v.digest && ` Digest ${v.digest}.`}</p>
          <Findings findings={rows.validation.findings} label="Validator results" />
          <p role="status">{rows.validation.valid ? "The validator reports no errors."
            : `The validator reports ${errors} error(s); the server refuses submission until they are fixed.`}</p>
          {v.status === "draft" && (
            <>
              <form aria-label="Edit the graph" onSubmit={(e) => void save(e)}>
                <label>Graph (JSON)
                  <textarea rows={16} cols={80} value={graph ?? JSON.stringify(v.graph, null, 2)}
                    onChange={(e) => setGraph(e.target.value)} />
                </label>
                <button type="submit" disabled={busy}>Save graph</button>
              </form>
              <ErrorMessage error={parseError} />
              <button type="button" disabled={busy} onClick={() => void reload()}>Validate again</button>
              <button type="button" disabled={busy}
                onClick={() => void act(() => post(`${WF}/versions/${id}/submit`, {}))}>Submit for approval</button>
            </>
          )}
        </>
      )}
    </article>
  );
}

export function Proposals() {
  const load = useCallback(() => get<Proposal[]>(`${WF}/proposals`), []);
  const { rows, error, busy, reload, act } = useRows(load);
  const [request, setRequest] = useState("");
  const [open, setOpen] = useState<number | null>(null);
  const [version, setVersion] = useState<number | null>(null);

  useEffect(() => { void reload(); }, [reload]);

  async function propose(e: FormEvent) {
    e.preventDefault();
    const out: { id?: number } = {};
    if (await act(async () => { out.id = (await post<Proposal>(`${WF}/proposals`, { request })).id; })
      && out.id !== undefined) {
      setRequest("");
      setVersion(null);
      setOpen(out.id);
    }
  }

  return (
    <section aria-label="Proposals">
      <h2>Proposals</h2>
      <button type="button" onClick={() => void reload()}>Refresh</button>
      <ErrorMessage error={error} />
      {rows && (
        <table>
          <thead><tr><th>Id</th><th>Rule</th><th>Status</th><th>Open questions</th><th /></tr></thead>
          <tbody>
            {rows.map((p) => (
              <tr key={p.id}>
                <td>{p.id}</td><td>{p.rule ?? "none"}</td><td>{p.status}</td><td>{p.questions.length}</td>
                <td><button type="button" aria-label={`Open proposal ${p.id}`}
                  onClick={() => { setVersion(null); setOpen(p.id); }}>Open</button></td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      <form aria-label="New proposal" onSubmit={(e) => void propose(e)}>
        <h3>New proposal</h3>
        <label>Request<textarea value={request} required maxLength={2000} rows={3} cols={80}
          onChange={(e) => setRequest(e.target.value)} /></label>
        <button type="submit" disabled={busy}>Propose</button>
      </form>
      {open !== null && version === null
        && <ProposalView key={open} id={open} onDrafted={(id) => { setVersion(id); void reload(); }} />}
      {version !== null && <DraftVersion key={version} id={version} />}
    </section>
  );
}
