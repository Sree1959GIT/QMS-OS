# QMS OS — Local-model benchmark plan (MVP-0 slice 4)

Status: **plan only.** Nothing in this file has been measured. No benchmark harness, adapter, recording or result
exists. Every number in *Pass criteria* is **proposed, Admin to set** unless the row names the specification or a
decision that states it. Results, when they exist, are added under *Results* by a later pull request.

## 1. Scope and rules

- **Runtime-neutral (R-26).** The plan measures provider entries, not one product. Ollama `v0.40.0` with
  `gemma4:12b` is the first case (`docs/UPSTREAMS.md`, Tier B); other runtimes and models are added as provider
  entries, each with its own `docs/UPSTREAMS.md` entry (network and update behaviour) and an egress classification
  rule before its adapter may be enabled (R-26).
- **Specification scope covered.** `docs/SPECIFICATION.md` section 7, lines 99 to 103 (context lengths, concurrency,
  latency, memory, citation accuracy, JSON tool calls, out-of-memory behaviour and safe fallback, a measured cap per
  provider; no assumption that a second model co-runs with Gemma4 at 256K on 12 GB VRAM), and section 12, line 158
  (MVP-0: "Ollama benchmark plan"). The specification is not edited.
- **Through the provider contract (ADR 0005).** Every benchmark call goes through `ProviderGateway.call`, so no run
  bypasses the allow-list, the egress class, the data-class ceiling or `model_digest`, and every call is logged
  without content (R-18). Each benchmarked entry is `local` and records its `model_digest` (R-21, R-25).
- **Integration mode.** The provider registry refuses `live` adapters (R-25). Benchmark runs therefore need a
  `test`-mode adapter for the runtime under test; that adapter and the harness do not exist yet and are a later
  slice with their own review (see *Open items*).
- **Runtime settings recorded per run.** For Ollama: `ollama --version`, the model-layer digest, the requested
  `num_ctx` and the context shown by `ollama ps` (UPSTREAMS: a new `num_ctx` reloads the model; the desktop app can
  update itself, so the version is recorded every run). Running with cloud features off (`OLLAMA_NO_CLOUD=1`) is
  proposal R-27; until it is decided it is recorded per run, not assumed.
- **Not covered:** cloud providers, routing (Laya), ranking (CLM), embeddings, OCR and text to speech. They get their
  own rows only when an Admin adds them as provider entries.

## 2. Test dimensions

- **B1 Context length.** Method: synthetic prompts filled to 8K, 16K, 32K, 64K, 128K and 256K tokens (spec line 103);
  the runtime's context set per request where it can be (Ollama native API `num_ctx`) and the actual allocation read
  back. Ladder upwards; stop at the first length that fails twice. Recorded: requested and actual context; completed
  or out of memory; GPU/CPU split; the largest passing length (the **measured cap**, shown to the Admin, spec line
  103).
- **B2 Concurrency.** Method: one request at a time, then two at once (spec line 103), at each passing length.
  Recorded: per-request latency at 1 and 2; errors; whether the runtime queued or ran both.
- **B3 Memory on the 12 GB host.** Method: peak VRAM and peak DRAM sampled during B1 and B2; the model alone, then
  with the API stack running. A second model is never assumed to fit alongside (spec line 101): co-running is a
  separate run, `not run` until an Admin adds it. Recorded: peak VRAM; peak DRAM; offload; out-of-memory events and
  what the system did after one (the **safe fallback**, spec line 103).
- **B4 JSON tool calls.** Method: a fixed set of synthetic prompts, each offering tools with a JSON schema; the reply
  is validated against the schema. Recorded: share of schema-valid calls; calls to tools not offered; malformed JSON.
- **B5 Latency.** Method: fixed synthetic prompts with a capped output length, repeated per cell. Recorded: p50 and
  p95 response time (spec line 103); time to first token.
