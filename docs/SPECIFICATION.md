# QMS Virtual Organization — Claude Code Build Specification

**Version:** 3.0, 29 September 2026  
**Owner:** the adopting organization (identity deliberately not recorded in this repository); draft for owner/process-owner review  
**Target:** GitHub development, Windows i9 laptop / 12 GB VRAM / 64 GB DRAM / SSD; local Docker Desktop/WSL2 stack; optional Vercel synthetic frontend preview.  
**Authoritative source for build:** this document plus reviewed organization SOPs and `docs/decisions.md`. Do not assume real employees, ISO certification, legal requirements or data-retention periods not supplied by the organization.

## 1. Purpose and architecture decision

Build a virtual mirror of the real organization: stakeholder-specific Hermes assistants support humans through Telegram text/voice and consented read-only mailbox ingestion. Human stakeholders are HIL for decisions, release, messages and changes. Claude Code is both the **interactive, Admin-operated Superadmin workbench** and the development IDE; it is NOT an embedded unattended supervisor or a subscription-backed service API. The normal Admin web UI configures organizations, departments, people, access, providers, agents and baselined workflows. An application-owned policy/workflow service enforces constraints regardless of model or prompt. Local Gemma 4 is first runtime candidate for Hermes; Admin can choose other local or approved paid providers through a provider registry. Claude Code may interact with read-only/proposal MCP tools from the workbench, but cannot itself publish organizational control changes without app-side approval. No Anthropic API/SDK is necessary for the interactive Superadmin mode; if unattended programmatic Claude management is later wanted, assess supported API/terms/billing separately. [A1][A2]

The original project source notes (a composite knowledge-framework Markdown file, its companion PDF and project chat notes, all held outside this repository) define multimodal WeKnora evidence, incrementally maintained wiki, Obsidian-compatible agent vaults, bounded Hermes agents and QMS provenance; later conversation adds first-class mailbox intake, Hindsight, second-brain-os, K-Plex, Laya, optional CLM, optional Webcmd, Digital-Secretary's spoken-summary behavior, ISO 9001:2026 and the Admin/workflow studio. The v0.1 PDF mirrors the v0.1 Markdown and does not contain the later email pipeline. [S1][S2][S3]

### 1.1 Sources of truth, in priority order

1. QMS PostgreSQL metadata/workflows + content-addressed original evidence store: authority for approved state, identity, provenance, ISO mapping and approvals.
2. WeKnora: multimodal ingestion/OCR, hybrid search, citations and **derived** wiki; not the signing or retention authority.
3. Agent Obsidian-compatible Markdown vaults: reviewable scoped working notes and approved links, not formal QMS controls.
4. Hindsight: scoped cross-session memory and reflections, never controlled QMS authority.
5. Telegram, mail, browsing and web search: transports or untrusted evidence sources; their content cannot grant tool permission.

```text
Human via Telegram text/voice, mail, Admin web
  -> identity/ACL, source classifier, immutable capture
  -> mandatory policy checks -> Laya typed route or rules fallback
  -> scoped WeKnora/QMS/vault/Hindsight retrieval
  -> optional CLM shortlisted-candidate scoring -> Hermes + selected model
  -> source/authority/semantic validation -> complete written answer
  -> independently composed short spoken explanation, if voice enabled
  -> named human reviews any controlled transition
  -> atomic QMS write + outbox -> notifications + trace

Claude Code interactive Superadmin -> read-only inspection/proposal MCPs
  -> versioned plan/diff -> human approval via Admin UI -> app policy gate.
```

## 2. System roles and boundaries

