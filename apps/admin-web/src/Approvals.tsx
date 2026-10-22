// The approval inbox (MVP-1 slice step 10f; R-32, R-56, R-59, R-60, R-76): the proposed versions the server lets the
// person read (GET /api/v1/workflow/versions?status=proposed), and for one of them the full digest, the diff against
// the current baseline of the same template and the validator's result. Approve sends exactly the digest shown and
// an effective date; the server checks the approver's qualification, refuses self-approval, needs a fresh step-up
// (the dialog opens once and the request is retried once) and answers 409 when the version changed since it was
// shown (R-59). Reject needs a reason. Nothing is kept: every review loads the version again.
import { type FormEvent, useCallback, useEffect, useState } from "react";

import { get, post } from "./api";
import { ErrorMessage, useRows } from "./ui";
import { Findings, type Validation, type Version, WF } from "./workflow";

type Diff = { version_id: number; against_id: number; nodes_added: string[]; nodes_removed: string[];
  nodes_changed: string[]; edges_added: string[][]; edges_removed: string[][]; other_changed: string[] };
type Review = { version: Version; baseline: Version | null; diff: Diff | null; validation: Validation };

/** Today's date in the person's calendar as YYYY-MM-DD (the server checks it against its own clock). */
export function localToday(now: Date = new Date()): string {
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
}

const list = (items: string[]) => (items.length === 0 ? "none" : items.join(", "));

function DiffView({ diff, baseline }: { diff: Diff | null; baseline: Version | null }) {
  if (!diff || !baseline) {
    return <p>No baselined version of this template yet: everything is new.</p>;
  }
  return (
    <dl aria-label="Changes against the baseline">
      <dt>Against</dt><dd>version {baseline.version_no} (id {baseline.id}), digest {baseline.digest}</dd>
      <dt>Steps added</dt><dd>{list(diff.nodes_added)}</dd>
      <dt>Steps removed</dt><dd>{list(diff.nodes_removed)}</dd>
      <dt>Steps changed</dt><dd>{list(diff.nodes_changed)}</dd>
      <dt>Links added</dt><dd>{list(diff.edges_added.map((e) => e.filter(Boolean).join(" → ")))}</dd>
      <dt>Links removed</dt><dd>{list(diff.edges_removed.map((e) => e.filter(Boolean).join(" → ")))}</dd>
      <dt>Other changes</dt><dd>{list(diff.other_changed)}</dd>
    </dl>
  );
}

function ReviewView({ id, onDecided }: { id: number; onDecided: (message: string) => void }) {
  const load = useCallback(async (): Promise<Review> => {
    const version = await get<Version>(`${WF}/versions/${id}`);
    const baselines = await get<Version[]>(`${WF}/versions?status=baselined`);
    const baseline = baselines.find((b) => b.template_id === version.template_id) ?? null;
    const diff = baseline ? await get<Diff>(`${WF}/versions/${id}/diff?against=${baseline.id}`) : null;
    const validation = await post<Validation>(`${WF}/versions/${id}/validate`, {});
    return { version, baseline, diff, validation };
  }, [id]);
  const { rows, error, busy, reload, act } = useRows(load);
  const [effective, setEffective] = useState(localToday());
  const [reason, setReason] = useState("");

  useEffect(() => { void reload(); }, [reload]);

  async function approve(e: FormEvent, digest: string) {
    e.preventDefault();
    if (await act(() => post(`${WF}/versions/${id}/approve`, { digest, effective_date: effective }))) {
      onDecided(`Version ${id} baselined with digest ${digest}.`);
    }
  }

  async function reject(e: FormEvent) {
    e.preventDefault();
    if (await act(() => post(`${WF}/versions/${id}/reject`, { reason }))) {
      onDecided(`Version ${id} rejected; it is a draft again.`);
    }
  }

  const v = rows?.version;
  return (
    <article aria-label={`Review of version ${id}`}>
      <h3>Version {id}</h3>
      <ErrorMessage error={error} />
      {v && rows && (
        <>
          <p>{v.title}, version {v.version_no} of template {v.template_id}, status {v.status}, submitted by person
            {" "}{v.submitted_by_id ?? "—"}.</p>
          <p>Digest: <code aria-label="Digest">{v.digest}</code></p>
          <DiffView diff={rows.diff} baseline={rows.baseline} />
          <Findings findings={rows.validation.findings} label="Validator results" />
          <p>{rows.validation.valid ? "The validator reports no errors." : "The validator reports errors."}</p>
          {v.status === "proposed" && v.digest && (
            <>
              <form aria-label="Approve" onSubmit={(e) => void approve(e, v.digest as string)}>
                <label>Effective date<input type="date" value={effective} required
                  onChange={(e) => setEffective(e.target.value)} /></label>
                <button type="submit" disabled={busy}>Approve this digest</button>
              </form>
              <form aria-label="Reject" onSubmit={(e) => void reject(e)}>
                <label>Reason<input value={reason} required maxLength={500}
                  onChange={(e) => setReason(e.target.value)} /></label>
                <button type="submit" disabled={busy}>Reject</button>
              </form>
            </>
          )}
        </>
      )}
    </article>
  );
}

export function Approvals() {
  const load = useCallback(() => get<Version[]>(`${WF}/versions?status=proposed`), []);
  const { rows, error, reload } = useRows(load);
  const [open, setOpen] = useState<number | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => { void reload(); }, [reload]);

  return (
    <section aria-label="Approval inbox">
      <h2>Approval inbox</h2>
      <button type="button" onClick={() => void reload()}>Refresh</button>
      <ErrorMessage error={error} />
      {message && <p role="status">{message}</p>}
      {rows && rows.length === 0 && <p>Nothing waits for approval.</p>}
      {rows && rows.length > 0 && (
        <table>
          <thead><tr><th>Id</th><th>Guideline</th><th>Title</th><th>Version</th><th>Submitted by</th><th /></tr></thead>
          <tbody>
            {rows.map((v) => (
              <tr key={v.id}>
                <td>{v.id}</td><td>{v.guideline_id}</td><td>{v.title}</td><td>{v.version_no}</td>
                <td>{v.submitted_by_id ?? "—"}</td>
                <td><button type="button" aria-label={`Review version ${v.id}`}
                  onClick={() => { setMessage(null); setOpen(v.id); }}>Review</button></td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {open !== null && <ReviewView key={open} id={open}
        onDecided={(m) => { setOpen(null); setMessage(m); void reload(); }} />}
    </section>
  );
}