- **B6 Citation accuracy.** Method: a synthetic corpus with known facts placed in the middle and at the end of the
  context (spec line 103). Recorded: share of answers citing the correct passage, middle and end separately.
- **B7 Audio input capability.** Method: a probe first: one synthetic audio clip sent to the entry under test. For
  Ollama `gemma4:12b` the audio question is open in `docs/UPSTREAMS.md` (code read and a partial metadata read only,
  **not run**). Recorded: accepted or refused; error text; if refused, audio work (B8) moves to another provider entry
  chosen by the Admin.
- **B8 Speech recognition.** Method: recordings in English with Indian and American accents, with and without
  shop-floor noise, containing QMS vocabulary, numbers and dates; scored against a human-checked reference transcript.
  Recorded: word error rate per accent and noise condition; error rate on QMS terms; numbers, dates and amounts
  misrecognised, and whether low confidence triggered a clarification request (spec section 8, line 107); real-time
  factor.

## 3. Pass criteria

No threshold below has been measured or approved. "Proposed, Admin to set" means a starting value for discussion,
not a decision. The specification states test points (context lengths, concurrency one then two) and asks for a
measured cap, but no numeric targets; section 14 ("Decision log and open inputs", line 187) lists "required actual
256K/latency targets" as something the organisation supplies.

- **Context length passes:** 10 of 10 runs complete without out-of-memory at that length. *proposed, Admin to set.*
- **Measured cap:** the largest length that passes; shown to the Admin per provider. *required by the specification
  (line 103); no minimum stated.*
- **Required context:** a minimum cap the entry must reach (for example 32K). *organisation to supply (spec section
  14, line 187); none proposed here.*
- **Concurrency 2:** no errors; p95 at concurrency 2 at most twice the p95 at concurrency 1. *proposed, Admin to set.*
- **Peak VRAM:** no out-of-memory event; peak at or below 11.0 GB of 12 GB. *proposed, Admin to set.*
- **Peak DRAM:** at or below 48 GB of 64 GB with the API stack running. *proposed, Admin to set.*
- **Safe fallback:** after an out-of-memory event, the call fails with a recorded error and no partial answer is used.
  *proposed, Admin to set.*
- **JSON tool calls:** at least 98 % schema-valid; 0 calls to tools not offered. *proposed, Admin to set.*
- **Latency:** p95 at most 20 s at 8K, concurrency 1, output capped at 512 tokens. *proposed, Admin to set (spec
  section 14, line 187: organisation to supply).*
- **Citation accuracy:** at least 90 % correct, middle and end separately. *proposed, Admin to set.*
- **Word error rate:** at most 10 % quiet, at most 20 % with shop-floor noise, per accent group. *proposed, Admin to
  set.*
- **QMS term error rate:** at most 5 %. *proposed, Admin to set.*
- **Numbers, dates, amounts:** 0 misrecognised values that pass without a clarification request. *proposed, Admin to
  set (spec line 107 asks for clarification of ambiguous names, dates and amounts).*
- **Speech real-time factor:** at most 0.5. *proposed, Admin to set.*

## 4. Data rules

- Real QMS documents and audio recordings stay on the Admin's machine, untracked and outside the repository (R-23).
- Only aggregate results enter the repository: no titles, numbers, names, paths, transcripts or audio (R-23, R-8,
  R-11). Recording sets are described by count, total duration, accent group and noise condition only.
- Fixtures and prompts in the repository are synthetic and visibly fictional (R-11, `tests/test_fixture_hygiene.py`).
- A call built from real QMS material is `confidential` (R-24) and may go only to a `local` or `org_private` entry
  (R-19). Benchmark calls on synthetic text state `public` (proposed; every call states a class, R-24).
- The model egress log holds no prompt or response content (R-18); benchmark notes follow the same rule.

## 5. Outputs and gates

**Order of runs** (each step only after the previous one is recorded):