| Role | Responsibilities | Must never do autonomously |
|---|---|---|
| Superadmin in interactive Claude Code | Inspect code, knowledge quality, org RACI, agent skills, security, workflow completeness, ISO transitions; draft GitHub PRs/proposals and run safe tests | Modify production ACLs/controlled docs directly, impersonate stakeholder, use all mailboxes, self-approve a change |
| Normal app Admin | Set up departments, people, agent assignments, model policies, baselined workflows and delegation | Override QMS process-owner approvals merely by having IT/admin privileges |
| Process owner / quality appointee | Validate procedure and skill mappings, CAPA and audit programmes, propose controlled changes | Transfer top-management accountability or audit own process as independent auditor |
| Functional Hermes agent | Answer from scoped evidence, support human, draft action and handoff | Approve, sign, send external mail, close CAPA/NCR, grant access, publish SOP or sign audit finding |
| Human stakeholder | Supply context; verify transcript; approve tasks within explicit authorization | Use Telegram display name as identity or blanket approval of altered payloads |

Top management retains policy, resources, objectives and review decisions; the appointed quality representative coordinates, not supersedes them. The real roster, qualifications and delegations must be configured by a human.

## 3. Admin console and Workflow Studio

**Required screens:** tenant/org bootstrap; functions/departments and process tree; staff directory (name, title, email, phone, Telegram numeric ID after enrollment, timezone, contact preference, absence/delegates); roles/RACI and granular grant preview; agent deployment/skills/mailbox grants/memory bank and vault scope; connectors and credentials status; provider/model registry and spend policies; workflows and calendar/availability; evidence/document control; task and approval inbox; audit and ISO transition; traces, health and backups. Do not create an agent or connect mail automatically just because a staff member is added.

**Permissions:** separate platform Admin, org Admin, QMS manager, process owner, auditor, stakeholder and service account. Effective grants = tenant + role + project + resource classification + explicit mailbox scope + time-limited delegation; server enforces at every API/tool/retrieval call. Require strong admin authentication/MFA if available, short sessions, audit history, dual control on provider/permission/security policy changes. Admin preview of effective access must show what each agent can and cannot read.

**Provider registry:** models/services assigned separately for stakeholder reasoning, Superadmin interactive workbench (outside runtime registry), routing, ranking, embeddings, OCR/VLM, ASR, TTS. Support adapter capability declarations: context, tool calls, JSON schema, vision/audio, cost, locality, privacy, concurrency and measured performance. Begin with local Ollama Gemma 4; other Ollama tags and approved OpenRouter/Perplexity/OpenAI/Anthropic/Gemini APIs are **candidates**, each with its own verified terms, endpoint, capabilities, privacy/retention region, key, spend cap and fallback test. Never assume an LLM provider offers every feature or that a Perplexity user subscription pays for API usage. Prevent automatic cloud failover of confidential HR/legal/customer content. Only administrator-configured model policies may route sensitive payloads. Store keys in secrets manager; display masked references; test each model in an isolated sandbox before activating. OpenRouter's provider/model/price guardrails are useful but must be configured and evaluated. [A3]

**Workflow layers:** `Guideline` (approved process repo and licensed standard references) -> `Versioned template` (fixed control states/gates and criteria) -> `Case instance` (actual assigned humans, calendar availability, dates and deliverables). Human-created natural-language request enters AI-assisted Workflow Studio; the assistant proposes a structured graph with triggers, roles, RACI, tasks, deliverables, evidence, entry/exit criteria, decision points, exceptions, absence/delegation, escalation, SLAs, target dates and notifications. Validator checks missing assignee, dead-end/cycles, no evidence, conflicting SOP/version, separation-of-duties, unavailable qualified owner, unreachable due dates, missing approval, absent rollback and privacy risk. Unknown facts become explicit questions, not invented decisions. Simulate on synthetic case; qualified process owner/quality representative reviews diff and baselines exact version and effective date. Executing cases pin that version; migration is explicit, with owner approval and preserved trace. Scheduling reacts to calendar/absence but cannot weaken mandatory controls. Evolving audit findings can propose template improvements through review, never rewrite running cases silently. ISO 19011 informs audits. [A4]

## 4. ISO 9001:2026 and specialized references

