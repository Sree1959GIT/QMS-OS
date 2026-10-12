# QMS OS — Local-model benchmark plan (MVP-0 slice 4)

Status: **plan only.** Nothing in this file has been measured. No benchmark harness, adapter, recording or result
exists. Every number in *Pass criteria* is **proposed, Admin to set** unless the row names the specification or a
decision that states it. Results, when they exist, are added under *Results* by a later pull request. The host and
Docker facts in section 1 were supplied by the Admin on 2026-10-11; they were not measured by Claude Code.

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

### Benchmark host (Admin-supplied facts, 2026-10-11; not measured by Claude Code)

- CPU Intel Core i9-13900HX; memory 96 GB installed, 95.7 GB usable (as reported by Windows); GPU NVIDIA GeForce
  RTX 4080 Laptop GPU with 12,282 MiB, and an Intel UHD integrated GPU; Windows 11 Home 10.0.26200.
- NVIDIA software: `nvidia-smi` 617.14, kernel-mode driver 617.14, CUDA user-mode driver 13.4; driver model WDDM.
  At idle: 0 MiB used, performance state P8, 2 W of an 80 W power cap, 49 C.
- No device or product IDs are recorded.
- The specification's target is 64 GB DRAM (`docs/SPECIFICATION.md`, line 5); this host has 96 GB, so results from
  it do not show that a 64 GB machine passes.
- The host runs plugged in. Each run records the power mode, the plugged-in state, the GPU temperature and the GPU
  in use (the RTX 4080, not the integrated GPU).

### Docker on the host (Admin-supplied facts, 2026-10-11; not measured by Claude Code)

- Docker Desktop v4.94.0 on WSL2 (`wsl -l -v`: `docker-desktop`, version 2); 45.82 GB of memory and 32 CPUs
  available to containers.
- An Ollama container already exists on the host: image `ollama/ollama:0.32.1`, digest
  `sha256:6345fbc18bd73a1e16404be681dbc6fd291a027cab43ed541abe78c4c81051b0`. It requests one NVIDIA GPU
  (configuration only; the container is stopped, so GPU use is not shown to work); it has no `OLLAMA_NO_CLOUD`;
  `OLLAMA_HOST=0.0.0.0:11434`; port published as `11434:11434`; it is in the `n8n-services` stack together with
  `cloudflare-tunnel`. A tunnel hostname exists in the local Cloudflare configuration (Admin-supplied; the hostname
  and path are not recorded here); the dashboard route and any Access policy are not checked, so whether the tunnel
  exposes this container is not checked (the specification, line 119, says the tunnel must not publish Ollama).
- **That container is not the benchmark target:** Ollama 0.32.1 is not researched in `docs/UPSTREAMS.md` (`v0.40.0`
  is), and the image is referenced by tag, not by a digest-pinned reference (R-21). Benchmark runs use the dedicated
  container in the pre-run checklist (section 5).

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
  separate run, `not run` until an Admin adds it. Recorded: peak VRAM; container and host peak memory; offload;
  out-of-memory events and what the system did after one (the **safe fallback**, spec line 103).
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

Units: **MiB** = 2^20 bytes and **GiB** = 2^30 bytes (as `nvidia-smi` reports GPU memory); **GB** = 10^9 bytes.
The specification's "12 GB VRAM" and "64 GB DRAM" and Windows' memory figures are quoted as written there.

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
- **Peak VRAM:** no out-of-memory event; peak at or below 11,264 MiB (11 GiB) of the host GPU's 12,282 MiB.
  *proposed, Admin to set.*
- **Peak DRAM:** at or below 48 GB of 64 GB with the API stack running, measured on the host. *proposed, Admin to
  set.* Caveat: memory inside the benchmark container is capped by the Docker allocation (45.82 GB at present,
  section 1), so the container alone cannot reach 48 GB; each run records the container's peak memory and the
  host's peak DRAM separately.
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

**Pre-run checklist** (every item true before step 1; otherwise every cell stays `not run`):

- a dedicated benchmark container, not the existing one in section 1, built in slice 1b (open item 11);
- Ollama `v0.40.0`, image pinned by digest (R-21; `docs/UPSTREAMS.md` records the `ollama/ollama:0.40.0` digests);
- outside the `n8n-services` stack;
- port published on `127.0.0.1` only;
- `OLLAMA_NO_CLOUD=1` set (R-27 is a proposal; this is the Admin's lean on open item 9);
- `nvidia-smi` inside the container shows the RTX 4080;
- the host plugged in.

**Order of runs** (each step only after the previous one is recorded):

1. Environment record: host profile, runtime version, model digest, settings (section 1), cloud setting (R-27),
   power mode, plugged-in state, GPU temperature and the GPU in use.
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
context requested and actual; concurrency; runs; p50 and p95 (s); peak VRAM (MiB); peak container memory (GB);
peak host DRAM (GB); GPU/CPU split; out-of-memory events; JSON valid (%); citation accuracy middle and end (%);
status (`pass`, `fail` or `not run`). Until a run is recorded, every row reads `not run`.

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
2. **Host:** *answered by the Admin (2026-10-11):* the host in section 1 (Admin-supplied facts, not measured by
   Claude Code), running a dedicated WSL2 container (pre-run checklist, section 5). It has 96 GB of memory against the
   specification's 64 GB, so results do not show a 64 GB machine passing. The R-16 note on shared deployments stays
   a proposal.
3. **Audio set:** *decided by the Admin (2026-10-11):* four cells (Indian and American accents, each quiet and with
   shop-floor noise), 20 clips per cell (80 in all), 15 to 30 seconds each, scripted from synthetic QMS text; the
   speakers are the Admin and willing colleagues, whose written consent is kept off the repository (R-23); English
   only for now (spec section 14, "Decision log and open inputs", line 187: voice languages to be supplied).
4. **Repetitions:** 10 repetitions per cell and a fixed output cap of 512 tokens. *Proposed, Admin to set.*
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
11. **Dedicated benchmark container:** built in a new slice, 1b, before any run, to the pre-run checklist in
    section 5 (ROADMAP slice 1b, not started).

## Results

None. Every cell is `not run`.
