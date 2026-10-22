// Guidelines and templates (2026-10-21, commit F): authors create a guideline (title, the owning department, the
// citations it rests on) and templates in it. The server decides who is an author (R-57: an org admin, the quality
// representative or a department head) and refuses a guideline its creator could not read (R-79); a template is
// created only in a guideline the person can read (404 otherwise). Neither needs a step-up under the existing rules.
// The guidelines listed are the ones the server returns (R-74 to R-77), with their classification; the departments
// offered are the ones the person can read (R-43). Nothing is kept between requests.
import { type FormEvent, useCallback, useEffect, useState } from "react";

import { get, post } from "./api";
import { ErrorMessage, Select, useRows } from "./ui";
import { type Guideline, WF } from "./workflow";

type Department = { id: number; code: string; name: string };
type Template = { id: number; title: string; versions: { id: number; version_no: number; status: string }[] };
type GuidelineDetail = Guideline & { references: string[]; templates: Template[] };

/** One citation per line, blank lines left out. */
export function referenceLines(text: string): string[] {
  return text.split("\n").map((line) => line.trim()).filter((line) => line !== "");
}

function GuidelineView({ id }: { id: number }) {
  const load = useCallback(() => get<GuidelineDetail>(`${WF}/guidelines/${id}`), [id]);
  const { rows: g, error, busy, reload, act } = useRows(load);
  const [title, setTitle] = useState("");

  useEffect(() => { void reload(); }, [reload]);

  async function create(e: FormEvent) {
    e.preventDefault();
    if (await act(() => post(`${WF}/guidelines/${id}/templates`, { title }))) {
      setTitle("");
    }
  }

  return (
    <article aria-label={`Guideline ${id}`}>
      <h3>Guideline {id}</h3>
      <ErrorMessage error={error} />
      {g && (
        <>
          <p>{g.title}, department {g.department_id}, classification {g.classification}.</p>
          <p>References: {g.references.length > 0 ? g.references.join("; ") : "none"}.</p>
          <table aria-label="Templates">
            <thead><tr><th>Id</th><th>Title</th><th>Versions</th></tr></thead>
            <tbody>
              {g.templates.map((t) => (
                <tr key={t.id}>
                  <td>{t.id}</td><td>{t.title}</td>
                  <td>{t.versions.map((v) => `${v.version_no} ${v.status}`).join(", ") || "none"}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <form aria-label="New template" onSubmit={(e) => void create(e)}>
            <label>Template title<input value={title} required maxLength={200}
              onChange={(e) => setTitle(e.target.value)} /></label>
            <button type="submit" disabled={busy}>Create template</button>
          </form>
        </>
      )}
    </article>
  );
}

export function Guidelines() {
  const load = useCallback(async () => {
    const guidelines = await get<Guideline[]>(`${WF}/guidelines`);
    const departments = await get<Department[]>("/api/v1/departments");
    return { guidelines, departments };
  }, []);
  const { rows, error, busy, reload, act } = useRows(load);
  const [title, setTitle] = useState("");
  const [department, setDepartment] = useState("");
  const [references, setReferences] = useState("");
  const [open, setOpen] = useState<number | null>(null);

  useEffect(() => { void reload(); }, [reload]);

  async function create(e: FormEvent) {
    e.preventDefault();
    const out: { id?: number } = {};
    const done = await act(async () => {
      out.id = (await post<Guideline>(`${WF}/guidelines`, { title, department_id: Number(department),
        references: referenceLines(references) })).id;
    });
    if (done && out.id !== undefined) {
      setTitle("");
      setReferences("");
      setOpen(out.id);
    }
  }

  return (
    <section aria-label="Guidelines">
      <h2>Guidelines</h2>
      <button type="button" onClick={() => void reload()}>Refresh</button>
      <ErrorMessage error={error} />
      {rows && (
        <table aria-label="Guidelines you can read">
          <thead><tr><th>Id</th><th>Title</th><th>Department</th><th>Classification</th><th /></tr></thead>
          <tbody>
            {rows.guidelines.map((g) => (
              <tr key={g.id}>
                <td>{g.id}</td><td>{g.title}</td><td>{g.department_id}</td><td>{g.classification}</td>
                <td><button type="button" aria-label={`Open guideline ${g.id}`} onClick={() => setOpen(g.id)}>
                  Open</button></td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      <form aria-label="New guideline" onSubmit={(e) => void create(e)}>
        <h3>New guideline</h3>
        <label>Title<input value={title} required maxLength={200} onChange={(e) => setTitle(e.target.value)} />
        </label>
        <Select label="Department" value={department} allowNone="(choose)" onChange={setDepartment}
          options={(rows?.departments ?? []).map((d) => ({ value: String(d.id), text: `${d.name} (${d.code})` }))} />
        <label>References (one per line)<textarea value={references} rows={3} cols={60}
          onChange={(e) => setReferences(e.target.value)} /></label>
        <button type="submit" disabled={busy || department === ""}>Create guideline</button>
      </form>
      {open !== null && <GuidelineView key={open} id={open} />}
    </section>
  );
}
