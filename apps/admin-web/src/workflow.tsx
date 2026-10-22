// Shared pieces of the workflow screens (MVP-1 slice steps 10e and 10f; ADR 0006, ADR 0008). The server decides every
// read (R-74 to R-77) and every change; these types only describe what its responses contain.
import { get } from "./api";

export const WF = "/api/v1/workflow";

export type Finding = { code: string; severity: string; node: string | null; edge: string | null; message: string };
export type Validation = { version_id: number; valid: boolean; findings: Finding[]; validator_version: number };
export type Question = { path: string; question: string };
export type Proposal = { id: number; rule: string | null; graph: unknown; department_id: number | null;
  questions: Question[]; findings: Finding[]; status: string; version_id: number | null; created_by_id: number };
export type Version = { id: number; template_id: number; version_no: number; title: string; graph: unknown;
  status: string; digest: string | null; origin: string; created_by_id: number; submitted_by_id: number | null;
  effective_date: string | null; guideline_id?: number };
export type Guideline = { id: number; title: string; department_id: number; classification: string; active: boolean };
type GuidelineDetail = Guideline & { templates: { id: number; title: string }[] };

export type TemplateOption = { value: string; text: string };

/** The templates the person may read, labelled with their guideline and its classification (R-74). */
export async function templateOptions(): Promise<TemplateOption[]> {
  const guidelines = await get<Guideline[]>(`${WF}/guidelines`);
  const out: TemplateOption[] = [];
  for (const g of guidelines) {
    const detail = await get<GuidelineDetail>(`${WF}/guidelines/${g.id}`);
    for (const t of detail.templates) {
      out.push({ value: String(t.id), text: `${g.title} (${g.classification}) / ${t.title}` });
    }
  }
  return out;
}

/** The validator's findings with their codes (R-60). */
export function Findings({ findings, label }: { findings: Finding[]; label: string }) {
  if (findings.length === 0) {
    return <p>{label}: no findings.</p>;
  }
  return (
    <table aria-label={label}>
      <thead><tr><th>Code</th><th>Severity</th><th>Step</th><th>Message</th></tr></thead>
      <tbody>
        {findings.map((f, i) => (
          <tr key={`${f.code}-${f.node ?? ""}-${i}`}>
            <td>{f.code}</td><td>{f.severity}</td><td>{f.node ?? f.edge ?? "—"}</td><td>{f.message}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export const errorCount = (findings: Finding[]) => findings.filter((f) => f.severity === "error").length;
