# QMS OS — Local-model benchmark plan (MVP-0 slice 4)

Status: **plan only.** No benchmark cell in this file has been measured. A harness and a test-mode adapter exist (section
7) but have not run against a real model; no recording or result exists. Every number in *Pass criteria* is **proposed,
Admin to set** unless the row names the specification or a decision that states it. Results, when they exist, are added
under *Results* by a later pull request. The host and Docker facts in section 1 were supplied by the Admin on 2026-10-11;
they were not measured by Claude Code. The container checks and the smoke test in section 5 were run by the Admin on
2026-10-12 (Admin-supplied output, not measured by Claude Code); they are not benchmark results.

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

- a dedicated benchmark container, not the existing one in section 1: service `ollama-bench` in `compose.yaml`,
  profile `benchmark` (never started by default or in CI), host port `11435` (slice 1b; open item 11). *Started by
  the Admin on 2026-10-12:* image pulled, volume `qms-os_qmsos_ollama_bench_models` created, container started;
- Ollama `v0.40.0`, image pinned by digest (R-21): `ollama/ollama:0.40.0`, index digest
  `sha256:1bef639749741b375e9a1eb2c1346fb57ce52f5432de1f74846e44ccc18e1687`, read from the registry with
  `docker buildx imagetools inspect` on 2026-10-12 (the same digest `docs/UPSTREAMS.md` records; no `v0.40.0` tag).
  *Checked by the Admin, 2026-10-12:* the digest-pinned image was pulled; `ollama --version` reports 0.40.0;