1. Environment record: host profile, runtime version, model digest, settings (section 1), cloud setting (R-27).
2. B7 audio probe (one synthetic clip), so that B8 knows which provider entry to use.
3. B1 context ladder at concurrency 1, with B3 memory sampling and B5 latency.
4. B2 concurrency 2 at each passing length.
5. B4 JSON tool calls and B6 citation accuracy at the measured cap and at 8K.
6. B8 speech recognition on the Admin's recordings, on the Admin's machine.
7. Optional co-running runs, only if an Admin adds a second model.

**What counts as "not run":** a cell with no completed measurement on the recorded runtime version and model digest.
That includes runs that were aborted, runs on a different version or digest, and runs without an environment
record. A "not run" cell is written as `not run`, never left blank, never 0 and never inferred from another model,
length or host.

**Results table template** (one row per provider entry, length and concurrency; aggregates only):

Columns, in order: run date; provider entry; model digest; runtime version; host profile; cloud off (R-27);
context requested and actual; concurrency; runs; p50 and p95 (s); peak VRAM and DRAM (GB); GPU/CPU split;
out-of-memory events; JSON valid (%); citation accuracy middle and end (%); status (`pass`, `fail` or
`not run`). Until a run is recorded, every row reads `not run`.

Speech results use a separate table: provider entry, model digest, accent group, noise condition, recordings,
total minutes, word error rate, QMS term error rate, values misrecognised and flagged, real-time factor, status.

**Before a live adapter** (a benchmark pass is necessary, not sufficient):

- two-admin approval of widening provider changes exists; until then the registry refuses `live` adapters (R-25);
- `model_digest` recorded and required for the entry (R-21, R-25);
- Ollama classified by endpoint host, not only by model name (ADR 0005);
- cloud features off for Ollama (R-27, **proposal**, Admin to confirm);
- the runtime has its `docs/UPSTREAMS.md` entry and an egress classification rule (R-26);
- the entry's measured cap and pass/fail per metric shown to the Admin (spec line 103).

## 6. Open items (questions for the Admin)

1. **Thresholds:** confirm, change or reject each "proposed, Admin to set" value in section 3, and supply the required
   context and latency targets (spec section 14, "Decision log and open inputs", line 187).
   *Admin's lean (not decided): accept the proposed values as starting values.*
2. **Host:** which machine runs the benchmark, and is it the specification's target (i9, 12 GB VRAM, 64 GB DRAM)?
   Its GPU model, driver and actual memory are not measured. Ollama on the Windows host or in a WSL2 container
   (R-16 note, a proposal)?
3. **Audio set size:** how many recordings per accent group and noise condition, of what length, recorded by whom and
   with what consent; which accents beyond Indian and American, and which working languages (spec section 14,
   "Decision log and open inputs", line 187: voice languages to be supplied).
4. **Repetitions:** runs per cell (10 is assumed in section 3) and the output-length cap.
5. **Speech provider:** if the B7 probe shows that the first entry does not accept audio, which provider entry the
   Admin adds for speech recognition (each needs its own UPSTREAMS entry, R-26).
6. **Citation corpus:** size of the synthetic corpus and how facts are placed for B6.
7. **Co-running:** whether a second model (embeddings, ranking) alongside the first is measured in this plan or later.
8. **Harness and `test`-mode adapter:** which slice builds them, and their review before any run.
   *Admin's lean (not decided): a new slice 4b builds the harness and the `test`-mode adapter.*
9. **Cloud setting for runs:** whether benchmark runs must use `OLLAMA_NO_CLOUD=1` before R-27 is decided.
   *Admin's lean (not decided): yes, benchmark runs use `OLLAMA_NO_CLOUD=1`.*
10. **Where results go:** this file's *Results* section or a separate results file, and the approval of each results
    pull request.
    *Admin's lean (not decided): a separate results file, with one results pull request per run set.*

## Results

None. Every cell is `not run`.