ISO announced ISO 9001:2026 on 16 September 2026. Build versioned standard edition, adoption/transition, clause-reference mapping, process controls, documents, training, competencies, objectives, quality culture/ethical leadership evidence, risk/opportunity, interested parties, operational outputs, audits and management-review evidence. Verify all detailed normative clause mappings against the **licensed standard** and certification body's transition arrangement; do not reproduce unlicensed normative text or claim certification. Persist 2015/2026 edition applicability by time/contract; perform human-reviewed gap analysis and controlled document/skill update. Optional applicable references: ISO 19011:2018 auditing; ISO 10015:2019 competence; ISO 10005:2018 quality plans; ISO 10002:2018 complaints; ISO/IEC 25010:2023 software quality; ISO/IEC/IEEE 12207 software lifecycle and 15288:2023 systems lifecycle; OWASP ASVS application security. Standards are not automatically legal obligations or certifications. [A4][A5]

## 5. Functional agents and approved skills

Implement skill registry keyed `skill_id, version, hash, owner, role, trigger, process/SOP+revision, edition applicability, input/output schemas, allowed data scope, required evidence, prohibited actions, HIL gate, tests, review_due`. Production Hermes approved skill directories mounted read-only; proposals area separate. Skills teach how, but tools/API grant access. `skills.write_approval` (if supported in pinned Hermes) plus OS permissions and app registration gate. Claude Code builds initial drafts from actual process map/RACI/SOPs; functional human + QMS/security reviewer signs before activation. On revisions, run tests, re-train and deprecate former version; agent self-learning proposes diffs only. [A6][A7]

**Generic skills all agents need:** identity/scope check; source citation and original passage; authority/time classification; conflicting-evidence detection; commitment and owner extraction from mail; voice critical-fact readback; exact draft-for-approval; bounded cross-role handoff; privacy and prompt-injection defense; memory correction/deletion proposal; audit trace; fallback to human on uncertainty.

| Function | Draft domain skills for process-owner review | Mandatory approval |
|---|---|---|
| Finance/Accounts | contract-to-invoice evidence; invoice variance; payment exception; supplier invoice checks; cost of poor quality | Finance validates tax, payment, write-off, accounting entry |
| HR | competence matrix; training need and effectiveness; onboarding; job authorization; exit/access handoff | HR/manager assesses competence and employment decision |
| Recruitment | job criteria; candidate evidence matrix; interview pack; hiring decision trail; candidate data retention | Human panel hires; candidate records private |
| IT Admin | joiner/mover/leaver; access recertification; backup/restore drill; incident/change; key rotation; connector health | Authorized human grants access or executes privileged change |
| Engineering Delivery | requirements baseline; design/drawing/BOM change; review; test/calibration; field deviation; release pack | Named technical authority accepts design and release |
| Software Development | requirement-test trace; code review; release readiness; dependency/security; defect-to-CAPA; rollback | Human reviewer and release authority sign |
| Marketing/Sales | quotation/scope; requirements handoff; customer commitments; complaint intake; feedback; claim substantiation | Authorized human approves prices, terms and external claims |
| Quality appointee | process map/RACI; document control; CAPA/NCR; objectives; audit plan; ISO transition | Quality/process owners sign; management owns policy/resources |
| Top Management | objectives; resource/risk review; customer/supplier trends; culture/ethics; management review | Executives approve and record decisions |
| Legal/Contracts | contract clause extraction; obligation register; deviation/change order; confidentiality/retention | Counsel or legal signatory validates conclusions |
| Internal Auditor | risk-based scope; independence; sampling/interviews; evidence matrix; findings; follow-up effectiveness | Qualified independent auditor signs report and verification |
| Procurement/Supplier Quality | supplier qualification; purchasing specs; incoming issue; supplier-CAPA; scorecard | Named authorized buyer/quality owner decides |
| Production/Test/Service | work-instruction check; inspection/test; equipment calibration; delivery/service acceptance; nonconforming output | Qualified human accepts and releases |

Cross-functional bundles: complaint->investigation->CAPA->effectiveness; quotation->contract->engineering->procurement->finance; design change->software/test->quality release; recruit->competence->IT access; project/function audit->finding->owner action->independent verification; evidence->management review->resourced action. Handoffs send task ID, ACL-filtered citations, owner and status, not private vault/mail content.