- outside the `n8n-services` stack. *Checked by the Admin, 2026-10-12:* compose project `qms-os` (config file the
  repository's `compose.yaml`), service `ollama-bench`; the image ID `sha256:2b28812c…2746` is the linux/amd64
  digest of the pinned index;
- port published on `127.0.0.1` only (`127.0.0.1:11435:11434`). *Checked by the Admin, 2026-10-12:* `docker port`
  shows `11434/tcp -> 127.0.0.1:11435`;
- `OLLAMA_NO_CLOUD=1` set (R-27 is a proposal; this is the Admin's lean on open item 9). *Checked by the Admin,
  2026-10-12:* `printenv OLLAMA_NO_CLOUD` returns `1`;
- `nvidia-smi` inside the container shows the RTX 4080. *Checked by the Admin, 2026-10-12:* RTX 4080 Laptop,
  12,282 MiB, 0 MiB used idle, 53 C, P3; NVIDIA-SMI tool 615.78.02, kernel-mode driver 617.14, CUDA UMD 13.4;
- the host plugged in. *Stated by the Admin, 2026-10-12.*

The service implements the proposals R-27 (Ollama cloud features off) and the R-16 note (Ollama in a container) for
this benchmark-only container; both remain proposals. The Admin ran these commands from the repository root on
2026-10-12 (output supplied by the Admin, not run by Claude Code; results marked above):

1. `docker compose --profile benchmark up -d ollama-bench`
2. `docker exec ollama-bench ollama --version` (expected: 0.40.0)
3. `docker exec ollama-bench nvidia-smi` (expected: the RTX 4080)
4. `docker exec ollama-bench printenv OLLAMA_NO_CLOUD` (expected: `1`)

The start command needs `POSTGRES_PASSWORD` set (normally from the Admin's `.env`; no value is recorded here),
because Compose resolves variables for the whole file (Compose behaviour as stated; not verified).
`scripts\reset-db.bat` runs `docker compose down -v` and may delete the benchmark models volume (not tested); models
would have to be pulled again.

**Smoke test (not a benchmark result).** Run by the Admin on 2026-10-12 in `ollama-bench`; output supplied by the
Admin, not measured by Claude Code; one run and one sample. Every benchmark cell stays `not run`.

- `ollama pull gemma4:12b`: layers `0cb0cd0a5c49` (175 MB), `bb722270d543` (7.4 GB), `7008a656050b` (465 MB) and
  `e5ca99f91896` (242 B); digest verified; model ID `6114515d63c1`.
- `ollama run gemma4:12b "Reply with one word: ready"`: the reply was "ready", preceded by visible "Thinking..."
  text.
- `ollama ps`: SIZE 1.1 GB, 100% GPU, CONTEXT 4096, runner llamacpp.
- `nvidia-smi` after the run: 8,786 MiB of 12,282 MiB used, process `/llama-server`, 53 C, P4, 37 W of 80 W (one
  sample). The `ollama ps` SIZE and the `nvidia-smi` figure differ; both are recorded as reported.
- The container was stopped afterwards; the models volume holds the model.

Comparison with `docs/UPSTREAMS.md` (`gemma4:12b`, registry manifest pin):

- **Layers match** (12-character prefixes only): `0cb0cd0a5c49` is the projector (175,115,616 bytes in
  UPSTREAMS), `bb722270d543` the model layer (7,381,383,680 bytes), `7008a656050b` the draft and `e5ca99f91896` the
  config. The licence layer `0d542e0c…` recorded in UPSTREAMS is not in the supplied pull output.
- **Model ID not comparable:** UPSTREAMS records layer digests and two conflicting short IDs from the Ollama pages
  (`c7597fc90b86`, `312246b09fab`), not a manifest digest. `6114515d63c1` matches neither short ID; what Ollama
  derives the model ID from is not verified here.

Findings from the smoke test (Admin-supplied output; not measurements):

- **Thinking text.** `gemma4:12b` emitted visible thinking text before its answer. Thinking tokens count toward the
  512-token output cap (open item 4) and toward latency (B5), and may truncate JSON output (B4).
  `docs/UPSTREAMS.md` records no per-request control for thinking; whether Ollama `v0.40.0` offers one for this
  model is **not verified**. Open item 12.
- **VRAM at the default context.** At the default context of 4096, 8,786 MiB of 12,282 MiB were in use after one
  run (one sample), so larger contexts may not fit on the GPU alone. This is measured in B1 and B3, not assumed
  (spec line 103: inspect actual allocation and GPU/CPU offload; spec line 101: never assume co-running at 256K on
  12 GB VRAM).

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
   *Admin's lean (not decided): a new slice 4b builds the harness and the `test`-mode adapter.* Slice 4b wrote them
   (section 7); no live run.
9. **Cloud setting for runs:** whether benchmark runs must use `OLLAMA_NO_CLOUD=1` before R-27 is decided.
   *Admin's lean (not decided): yes, benchmark runs use `OLLAMA_NO_CLOUD=1`.*
10. **Where results go:** this file's *Results* section or a separate results file, and the approval of each results
    pull request.
    *Admin's lean (not decided): a separate results file, with one results pull request per run set.*
11. **Dedicated benchmark container:** built in a new slice, 1b, before any run, to the pre-run checklist in
    section 5. Done: merged as `9e57e8b` (pull request #31); container checks and a smoke test run by the Admin on
    2026-10-12 (section 5).
12. **Thinking output:** how thinking text from `gemma4:12b` is treated in runs: counted toward the 512-token cap,
    capped separately, or disabled. A per-request control is not verified (`docs/UPSTREAMS.md` records none).
    *Admin to decide.*

## 7. Harness (slice 4b)

Written in slice 4b; **no live run.** It has been tested only against a fake server. Every benchmark cell stays
`not run` until the Admin runs it and a results pull request records the aggregates (open item 10).

**What it measures.** B4 (JSON tool-call validity) and B5 (latency), each at `num_ctx` 4096 and 8192: four cells
(`B4-4K`, `B4-8K`, `B5-4K`, `B5-8K`). B1, B2, B3 and B6 to B8 are not covered yet. Per cell: warm-up runs first
(default 1, left out of the aggregates; a different `num_ctx` reloads the model, `docs/UPSTREAMS.md`), then N
repetitions (default 10, open item 4). Every request is `POST /api/chat` with `stream: false`, `options.num_ctx` set
per request and the output cap `options.num_predict` (default 512, open item 4). B4 offers three synthetic tools; a
run is valid when the reply holds exactly one tool call, to the tool the prompt asks for, with arguments that match
the tool's schema (required names, types and enums; a name the schema does not list is invalid). B5 sends synthetic
prompts without tools. The prompts are synthetic and in the repository (`apps/api/qms_bench/prompts.py`).

**Per run it records** (raw, untracked: `bench-results/<UTC time>/runs.jsonl`): cell id, `num_ctx`, the cap, prompt id,
warm-up flag, the wall-clock time of the HTTP exchange, the HTTP status, `done_reason` and whether it is `length`
(truncated), `prompt_eval_count`, `eval_count` and the duration fields as the endpoint returns them, the character counts
of the answer and of the thinking text (never the text), the number of tool calls, B4 validity with a reason code, the
response's key names and the gateway request id. `meta.json` holds the server version (`GET /api/version`), the model
name and digest as `GET /api/tags` reports them, `GET /api/ps` after each cell (`size`, `size_vram`, `context_length`,
runner), the Admin's flags and the counts of the run's egress-log rows by provider, model, egress class, integration
mode, data class and outcome. `aggregate.json` holds the aggregate rows. Nothing is written into `docs/`.

**Printed aggregates**, per cell: runs, errors, p50 and p95 latency (linear interpolation between the closest ranks),
the valid-JSON count and rate (B4; an error counts as invalid), the truncated count and the runs with thinking text.
The aggregate output records the provider, the model and the egress class: a line above the printed table, and
three fields in every row of `aggregate.json`.

**Through the provider contract.** Each model call goes through `ProviderGateway.call` with the test-mode adapter
`OllamaBenchProvider` (`apps/api/qms_bench/ollama_adapter.py`): integration mode `test`, family `ollama`, egress class
`local`. The harness and the adapter are a package of their own, `apps/api/qms_bench/`, outside `qms_os`: the application
package holds no HTTP client (an existing test checks it) and never imports `qms_bench` (a new test). The registry
accepts it because it refuses only `live` adapters (R-25, unchanged; a test checks that it still refuses this adapter as
`live`); no default registry registers it, so the application never calls it. The endpoint must be
`http://127.0.0.1:<port>` or `http://localhost:<port>`: any other host is refused, redirects are not followed and proxy
settings are ignored. The gateway uses a temporary SQLite database, created in the run's output directory and deleted
after the run, also when the run fails; the harness never opens the application's database (a test checks both; Admin,
2026-10-13). Its allow-list holds one entry that the harness writes for the run (the model, the digest the Admin passes,
egress class `local`, ceiling `public`), and every call states the data class `public`. **Benchmark runs therefore bypass
the Admin's audited allow-list** (ADR 0005, R-25): no account admin approves the entry and no audit event is written. The
egress log still records every call, and its counts are kept in `meta.json`. Before any model call the harness refuses to
run unless `GET /api/tags` lists the model with exactly that digest (R-21). The gateway's cloud model-name rule still
applies.

**How the Admin runs a live run**, from the repository root, with the container from slice 1b (section 5).
`scripts\run-benchmark.bat` changes to `apps\api` and forwards its arguments to `python -m qms_bench`:

1. `docker compose --profile benchmark up -d ollama-bench` (needs `POSTGRES_PASSWORD`, section 5).
2. `scripts\run-benchmark.bat --list-models` prints each model's name and digest.
3. `scripts\run-benchmark.bat --model gemma4:12b --model-digest sha256:<64 hex from step 2> --power-mode "<mode>"
   --plugged-in yes --gpu-temp-c <C> --gpu-in-use "<GPU>"` (one line). Optional flags:
   `--endpoint` (default `http://127.0.0.1:11435`), `--repetitions` (10), `--warmup` (1), `--num-predict` (512),
   `--contexts` (`4096,8192`), `--timeout` (600 s per request), `--out` (a new directory).
4. `docker compose --profile benchmark stop ollama-bench`.

Exit codes: 0 done, 2 usage error, 3 refused or failed.

**Not verified:**

- No live run: behaviour against Ollama `v0.40.0` is tested only with a fake server.
- Field names come from the `v0.40.0` source at `0d0720e5` (`api/types.go`, `server/routes.go:2293`,
  `llm/server.go:255-265`), read on 2026-10-13 from the archive recorded in `docs/UPSTREAMS.md`. Of these, only
  `options.num_ctx` is in the UPSTREAMS rows; `options.num_predict` and the response fields are not. Each record keeps
  the response's key names, so a field that is missing or renamed shows up.
- Whether `eval_count` includes thinking tokens. That source has no separate thinking-token count, so thinking is
  recorded as a character count. It has a request field `think` (`api/types.go:112,164`); the harness does not set
  it, and its effect on `gemma4:12b` is not verified. How thinking is treated is open item 12, the Admin's decision.
- The duration fields' unit (Go `time.Duration`, nanoseconds by that source's JSON encoding); stored as returned.
- Whether the `/api/tags` digest is the value behind the model ID that `ollama list` shows.
- The latency is the HTTP exchange measured on the host; the gateway's log writes are outside it.
- `localhost` is resolved by the host; `127.0.0.1` avoids that.

## Results

None. Every cell is `not run`.