## 6. Knowledge, memory and retrieval

**Original evidence:** file upload/scans/tables/images, mail per stakeholder, meetings, Telegram audio/text, approved human notes, Git-backed source changes; store original binaries and MIME, SHA-256, owner/classification, source and validity timestamps, revision/effective/superseded states and page/table/line offsets. Immutable original + reversible parsed/OCR result; dedupe by provider stable IDs and revision, not only hash. Update impacted WeKnora Wiki/Obsidian note by cited proposed delta after review; an email is evidence of communication but does not rewrite approved SOP. Index only authorized/current documents for normative answers and label historical results. Corpus includes text PDF, scanned PDF, multipage table, merged-cell XLSX, DOCX+image, screenshot and engineering diagram. [S1][S2]

**Mail:** the desktop mail client does not determine the backend, which must be identified: Microsoft Graph OAuth/delta for Exchange Online; Gmail OAuth/history/watch for Google; on-prem Exchange or supported IMAP adapter if required. Start with read-only fixture and opt-in mailboxes/folders/projects. Preserve individual messages, thread ancestry, quoted-body separation, dates and attachments. Cursors/delta/history recover missed notifications. Extract claims, owner/due date, customer commitment, dispute, exception, relevant CAPA as *proposals*. No global organization-mail search; send/forward/archive/delete require separate human gate. [S3][A8][A9]

**Hindsight:** local self-host candidate for Hermes plugin. Bank per tenant+principal+role (separate shared bank for reviewed cross-team lessons); verify Hermes plugin `bank_id_template`/isolation in pinned release. Retain selected verified preferences/lessons and references, not raw all-mail, privileged legal, candidate CV, credentials or uncertain voice transcripts. Reflect/recall are expensive, so async queue and per-task budget. Memory may suggest a question but must never establish a controlled fact; support correction, expiry and restore. [A10]

**second-brain-os:** assess vault template `raw/wiki/projects/templates/output`, ingestion/review/privacy/graph skills and agent definitions; adapt permitted structures, do not auto-install third-party skills. **K-Plex:** optional Obsidian human visual editor of related vault notes, not agent recall backend. **Webcmd:** optional read-only browser to allowlisted portals without APIs; learned navigation is not live evidence, inspect its privacy/first-visit cloud seed, use separate browser profiles, require exact approval for website writes. [A11][A12][A13]

**Retrieval tier:** session cache -> authorized per-agent Hindsight/vault -> WeKnora hybrid retrieval with ACL and approved revision filters -> structured QMS records/graph -> model synthesis with exact citations/conflict. Do not make 256K prompt accumulation the substitute for retrieval.

## 7. Decision layer and provider benchmark

Laya specifically `NandhaKishorM/laya` for bounded typed routing: route to role/knowledge source, choose retrieval/no-retrieval, urgency and escalation. Deterministic high-risk policy gates precede it, and fallback is rules-only. Calibrate multilingual model on fixture transcripts in the organization's actual working languages and domain terms; default to retrieval/escalation when uncertain. **CLM-v0.1-8B** optional ranking of an already retrieved large/stable shortlist of documents/tools/actions: Qwen3-8B pooled encoder plus CLM head and state-action candidate caching; requires pinned compatible setup and GPU fit benchmark; not a complete retriever. Never assume it can co-run with Gemma4 at 256K on 12 GB VRAM. WeKnora hybrid search and reranking remain primary evidence retrieval. No Azure AI Search dependency unless a separately approved cloud adapter is selected. [A14][A15][A16]

For Ollama `gemma4:12b`, 256K is a published model limit, not proven throughput. Under-24-GiB VRAM Ollama can default far below that; configure `num_ctx`, inspect actual allocation and GPU/CPU offload. Benchmark 8/16/32/64/128/256K, concurrency one then two, p50/p95 response, peak DRAM/VRAM, citation accuracy at middle/end, JSON tool-call reliability; document OOM and safe fallback. Admin must see measured cap per provider. [A17][A18]

## 8. Telegram written and natural spoken behavior

Reuse the owner's Digital-Secretary project as an **upstream UX/adapter reference**, with code/license/security review. Telegram direct messages from enrolled numeric user IDs by default; preserve update IDs and session ID; do not infer identity from display name. For voice input: download original -> private object store + hash -> local ASR/transcript/confidence -> request clarification of ambiguous names/dates/amounts/approval -> QMS answer/action proposal. Answer stores **complete evidence-backed written response** plus **independently worded brief spoken explanation** grounded solely in checked text, never simply reads the whole message; on “read it” request, read selected text verbatim; on “explain”, provide fresh explanation. TTS local by default for confidential info; inspect Digital-Secretary's actual speech dependency (edge-tts may transmit). Check semantic consistency of speech for numbers/negation/approval state. On audio service outage, send text only with status. Telegram voice notes are asynchronous, not full-duplex calls. Human approval is a distinct authenticated workflow, not an ambiguous voice instruction. [A19][A20]

## 9. Work items and audit proof

States `detected -> triaged -> proposed -> evidence_checked -> human_review -> approved/rejected -> executed -> independently_verified -> closed`; include rework/blocked/overdue. Every transition records actor, authority, time, exact payload hash+expected_version, cited source spans, model and prompt/skill versions, who approved, consequence, undo policy and trace. No LLM-accessible `approve` API. Application-authorized approver with a fresh nonce approves digest of exact recipients/body/attachments/document revision; if proposal changes, repeat approval. Use DB transactional outbox for notifications with idempotent delivery and last known external message IDs. Independent auditor must not approve own finding or verify own remediation when independence requires another reviewer.

Tables: tenant, function, person, role, grants, delegation, principal_telegram, agent_profile, skill_registry, model_registry, workflow_guideline, workflow_template, workflow_instance, approvals, sources/versions/spans, assertion/conflict, document_revisions, complaints, CAPAs, audits/findings, actions, management_reviews, mail_messages/cursors, voice_turn, memory_manifest, outbox, audit_events and ISO edition/mapping. Application API `/api/v1` provides authenticated CRUD/proposal endpoints, review/approval, trace, health and reporting. Use Pydantic/OpenAPI, Postgres migrations, expected_version and unique idempotency key; original objects in backed-up private storage. No raw SQL/shell/global mail search tools exposed to agents.

## 10. Local deployment, GitHub CI, Vercel preview

GitHub repository holds source, schema, docs, approved **generic** skill definitions, synthetic fixtures, CI and a current `docs/HANDOFF.md`; never secrets, HR/candidate mail, source PDFs with confidential content, Hindsight banks or actual stakeholder vaults. PRs run formatter/type/lint/unit/integration tests with fake providers and a secret scan. Do not attach a privileged self-hosted GitHub runner to the production laptop for untrusted PRs. [A21]

Docker Desktop/WSL2 on Windows laptop runs QMS API, Postgres, workers, object store, Hermes, WeKnora and dependencies, vaults, Hindsight, Telegram gateway, optional Laya/SearXNG/speech. Ollama can run on host via private network or GPU-enabled Linux container after verification. Cloudflare Tunnel + Access optionally publishes only authenticated Admin web, not Ollama/DB/WeKnora admin. Telegram long polling is outbound; no tunnel needed for bot ingress. Laptop availability, snapshots/offsite backups, disk exhaustion and restart reconciliation are operational constraints.

Vercel GitHub preview is **only** for separately deployed Admin frontend backed by synthetic/mock API initially; protect previews. No private QMS evidence or production secrets in preview. Vercel functions have read-only deployment filesystem and limited scratch/finite runtime; do not move persistent Obsidian vaults, long-running Hermes/WeKnora, Postgres, model weights or OCR workers there. Production frontend hosting on Vercel is a later reviewed choice with protected connectivity, availability and data policy. [A22][A23]

## 11. Repo shape and Claude Code Superadmin pack

```text
qms-virtual-org/
  CLAUDE.md                  # short project guardrails and where to read next
  INTENT.md                  # project-specific vision; not a special Claude Code loader
  README.md  compose.yaml  .env.example  pyproject.toml
  docs/SPECIFICATION.md     # this document (source for implementation)
  docs/HANDOFF.md           # up-to-date concise session state, not historical diary
  docs/DECISIONS.md docs/ROADMAP.md docs/UPSTREAMS.md docs/RACI.md
  docs/CONNECTORS.md docs/MCP_GUIDELINES.md docs/SECURITY.md
  docs/ISO_9001_2026_TRANSITION.md docs/SKILL_CATALOG.md
  docs/RUNBOOK.md docs/BENCHMARKS.md docs/PR_TEMPLATE.md
  .claude/rules/{security,workflow,connectors,testing}.md
  .claude/skills/{handoff,review-org,workflow-check,iso-gap,
                  audit-knowledge,inspect-security,review-model,review-connector}/SKILL.md
  .mcp.example.json         # example only; do not enable production secrets
  apps/{api,worker,admin-web,telegram-gateway}/
  packages/{domain,policy,workflow,retrieval,agent-runtime,memory,
            providers,voice,mail,standards}/
  agents/profiles/          # versioned agent configs, not credentials
  skills/{common,finance,hr,recruitment,it,engineering,software,
          sales,quality,management,legal,auditor,procurement,service}/
  adapters/{weknora,hermes,hindsight,laya,clm,ollama,mail,webcmd}/
  infra/{weknora,searxng,cloudflare}/ migrations/ tests/ scripts/
```

**CLAUDE.md (under ~200 lines):** identity, boundaries, source of truth, build/test commands, read `docs/HANDOFF.md` then spec/decisions, one slice per PR, never claim untested connection, update handoff at end. Project skills live under `.claude/skills/<name>/SKILL.md`; task-specific skills load on invocation, and privileged actions should use `disable-model-invocation: true`. `.claude/rules/` hold scoped instructions. Claude Code's local auto-memory is useful but not a GitHub-shared source of truth; `HANDOFF.md` is explicit and versioned. Instruction files are context, not enforcement; enforce permissions in settings and app. [A24][A25]

**Superadmin skill requirements:** review-org, inspect-workflow-completeness, iso-gap, access-segregation, skill-governance, knowledge-integrity, model-provider-review, connector/MCP-audit, security-review, repo-handoff. All produce review reports/patch proposals; no direct publish. MCP servers: GitHub read/search PR, QMS evidence read and workflow **proposal**, optionally scoped WeKnora read; begin with zero direct write connectors. Keep secrets/privileged local MCP definitions in user/local settings; `.mcp.example.json` has placeholders only; promote vetted shareable `.mcp.json` later. Test least-privilege and prompt injection. Never ask Claude Code to commit production credentials or grant itself broad QMS access. [A26]

**GitHub process:** `main` protected, short branches and PR review, CI on synthetic fixtures, no real evidence in public issues. At the end of *each stage* ask Claude Code to (1) run tests and record exact results, (2) update `docs/HANDOFF.md`, `docs/DECISIONS.md`, roadmap and any runbook, (3) make a commit on branch with only reviewed code/docs, (4) open a PR or prepare PR instructions as authorized by the human. A commit/push/PR is an external write: human explicitly authorizes the actual operation in their IDE. If offline, handoff remains locally saved and must be committed before switching devices.

## 12. MVP and production gates

**MVP-0:** upstream inspection/license/version matrix, Git scaffold, Docker config, synthetic fixtures, provider contract, Ollama benchmark plan. Exit: one safe fixture startup and no unverified feature claim.

**MVP-1:** Auth and org Admin UI (departments, humans, role/grant preview, selective agents), Postgres+object store, auditable versioned workflow/template engine with human approvals and admin workflow proposal form using local model or rules. Exit: no self-approval; proposed audit workflow fails completeness until missing control fixed.

**MVP-2:** WeKnora ingestion + citations for mixed document fixtures, QMS evidence, initial skills/quality+project Hermes profiles and Telegram text simulator. Exit: exact cited answer, approved revision filter, cross-role denial.

**MVP-3:** Telegram voice using Digital-Secretary pattern; local ASR/TTS; two-dimensional answer (full text + brief spoken explanation), human correction and provenance. Exit: spoken/typed numerical consistency, read-it mode, reboot recovery.

**MVP-4:** Read-only fixture mail then one authorized live provider; Hindsight isolated banks and knowledge/vault sync; Laya router with rules fallback; CAPA/customer complaint end-to-end; limited role pack. Exit: duplicate mail/update replay safe, memory cross-bank denied, external messages remain drafts until human review.

**Production-1:** full model registry (all approved providers, privacy/cost controls), approved role skill packs, org-wide RACI/ISO edition mapping, audit and management-review, calendar/delegation and Workflow Studio simulation; security reviews and DLP policy.

**Production-2:** independent penetration/privacy/backup/restore drill, active monitoring, retention/legal hold, alerting/RPO-RTO, performance benchmark, durable upgrade/migrations, staged rollout. Optional CLM/Webcmd/K-Plex/Vercel real-API integration only after explicit go/no-go and separate threat model. External API pricing and actual 256K operational context must be measured.

**Release blockers:** unauthorized source leaks; action without named human approval; voice contradicts text; unsupported formal answer; missing ability to restore; incorrect ISO clause assumption; uncaught provider data transfer; silently changed running workflow; role skill auto-activation without review.

## 13. Acceptance journeys

1. Admin adds human and department, assigns zero agents by default; explicitly enrolls agent, grants scoped mail/vault access and exact Telegram ID. Non-assigned user has no Hermes access.
2. Admin describes project audit in natural language; system asks missing criteria; plans eligible independent auditor around actual availability; baseline published only after reviewed complete graph; project finding later proposes, but does not auto-publish, changed future workflow.
3. Project lead voice reports overdue supplier CAPA. Original audio and confirmed transcript preserved; QMS approved due date and scoped email compared; full written cited answer plus short conversational voice explanation; agenda proposal and notification require separate appropriate approval. Repeat Telegram update yields one work item.
4. Auditor requests Finance private mailbox; denied with no snippet; false bank memory corrected; no action authorized by external doc prompt injection.
5. Claude Code Superadmin inspects ISO gap and skill changes, drafts PR and proposal; QMS Admin independently approves baseline in app; no credential exposure or direct DB update.
6. On reboot/LLM outage/mail cursor expiration, pending approval/work queue persist, sync reconciles idempotently, operator sees explicit degraded state. All production claims have a measured test and trace ID.

## 14. Decision log and open inputs

**Frozen:** interactive Claude Code Superadmin vs app Admin; provider-neutral Hermes runtime; local-first initial deployment; GitHub source/CI; synthetic Vercel UI preview only; humans approve QMS control; WeKnora/Hindsight/vault separation; Digital-Secretary spoken-summary experience; ISO 9001:2026-aware control mapping.

**Organization to supply:** named department owners and auditors; whether ISO 9001 certification/transition exists; licensed standard and SOP corpus; mail provider behind the desktop mail client; calendars; voice languages and TTS privacy; contact data and retention rules; Telegram bot per role vs shared; allowed cloud providers/data classes; domain and Vercel preview protection; required actual 256K/latency targets; RPO/RTO and approved backups. Start fixtures while awaiting answers. No inference about statutory obligations or real approvals.

## 15. Upstream source register (exact URLs to inspect)

| ID | URL | What to verify |
|---|---|---|
| A1 | https://code.claude.com/docs/en/agent-sdk/overview | SDK vs interactive Claude Code and third-party authentication |
| A2 | https://support.claude.com/en/articles/11145838-use-claude-code-with-your-pro-or-max-plan | Subscription use for interactive tool |
| A3 | https://openrouter.ai/docs/guides/features/guardrails | model/provider/data/spend controls |
| A4 | https://www.iso.org/standard/70017.html | ISO 19011 audit programme / competence |
| A5 | https://www.iso.org/news/2026/09/ISO9001-2026 | ISO 9001:2026 release; get licensed text separately |
| A6 | https://hermes-agent.nousresearch.com/docs/user-guide/features/skills | skills discovery and write approval |
| A7 | https://agentskills.io/specification | SKILL.md conventions |
| A8 | https://learn.microsoft.com/en-us/graph/delta-query-messages | Exchange Online deltas |
| A9 | https://developers.google.com/workspace/gmail/api/guides/push | Gmail notifications/history |
| A10 | https://github.com/vectorize-io/hindsight | local persistent agent memory |
| A11 | https://github.com/undefined-ui/second-brain-os | vault and skill template candidates |
| A12 | https://community.obsidian.md/plugins/k-plex | optional human graph UI |
| A13 | https://github.com/agentrhq/webcmd | optional browser workflow; cloud seed privacy |
| A14 | https://github.com/NandhaKishorM/laya | specifically requested typed router |
| A15 | https://github.com/Contrastive-LM/CLM | GPU candidate scoring |
| A16 | https://huggingface.co/Contrastive-LM/CLM-v0.1-8B | checkpoint architecture and runtime |
| A17 | https://ollama.com/library/gemma4:12b | model variants and published context |
| A18 | https://docs.ollama.com/context-length | actual context configuration |
| A19 | Digital-Secretary (owner's repository; location kept outside this repository) | own Telegram voice UX modules and implementation |
| A20 | https://core.telegram.org/bots/api | voice files and updates |
| A21 | https://docs.github.com/en/actions/reference/security/secure-use | CI runner security |
| A22 | https://vercel.com/docs/deployments/environments | synthetic PR previews |
| A23 | https://vercel.com/docs/functions/runtimes | ephemeral read-only filesystem constraint |
| A24 | https://code.claude.com/docs/en/memory | CLAUDE.md and auto-memory vs Git handoff |
| A25 | https://code.claude.com/docs/en/skills | project and invocation-controlled skills |
| A26 | https://code.claude.com/docs/en/mcp | scoped MCP configuration and server trust |
| A27 | https://github.com/Tencent/WeKnora | canonical evidence retrieval candidate |
| A28 | https://github.com/NousResearch/hermes-agent | runtime agent and gateway |
| A29 | https://github.com/searxng/searxng | opt-in public search, no private queries |
| A30 | https://github.com/cloudflare/cloudflared | optional authenticated tunnel |
| A31 | https://obsidian.md/help/data-storage | Markdown vaults are local files |
| A32 | https://github.com/anthropics/claude-agent-sdk-python | optional future SDK only |
| A33 | https://www.iso.org/standard/69459.html | competence guidance |
| A34 | https://www.iso.org/standard/70398.html | project quality-plan guidance |
| A35 | https://www.iso.org/standard/71580.html | complaints-handling guidance |
| A36 | https://www.iso.org/standard/78176.html | software quality model |
| A37 | https://www.iso.org/standard/81702.html | system life-cycle guidance |
| A38 | https://owasp.org/www-project-application-security-verification-standard | app security verification |
| A39 | https://github.com/allenporter/home-assistant-laya | old chat candidate, NOT chosen Laya |
| A40 | https://github.com/aayushch/laya | old chat candidate, NOT chosen Laya |
| A41 | https://github.com/razorback16/openjev | old chat OpenJev candidate, not chosen |
| A42 | https://github.com/GPT-AGI/OpenJev | old chat OpenJev candidate, not chosen |
| A43 | https://github.com/kyegomez/open-jev | old chat OpenJev candidate, not chosen |

[S1] = attached original composite framework Markdown; [S2] = attached original 21-page PDF; [S3] = attached project chat including first-class mail requirements. For every adopted upstream create an entry in `docs/UPSTREAMS.md` with commit/tag, checked date, license for code and weights, API, privacy behavior, OS/GPU fit and passing tests. Similar names do not imply compatible repos.
