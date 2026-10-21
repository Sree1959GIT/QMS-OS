# QMS OS — Session handoff

**Purpose:** Commit this concise checkpoint as `docs/HANDOFF.md`. Claude Code must check each claim against the live Git checkout at the start of a session. Keep current state here; move substantial history to Git commits, PRs and dated decision records. Do not put secrets or private organizational data here.

## Snapshot to verify

- Repository: this repository (`QMS-OS`); confirm the remote with `git remote -v`.
- Specification: `docs/SPECIFICATION.md`, v3.0 dated 29 September 2026. Verify title and version locally.
- Baseline recorded here: `main` at `8b0c0ef03909180593308ada7128defc78c94390` (2026-10-21; squash merge of pull
  request #42, MVP-1 pull request 6, slice 10b; `git pull --ff-only`, 2026-10-21). Its tree is identical to
  `ac712a0`, the last commit of the deleted branch `feat/mvp1-admin-ui-signin` (`git diff` empty); that branch's
  commits (`f6d606f`, `f251734`, `6186328`, `138f23a`, `ac712a0`) exist only in pull request #42's history. The
  previous baseline, `efaeec1` (pull request #41, slice 10a), likewise replaced the commits of `feat/mvp1-admin-ui`
  (`2b05481`, `d79a00e`, `77fc4fe`, `bc9c83a`, `ec414e1`); its squash title kept "(draft)".
  Work in progress: branch `feat/mvp1-admin-ui-org` from `8b0c0ef`, slices 10c and 10d and the draft ADR 0008 (no
  pull request yet).
  Re-verify branch, HEAD and working tree with Git at session start; this file may be stale.
- Stage: MVP-0 declared met (R-29), by the Admin on 2026-10-13, on the narrow reading of the exit (R-28). Of the
  eight items in the ROADMAP's MVP-0 table, five are done (Git scaffold, CI and protected `main`; synthetic fixtures;
  fixture startup as a server process; documentation reconciled; model-provider contract), the benchmark plan and
  the upstream matrix are done for the exit (9 flagged claims, kept as labelled by the Admin on 2026-10-13) and
  container configuration beyond PostgreSQL is descoped for the exit. No slices remain for the exit; the evidence
  and the accepted gaps are in *MVP-0 exit evidence* in `docs/ROADMAP.md`. MVP-1: planned as bundled pull requests
  (R-37; *MVP-1 plan* in `docs/ROADMAP.md`); pull request 1 (slice 1) merged as `ded0fe8`; pull request 2 (the
  `/api/v1` move, slices 2 and 3, the first three skills) merged as `6aa5246`; pull request 3 (slices 4 and 5)
  merged as `caabb11`; pull request 4 (slices 6 to 9, R-55) merged as `6c74d60` (pull request #40); pull request 5
  (slice 10a) merged as `efaeec1` (pull request #41); pull request 6 (slice 10b) merged as `8b0c0ef` (pull request
  #42); slices 10c and 10d in progress on `feat/mvp1-admin-ui-org`.
- Mode: synthetic only. No live connectors, staff accounts or model credentials are configured in this repository,
  and none has been verified; do not claim they are configured.

## Verified state

Each item says how it was verified.

- **Merge of pull request #42 (2026-10-21):** merged at 07:34 UTC as `8b0c0ef` (GitHub public API). Pull request run
  39562347176 (#88) on `ac712a0` and `main` run 39562889995 (#89) on `8b0c0ef`: all eight jobs succeeded in both
  (`test`, `test-py311`, `lint`, `types`, `postgres`, `secret-scan`, `frontend`, `e2e`; every step of `e2e`
  succeeded, including "Browser tests"), from the GitHub public API, 2026-10-21. The job logs were not read.
- **Merge of pull request #41 (2026-10-21):** merged at 04:06 UTC as `efaeec1` (GitHub public API: state closed,
  merged, merge commit `efaeec19dfbee2d5f2007fdd133a6f90294f168e`). `main` run 39542227140 (shown as #87, push at
  `efaeec1`): all seven jobs succeeded, `postgres` (2m 36s), `test` (1m 41s), `test-py311` (1m 11s), `types` (35s),
  `frontend` (20s), `lint` (14s) and `secret-scan` (9s) (GitHub public API, read 2026-10-21). Pull request run
  39539241722 (#86) on `ec414e1`: all seven jobs succeeded (same source). `frontend` is green on `main` and not
  yet required (R-13, R-71: the Admin decides).
- **Pull request #41 (2026-10-21):** `origin/feat/mvp1-admin-ui` was at `d79a00e` after `git fetch` on 2026-10-21
  (nothing pushed by anyone since 2026-10-15). Run 38772304414 on `d79a00e` (GitHub public API, read 2026-10-21):
  `test`, `test-py311`, `lint`, `types`, `postgres` and `secret-scan` succeeded; `frontend` failed at "Licence
  check", which refused `lightningcss-linux-x64-musl@1.33.0` (MPL-2.0; the exception named three packages). The
  steps after it (dependency audit) did not run in CI. Pull request #40's and `main`'s runs on `6c74d60` were not
  recorded. Locally on 2026-10-21 (Windows 11, Node 24.13.1, pnpm 10.34.6), at `bc9c83a`: lint, type check, 25
  frontend tests, build, bundle check, licence check (3 production packages and 218 in all, 0 refused) and
  `pnpm audit --audit-level high` (no known vulnerabilities) passed; `scripts\run-tests.bat` 560 passed, 2 skipped;
  `scripts\run-lint.bat` ruff, mypy and the image digest check passed; `scripts\run-pg-tests.bat full` 591 passed;
  `claims-register` check clean; gitleaks 8.30.1 on the staged changes found nothing.
- **What CI has not proved yet:** the `frontend` job (with the licence check and the dependency audit) passed on
  pull request #41 (run #86) and on `main` (run #87); not proved: anything in a browser (the browser end-to-end job,
  R-71, does not exist yet), and that the Linux runner now skips the musl builds (the job logs need a GitHub
  sign-in and were not read).
- **Licence-check limits (R-73):** pnpm reads licences from the installed packages in `node_modules`, and
  `pnpm-lock.yaml` (lockfile 9.0) records none, so each host checks only the platform builds it installs (Windows
  x64: the msvc builds; the Linux runner: the gnu builds, and before `bc9c83a` also the musl builds). The 14 rolldown
  platform builds and `fsevents` not installed on a host are not checked there. Licences are package metadata
  (secondary), not the licence text; the lightningcss exception is a licence interpretation, not a legal opinion
  (C-147 flagged). Since `bc9c83a` the lockfile records `libc` for the ten Linux rolldown and lightningcss builds,
  so a glibc host should skip the musl builds (to be confirmed by the next CI run).

- **Git:** on 2026-10-15 `git pull --ff-only` brought local `main` to `caabb11a11b947d424b505e7d95d7874ebdc7d4e`
  (= `origin/main`), working tree clean; its tree is identical to the tip of `feat/mvp1-agents-store` (`c6c93d4`).
  Pull request #39 (MVP-1 pull request 3) was merged as `caabb11`. Pull request run (run id not recorded): job
  `postgres` "468 passed, 1 skipped, 1 warning" (from the Admin's pasted log); the skip is the Windows-only
  `test_rename_publish_never_replaces_on_windows`, skipped on the Linux runner. `main` run 38681512256 (shown as #82,
  push to `main` at `caabb11`): Success, 2m 3s; jobs `test` (1m 13s), `test-py311` (57s), `lint` (21s), `types`
  (34s), `postgres` (1m 59s) and `secret-scan` (6s). Both from the Admin's pasted log and screenshot, not read from
  GitHub by Claude Code. Branch `feat/mvp1-workflow` was created from `caabb11` (local only).
  Earlier: on 2026-10-14 `git pull --ff-only` brought local `main` to `6aa5246d881f1a155d5a006da2608e47910683f6`
  (= `origin/main`), working tree clean, no commits after it; its tree is identical to the tip of
  `feat/mvp1-org-grants` (`284650c`). Pull request #38 (MVP-1 pull request 2) was merged as `6aa5246`. Pull request
  run (run id not recorded): job `postgres` "395 passed", no skips (from the Admin's pasted log), so the org-admin,
  access and super admin tests ran in CI. `main` run 38598563188 (shown as #80, push to `main` at `6aa5246`):
  Success, 1m 51s; jobs `test` (1m 42s), `test-py311` (58s), `lint` (26s), `types` (38s), `postgres` (1m 48s) and
  `secret-scan` (5s). Both from the Admin's screenshot or pasted log, not read from GitHub by Claude Code. Branch
  `feat/mvp1-agents-store` was created from `6aa5246` (local only).
  Earlier: on 2026-10-14 `git pull --ff-only` brought local `main` to `ded0fe88be199ac391a8d9862bdf973be96ec9f7`
  (= `origin/main`), working tree clean; its tree is identical to the tip of `feat/mvp1-foundation` (`5fe7631`; `git
  diff` empty). Pull request #37 (`feat/mvp1-foundation`, MVP-1 pull request 1) was merged as `ded0fe8`. Pull request
  run 38576897109 (shown as #77): job `postgres` "348 passed", no skips (from the Admin's pasted log), so
  `tests/test_startup_smoke_pg.py` ran in CI. `main` run 38578074918 (shown as #78, push to `main` at `ded0fe8`):
  Success, 1m 44s; jobs `test` (57s), `test-py311` (44s), `lint` (15s), `types` (34s), `postgres` (1m 40s) and
  `secret-scan` (6s). Both from the Admin's screenshots or pasted logs, not read from GitHub by Claude Code. Branch
  `feat/mvp1-org-grants` was created from `ded0fe8` (local only).
  Earlier: on 2026-10-14 local `main` was at `59d4d5ea5c045a8fc2eb558a21d3dc5535d6a5f6` (= `origin/main` after
  `git fetch`), working tree clean; its tree is identical to the tip of `docs/mvp0-declaration` (`5415d48`; `git diff`
  empty). Pull request #36 (`docs/mvp0-declaration`, head `5415d48`, R-29) was merged as `59d4d5e`. Pull request run
  38436176286 (shown as #75, on pull request #36): Success, 1m 39s. `main` run 38437483176 (shown as #76, push to
  `main` at `59d4d5e`): Success, 1m 47s; jobs `test` (1m 8s), `test-py311` (44s), `lint` (13s), `types` (27s),
  `postgres` (1m 43s) and `secret-scan` (15s). Both from the Admin's screenshots of the run pages, not read from
  GitHub by Claude Code. Branch `feat/mvp1-foundation` was created from `59d4d5e` (local only).
  Earlier: on 2026-10-13 `git pull --ff-only` brought local `main` to `e1b5276d1c114b50fba51e05f937d535a4707d01`
  (= `origin/main`), working tree clean; its tree is identical to the tip of `docs/mvp0-review` (`1151373`; `git
  diff` empty). Pull request #35 (`docs/mvp0-review`, head `1151373`, the slice 6 review and evidence table) was
  merged as `e1b5276` (committer time 2026-10-13 16:55 UTC, from Git). `main` run 38434451817 on `e1b5276`:
  conclusion Success, total 1m 37s; jobs `test` (50s), `test-py311` (55s), `lint` (13s), `types` (35s), `postgres`
  (1m 33s) and `secret-scan` (5s), all passed — from the Admin's screenshot of the run page, 2026-10-13, not read
  from GitHub by Claude Code. Branch `docs/mvp0-declaration` was created from `e1b5276` (local only).
  Earlier: on 2026-10-13 `git pull --ff-only` brought local `main` to `fa5c5f239f2d390e672d819e125996117b2f5c28`
  (= `origin/main`), working tree clean; its tree is identical to the tip of `docs/mvp0-closure` (`7eed4da`; `git
  diff` empty). Pull request #34 (`docs/mvp0-closure`, head `7eed4da`, R-28 and the claims register) was merged as
  `fa5c5f2` (committer time 2026-10-13 14:19 UTC, from Git). `main` run 38412392880 (shown as #72) on `fa5c5f2`:
  conclusion Success, total 1m 17s; jobs `test` (41s), `test-py311` (48s), `lint` (15s), `types` (32s), `postgres`
  (1m 13s) and `secret-scan` (7s), all passed — from the Admin's screenshots of the run page, 2026-10-13, not read
  from GitHub by Claude Code. The pull request run was not recorded. Branch `docs/mvp0-review` was created from
  `fa5c5f2` (local only).
  Earlier: on 2026-10-13, after a restart of the laptop, `git pull --ff-only` brought local `main` from `2a385a9`
  to `d7f1127ef09c0075dbe5cfcc24ae3febeba840b5` (= `origin/main`), working tree clean; the merged tree is identical
  to the tip of `feat/benchmark-harness` (`git diff` empty). Pull request #33 (`feat/benchmark-harness`, slice 4b)
  was merged as `d7f1127` on 2026-10-13 at 04:05 UTC: pull request run 38344515431 (checks about 04:02 to 04:03 UTC
  on 2026-10-13, read from GitHub via the Perplexity GitHub connector) and `main` run 38344797527 (run page checked
  by the Admin, screenshot); not read in this session. Branch `docs/mvp0-closure` was created from `d7f1127`
  (local only).
  Earlier: on 2026-10-13 `git pull --ff-only` brought local `main` to `2a385a94…` (= `origin/main`), working tree
  clean. Pull request #32 (`docs/benchmark-checks`, head `b74530b3…`, the container checks and smoke test) was
  merged as `2a385a9` on 2026-10-12 at 17:22 UTC: pull request run 38283632219 (checks about 17:21 to 17:22 UTC on
  2026-10-12, read from GitHub via the Perplexity GitHub connector) and `main` run 38283810827 (run page checked by
  the Admin, screenshot); not read in this session. Branch `feat/benchmark-harness` was created from `2a385a9`
  (local only).
  Earlier: on 2026-10-12 `git pull --ff-only` brought local `main` to `9e57e8be…` (= `origin/main`), working tree
  clean. Pull request #31 (`feat/benchmark-container`, head `c6cac876…`, slice 1b) was merged as `9e57e8b` on
  2026-10-12 at 16:09 UTC: pull request run 38267172919 (checks about 15:01 UTC on 2026-10-12, read from GitHub via
  the Perplexity GitHub connector) and `main` run 38275404315 (run page checked by the Admin, screenshot); not read
  in this session. Branch `docs/benchmark-checks` was created from `9e57e8b` (merged as `2a385a9`, pull request
  #32).
  Earlier: on 2026-10-12 `git pull --ff-only` brought local `main` to `5a3e3e31…` (= `origin/main`), working tree
  clean. Pull request #30 (`docs/benchmark-host`, head `34da1bff…`, plan update and slice 1b added) was merged as
  `5a3e3e3` on 2026-10-12 at 14:26 UTC: pull request run 38261346033 (checks about 14:13 to 14:15 UTC on
  2026-10-12, read from GitHub via the Perplexity GitHub connector) and `main` run 38262886157 (run page checked by
  the Admin, screenshot); not read in this session. Branch `feat/benchmark-container` was created from `5a3e3e3`
  (merged as `9e57e8b`, pull request #31).
  Earlier: on 2026-10-11 `git pull --ff-only` brought local `main` to `b2c74ae1…` (= `origin/main`), working tree
  clean. Pull request #29 (`docs/benchmark-plan`, head `29474235…`, ROADMAP slice 4, plan only) was merged as
  `b2c74ae`: pull request run 38146662152 (read from GitHub via the Perplexity GitHub connector, 2026-10-11) and
  `main` run 38147116486 (run page checked by the Admin, screenshot, 2026-10-11); not read in this session. Branch
  `docs/benchmark-host` was created from `b2c74ae` (merged as `5a3e3e3`, pull request #30).
  Earlier: on 2026-10-11 `git pull --ff-only` brought local `main` to `fed244fa…` (= `origin/main`), working tree
  clean. Pull request #28 (`docs/handoff-after-pr27`, head `42f06ae8…`, `docs/HANDOFF.md` only) was merged as
  `fed244f`: pull request run 38118188007 (six jobs green, read from GitHub via the Perplexity GitHub connector,
  2026-10-11) and `main` run 38118371953 (six jobs green, run page checked by the Admin, screenshot, 2026-10-11);
  not read in this session. Branch `docs/benchmark-plan` was created from `fed244f` (merged as `b2c74ae`, pull
  request #29).
  Earlier: on 2026-10-11 `git pull --ff-only` brought local `main` to `a49baee8…` (= `origin/main`), working tree
  clean. Pull request #27 (head `feabb403…`; R-26 decided, R-27 and the R-16 note proposals) was merged as
  `a49baee` at 2026-10-11 05:41 UTC: pull request run 38115212746 (six jobs green, read from GitHub via the
  Perplexity GitHub connector, 2026-10-11) and `main` run 38115607032 (push on `main`; six jobs green, run page
  checked by the Admin (screenshot, 2026-10-11); commit a49baee8e46bb8ddc70e46968060741c5340c8f5 confirmed via
  GitHub); not read in this session. Branch `docs/handoff-after-pr27` was created from `a49baee` (merged as
  `fed244f`, pull request #28).
  Earlier: on 2026-10-11 `git fetch` showed `origin/main` and local `main` at
  `686b12be…`, working tree clean. Pull request #26 (`docs/upstream-ollama-items`, ROADMAP slice 2, the three
  Ollama items) was merged as `686b12b`: pull request run 38035882422 (six jobs green, read from GitHub via the
  Perplexity GitHub connector, 2026-10-11) and `main` run 38110041414 (as reported by the Admin, not verified).
  Branch `docs/model-agnostic-providers` was created from `686b12b` (merged as `a49baee`, pull request #27).
  Earlier: on 2026-10-10 `git fetch`
  showed `origin/main` and local `main` at `e4ebfd37…`, working tree clean. Pull
  request #25 (`feat/pin-compose-postgres`, ROADMAP slice 1, PostgreSQL pin) was merged as `e4ebfd3`: pull request
  run 38028183377 and `main` run 38033037362, as reported by the Admin, not read from GitHub. Branch
  `docs/upstream-ollama-items` was created from `e4ebfd3` (merged as `686b12b`, pull request #26). Earlier: on 2026-10-10 local `main` was at
  `a7b90da…` with a clean working tree (`git rev-parse HEAD`, `git status`; not fetched). Pull request #24 (`feat/ci-image-digest-check`, ROADMAP slice 3a) was merged as `a7b90da`:
  pull request run 38024123786 and `main` run 38024289981, as reported by the Admin, not read from GitHub. Branch
  `feat/pin-compose-postgres` was created from `a7b90da` (merged as `e4ebfd3`, pull request #25). Earlier: on 2026-10-09 `main` was at
  `53f6f23…` with a clean working tree (`git fetch`, then `git status -sb`:
  `main...origin/main`). Pull request #23 (`feat/provider-contract`, ROADMAP slice 3) was merged as `53f6f23`; `main`
  CI run 37939344103 green, as reported by the Admin, not read from GitHub. Branch `feat/ci-image-digest-check` was
  created from `53f6f23` (merged as `a7b90da`, pull request #24). Earlier: on 2026-10-09 `main` was at `dae34ae…`. Pull request #22 (`docs/provider-decisions`) was merged as `dae34ae`: pull request run
  37883681486, six jobs green, and `main` run 37910850440 for `dae34ae`, six jobs green — both as reported by the
  Admin, not read from GitHub. Earlier: on
  2026-10-09 `main` was at `fe6eb05…`. Pull request #21 (`docs/upstream-matrix`) was merged as `fe6eb05`; the squash
  title lost the "A" of "Add" ("dd the upstream licence…"), and `main` is not rewritten for it. Pull request #21's six
  CI jobs passed, as reported by the Admin (run IDs not captured); `main` run 37876971887 for `fe6eb05`, six jobs
  green, as reported by the Admin, not read from GitHub. Earlier: on 2026-10-07 `main` was at `5b3e181…`. Pull request #20 (`ci/lint-types`) was merged as `5b3e181` and
  pull request #19 (`docs/refresh-status`) as `31966a2`; CI runs 37648488409 (#20) and 37617433395 (#19) as reported
  by the Admin, not read from GitHub in this session. Earlier: on 2026-10-07 `main` was at `eb3c583…`. Pull request #18 (`feat/link-code`, head `69a60d3`; the one-time link code) was
  merged as `eb3c583`; jobs `test`, `postgres` and `secret-scan` all succeeded on the pull request (run 37614209373:
  jobs 112768522314, 112768521989, 112768522176) and on `main` (run 37614974061: jobs 112771010112, 112771010504,
  112771010529); the branch has been deleted (absent locally and on GitHub). Pull request #17 (`docs/scan-rule`,
  head `dd6034c`; the secret-scan and `.env` boundary rule in `CLAUDE.md`) was merged as `81d0cb8`, and pull request #16 (`docs/handoff-ci-merged`, head
  `a11023a`; handoff after the CI merge) as `816f574`; jobs `test`, `postgres` and `secret-scan` all succeeded on
  pull request #16 (run 37608866464) and on `main` at `816f574` (run 37609515878), and on pull request #17 (run
  37611716382) and on `main` at `81d0cb8` (run 37611951140); both branches have been deleted (absent locally and on
  GitHub). Pull request #15 (`ci/secret-scan-and-pg`, head `e198781`) was merged to `main` as
  `0f66d47`; jobs `test`, `postgres` and `secret-scan` all succeeded on the pull request (run 37565023452) and on
  `main` (run 37566508358); the branch has been deleted (absent locally and on GitHub). Pull request #14
  (`feat/account-admin-cli`, head `58d81bd`) was merged to `main` as `d65b0c9`; CI job `test` succeeded on the pull request (run 37493133191) and on `main` (run 37493474630); the
  branch has been deleted (absent locally and on GitHub). Pull request #13 (`chore/gitattributes-bat`, head
  `1ef0c7e`) was merged to `main` as `9b79841`; CI job `test` succeeded on the pull request (run 37478760925) and on
  `main` (run 37478911185); the branch has been deleted (absent locally and on GitHub). Pull request #12
  (`feat/env-temp-root`, head `870a042`) was merged to `main` as `58bfd13`; CI job `test` succeeded on the pull
  request (run 37465702805) and on `main` (run 37465852131); the
  branch `feat/env-temp-root` has been deleted (absent locally and on GitHub). Pull request #11
  (`docs/handoff-r3-merged`, handoff only) was merged to `main` as
  `82d5897`; CI job `test` succeeded on `main` (run 37462907004). Pull request #10 (`feat/auth-r3`, head `74a4460`)
  was merged (squash) to `main` as `23329f3`; its CI job `test` succeeded on the pull request (run 37449326911, job
  112221750807) and on the push to `main` (run 37449476896, job 112222249819). Earlier: pull request #9 merged as
  `997e55b`, CI passed (runs 37432905647, 37433046381). All read from the public GitHub API on 2026-10-06.
- **First Linux install of the R-3 dependencies: verified (by step results).** Both runs above, on `ubuntu-24.04`
  with Python 3.12.10, passed step "Install" (`pip install -e ".[dev]" -c constraints-ci.txt`, which must install
  argon2-cffi 25.1.0, argon2-cffi-bindings 26.1.0, cffi 2.1.1 and cryptography 50.0.2 as pinned, or fail) and step
  "Test", whose test modules import argon2 and cryptography at collection. The install log itself was not read:
  the logs API returns `403 Must have admin rights` without a token.
- **Windows Smart App Control:** on 2026-10-06 it blocked SQLAlchemy's unsigned `_row_cy` extension (Code
  Integrity events 3033/3077 at 12:08 local), so `scripts\run-tests.bat` could not load the tests. Later the same day
  its state read `0` (off) and all extensions loaded; the SQLAlchemy files were unchanged. Unsigned compiled
  dependencies can be blocked again if it is re-enabled.
- **Python versions:** the project `.venv` runs Python **3.12.7**; CI runs 3.12.10, plus 3.11.17 in job
  `test-py311` (SQLite suite only; verified per the Admin on 2026-10-07). Earlier local results recorded
  as 3.12.10 predate the project venv. The two have not been reconciled.
- **Tests:** `python -m pytest -q -p no:cacheprovider`, run from `apps/api/`:
  - `main`, local Windows (`scripts\run-tests.bat`, Python 3.12.7) on 2026-10-05: `105 passed, 1 warning` (the
    warning is the Starlette `httpx` test-client deprecation notice);
  - `main` at `8863669…`, local Windows (`scripts\run-tests.bat`, Python 3.12.7) on 2026-10-06:
    `112 passed, 1 skipped, 1 warning`; PostgreSQL results: see *PostgreSQL (R-14)* below;
  - `main` at `997e55b…` on 2026-10-06: `112 passed, 1 skipped, 1 warning`, exit code 0. `scripts\run-tests.bat` now
    returns pytest's exit code (pull request #9); before that it returned 0 even when pytest failed;
  - `main` at `23329f3…` (R-3 merged), local Windows on 2026-10-06: `155 passed, 1 skipped, 1 warning`, exit 0;
    branch results before the merge: see *Authentication (R-3)* below;
  - branch `feat/ci-image-digest-check`, local Windows on 2026-10-09: `scripts\run-tests.bat` `261 passed, 1
    skipped, 1 warning`; `scripts\run-pg-tests.bat` `22 passed, 261 deselected`; `scripts\run-pg-tests.bat full`
    `283 passed`; `alembic check` "No new upgrade operations detected."; `alembic heads` `44bca21ba248 (head)`;
    `scripts\run-lint.bat`: ruff "All checks passed!", mypy "Success: no issues found in 46 source files", "image
    digest check: 2 scanned in 2 files, 1 baselined, 0 problems";
  - branch `feat/provider-contract` (merged as `53f6f23`), local Windows on 2026-10-09: `scripts\run-tests.bat` `229 passed, 1 skipped,
    1 warning`; `scripts\run-pg-tests.bat` `22 passed, 229 deselected`; `scripts\run-pg-tests.bat full` `251
    passed`; `alembic check` "No new upgrade operations detected."; `alembic heads` `44bca21ba248 (head)` (single
    head); ruff "All checks passed!"; mypy "Success: no issues found in 46 source files". Nine deliberate breaks
    (M1–M9) each made their tests fail (see *Last sessions*);
  - branch `feat/mvp1-foundation` (MVP-1 slice 1), local Windows (Python 3.12.7) on 2026-10-14:
    `scripts\run-tests.bat` `324 passed, 2 skipped, 1 warning` (exit 0; the skips are the two PostgreSQL modules);
    `scripts\run-pg-tests.bat` `24 passed, 324 deselected` (exit 0); `scripts\run-pg-tests.bat full` `348 passed, 1
    warning` (exit 0);
  - `main` at `e1b5276…` (slice 6 merged), local Windows (Python 3.12.7) on 2026-10-13: `scripts\run-tests.bat`
    `324 passed, 1 skipped, 1 warning` (exit 0); `scripts\run-pg-tests.bat full` `346 passed, 1 warning` (exit 0);
  - `main` at `fa5c5f2…` (R-28 merged), local Windows (Python 3.12.7) on 2026-10-13: `scripts\run-tests.bat` `324
    passed, 1 skipped, 1 warning` (exit 0; the skip is the PostgreSQL module); `scripts\run-pg-tests.bat full` `346
    passed, 1 warning` (exit 0);
  - `main` at `eb3c583…` (link code merged), local Windows on 2026-10-07: `scripts\run-tests.bat` `179 passed, 1
    skipped, 1 warning` (exit 0); `scripts\run-pg-tests.bat full` `200 passed, 1 warning` (exit 0);
  - GitHub Actions, Ubuntu 24.04, Python 3.12.10: job `test` succeeded on pull request #1 (run 36837238711; its
    job log reports `104 passed, 1 warning`) and on the push of `30a0c198…` to `main` (run 36842625286).
  - Latest runs, same environment: job `test` succeeded on pull request #5 (run 37135721617) and on the push of `9a1c344…` to `main` (run 37135996806). The per-test count for these runs was not read from the logs.
  - History: before the Checkpoint A repair the suite stood at `4 failed, 32 passed`.
- **CI:** `.github/workflows/ci.yml` runs on pull requests to `main`, pushes to `main` and manual runs, with
  `permissions: contents: read`, `persist-credentials: false`, actions pinned to full commit SHAs, and dependency
  versions held by `apps/api/constraints-ci.txt`. No secrets are used. Six jobs since pull request #20 (`test-py311`, `lint`, `types` added); the first three since pull request #15:
  `test` (SQLite), `postgres` (the whole suite on a pinned PostgreSQL 17.11 service container, including the
  migration-drift and concurrency tests) and `secret-scan` (gitleaks 8.30.1, SHA-256-verified). **Verified in CI**
  (public GitHub API, 2026-10-07): all three succeeded on pull request #15 (run 37565023452: jobs 112610644153,
  112610644435, 112610644447) and on `main` at `0f66d47` (run 37566508358: jobs 112615340743, 112615340735,
  112615340462). Scan scope, from step results only: on the pull request "Scan the pull request's commits" ran and
  "Scan the whole history" was skipped; on `main` the whole-history step ran. The job logs are not readable without
  a token (`403`), so the scanned commit count and the `postgres` test count were not read (locally the same suite
  gives `185 passed`). Required status checks on `main` (ruleset 24295033): since 2026-10-07 all six jobs, with
  branches required to be up to date (R-13; set by the Admin, as reported by the Admin, not re-read from GitHub).
- **Layout:** application code lives in `apps/api/` (R-1; pull request #5). Verified by: `105 passed, 1 warning` run locally from `apps/api/`, and job `test` passing on pull request #5 and on the push to `main`.
- **Local runtime:** PostgreSQL 17 runs through `compose.yaml` (R-2) and the Python venv and caches live inside the project folder. Verified on a local Windows machine on 2026-10-05 by: `scripts\start-db.bat` reaching a healthy container, `select version()` returning PostgreSQL 17.11, `scripts\backup-db.bat` writing a non-empty dump, and `scripts\run-tests.bat` giving `105 passed, 1 warning`. On 2026-10-10 (branch `feat/pin-compose-postgres`, merged as `e4ebfd3`) the image is pinned to the CI reference, `postgres:17.11@sha256:d74eeac9…` (no `POSTGRES_TAG`): `scripts\backup-db.bat` wrote an 878-byte dump first; `docker compose config --images` printed the pinned reference; `scripts\start-db.bat` recreated the container on that image (exit 0), health `healthy`, and `select version()` returned `PostgreSQL 17.11 (Debian 17.11-1.pgdg13+2) on x86_64-pc-linux-gnu`. The named volume was kept; `scripts\run-pg-tests.bat` afterwards gave `22 passed, 261 deselected`.
- **Protection of `main`** (GitHub public API): an active ruleset on the default branch blocks deletion and
  force-pushes, requires pull requests and linear history, and (since 2026-10-07, per the Admin) the six status checks with the
  up-to-date rule. Bypass settings
  are not visible through the public API.
- **Implemented on `main` (synthetic/test data only):** `apps/api/` FastAPI + SQLAlchemy prototype — audit
  programme planning and auditor assignment, finding/corrective-action lifecycle, FMEA risk register, drafts-only
  notifications, append-only audit events, isolated knowledge module; 409 `held` contract for unresolved
  audit-validity conditions with a durable `transition.held` event. Runtime modes: `operational` (default) loads
  the organisation policy from a git-ignored local file and holds policy-dependent work until Top Management
  approval (R-9); `demo`/`test` use labelled synthetic values only. Risk assessments follow R-10 (functional head
  or assigned project manager → MA co-approval → Top Management sign-off); risk closure is held pending D-15;
  organisational project-manager assignment pending D-16. No record-retention parameter or deletion job (D-14;
  guarded by `tests/test_no_retention.py`). Fixtures are visibly fictional (guarded by
  `tests/test_fixture_hygiene.py`).
- **Timestamps:** every stored timestamp is timezone-aware UTC (`qms_os/timeutil.py` `UTCDateTime`: naive values
  rejected, reads always UTC) and the API serialises them with an explicit `+00:00`; guarded by
  `tests/test_timestamps.py`.
- **Server startup:** `tests/test_startup_smoke.py` starts the app as a separate process in `demo` mode against a
  seeded temporary SQLite database and checks the health route (`/api/v1/health` since R-35); it passed locally on
  Windows and in CI on Linux.
- **PostgreSQL (R-14; on `main` via pull request #8; run locally and, since pull request #15, in CI job `postgres`):**
  psycopg 3.3.6 and Alembic 1.20.0 (optional extra `postgres`); baseline revision `7f29c1686517` autogenerated against the empty
  `qmsos_test` database (PostgreSQL 17.11 container) and reviewed by hand (the circular
  `departments.head_user_id` key is added after `users`). Commands actually run on 2026-10-05, Windows, Python
  3.12.7, and their exact results:
  - `scripts\run-pg-tests.bat` (marker `postgres`): `12 passed, 112 deselected, 1 warning`;
  - `scripts\run-pg-tests.bat full` (whole suite on PostgreSQL, opt-in): `124 passed, 1 warning in 45.88s`;
  - `scripts\run-pg-tests.bat alembic check`: `No new upgrade operations detected.`; `alembic current`:
    `7f29c1686517 (head)`;
  - `scripts\run-tests.bat` (in-memory SQLite, as CI): `112 passed, 1 skipped, 1 warning` (105 existing + 4 URL
    tests + 3 static migration tests; the PostgreSQL module is skipped);
  - the same suite with `alembic` and `psycopg` made unimportable (a CI simulation): `112 passed, 1 skipped`.
  No string-length or row-order failures appeared. The test-database URL is read from the git-ignored
  `.private/pg-test-url.txt` inside `scripts\run-pg-tests.bat` only and was not displayed.
- **Authentication (R-3; on `main` as `23329f3` via pull request #10, squash; CI job `test` passed on Linux):**
  local accounts with
  Argon2id passwords and TOTP, server-side sessions with CSRF, lockout, recovery codes, CLI first-Admin bootstrap,
  dual-control credential resets, `account_admin` platform role, access level on every route, `401` with a
  non-leaking reason, `actor_kind`/`channel` on audit events; `X-User-Id` removed, `/api/users` needs sign-in. See
  `docs/adr/0003-auth-dev-identity.md`. Migration `0b13751a07cc` (additive). Commands run on 2026-10-06, Windows,
  Python 3.12.7:
  - `scripts\run-tests.bat`: `155 passed, 1 skipped, 1 warning`, exit 0 (112 earlier + 38 `test_auth.py` + 4
    `test_auth_routes.py` + 1 additive-migration check);
  - `scripts\run-pg-tests.bat`: `17 passed, 155 deselected, 1 warning`, including four concurrency tests (same TOTP
    code twice in parallel: exactly one success; N parallel wrong passwords: counted exactly, locked at 5; two
    concurrent approvals of one reset: exactly one; reset approval racing the person's sign-in: no live session and a
    fully cleared credential); `scripts\run-pg-tests.bat full`: `172 passed, 1 warning`, exit 0; `alembic check`:
    `No new upgrade operations detected.`; `alembic current`: `0b13751a07cc (head)`.
  - Review fixes (2026-10-06): 422 responses no longer echo submitted values; credential row locked with
    `SELECT … FOR UPDATE` (with the person and account-action rows, in a fixed order) for every check or change of
    account state, plus conditional UPDATEs; the recovery-code session ends after TOTP re-enrolment;
    `generate-key` refuses paths inside a Git work tree and `.gitignore` excludes `*.key`/`*.pem`. The concurrency
    tests were shown to fail against the pre-fix code (scratch mutation run). The one-time link limitation is
    addressed by the link-code slice, merged as `eb3c583` (pull request #18; ADR 0003, *One-time links need two
    parts*).

## Not verified

- CI job logs (not readable without a token): the `postgres` test count and the number of commits scanned are known
  only from the Admin's pasted logs (MVP-1 pull request 2: 395 passed, no skips, so the org-admin, access and super
  admin tests ran in CI; run id not recorded). The
  API server *process* has been run only against the migrated PostgreSQL test database (since MVP-1 slice 1,
  `tests/test_startup_smoke_pg.py`; locally, and in CI job `postgres` on pull request run 38576897109, 348 passed
  with no skips, from the Admin's pasted log), not against any other PostgreSQL database; `qms_os.seed` supports
  SQLite only. Database-level
  append-only enforcement (trigger or revoked privileges on `audit_events`) does not exist; append-only is enforced
  by application code and `tests/test_no_retention.py`. TLS to a non-local database is not configured.
- Agents (MVP-1 slice 4; R-48, R-49): no agent can authenticate or call the API in MVP-1; `agent_access` is used by
  the preview and the super admin review, and is the path enforcement will use once agent principals exist. No
  runtime, tool, Telegram, mailbox or credential exists for an agent.
- Interim evidence store (MVP-1 slice 5; R-50 to R-54): **open item:** true append-only enforcement. The triggers on
  `evidence_objects` stop application-level UPDATE and DELETE but not TRUNCATE or DROP by a database owner (R-52).
  Denied evidence reads are not audited per request (R-53; to revisit before any real evidence). The store cannot
  tell real content from synthetic (R-54). Evidence grants have no org admin route (fixtures and the database
  only). The Windows publish path (`os.rename`) is tested locally only (no Windows CI job); the Linux path
  (`os.link`) runs locally and in CI. On a workstation whose pytest temporary folders are inside the repository,
  the evidence tests disable the "outside a Git work tree" check for their store folder (one test checks that rule
  with a folder inside a work tree; CI runs it unpatched). No backup of the store folder is set up.
- Migration guard (R-52; Admin decision 2026-10-15): the additive-only guard accepts `op.execute` when the literal
  starts with `CREATE FUNCTION` or `CREATE TRIGGER`; it checks only how the literal starts, so a function body is not
  inspected. Since MVP-1 pull request 4 the name must also be on the guard's allowlist (R-63); function bodies are
  still not inspected.
- Skills (MVP-1 pull request 3 skill run): the Skill tool loaded `knowledge-integrity` although pull request 2's
  check refused skills marked `disable-model-invocation`; the cause is unknown, so "only a human invokes the skills"
  is not established. Write and Edit stayed denied after the skill run for longer than the frontmatter schema says,
  while Bash could still write files, so `disallowed-tools` is not the boundary.
- Workflow engine (MVP-1 pull request 4): workflow reads are not grant-governed (R-64; must become grant-governed
  before any non-synthetic use); one human with two `users` rows cannot be detected as the same approver (R-57);
  calendar availability, absence and working-day due dates are not validated (R-60); the proposal form knows three
  rule templates only (R-62); approver qualification (`MA`, department head) is a candidate until R-4. The
  workflow triggers do not stop TRUNCATE or DROP by a database owner (R-58, R-61).
- Windows file-publish path (`os.rename`, slice 5): tested locally only; there is no Windows CI job.
- Mutation M8 (slice 5, Linux publish path changed to `os.replace`): the no-overwrite test failed after the
  overwrite had happened (`FileNotFoundError` on the temporary file), not on its first assertion.
- Grants (MVP-1 slice 3): the `classification` columns on `departments`, `users` and `projects` have no database
  CHECK constraint (service-layer validation only; the additive-only migration guard does not allow
  `create_check_constraint` on existing tables; the new grant tables do have CHECK constraints). Project
  classification has no route (it can be set in the database only).
- Super admin skills: what `allowed-tools` pre-approves was not shown (the acceptance run was approved by auto mode);
  `disallowed-tools` is accepted by the installed Claude Code's frontmatter schema, but its effect was not observed
  in a run.
- Docker Compose beyond the PostgreSQL service: no other service has been run. A PostgreSQL restore drill has not been run.
- Benchmark harness (slice 4b, on `main` since `d7f1127`): tested only against a fake server on 127.0.0.1; no live
  run is recorded. The Admin made a trial run on 2026-10-13; it exists, untracked, and no numbers from it are
  recorded here. Response field names come from the Ollama `v0.40.0` source at `0d0720e5`; whether `eval_count`
  includes thinking tokens and the effect of the request field `think` on `gemma4:12b` are not verified
  (`docs/BENCHMARK-PLAN.md`, section 7).
- Benchmark container `ollama-bench` (slice 1b): started, checked and smoke-tested by the Admin on 2026-10-12
  (Admin-supplied output; not run by Claude Code); no benchmark cell has been run. Whether Ollama `v0.40.0` has a
  per-request control for `gemma4:12b` thinking output (plan open item 12). `scripts\reset-db.bat` runs
  `docker compose down -v` and may delete the benchmark models volume (not tested); models would have to be pulled
  again. The start command needs `POSTGRES_PASSWORD` set (normally from the Admin's `.env`; no value is recorded).
- Authentication (R-3): the CI install log for the compiled dependencies (not readable without a token; the
  install and test steps passed); payload-bound approval (later slice); OIDC sign-in; a breached-password lookup; demo-mode accounts for the fixture
  people; the CLI commands (`bootstrap-admin`, `grant-account-admin`, `revoke-account-admin`) run in a real terminal
  (tested with stubbed input; the revoke race on PostgreSQL, the rest on SQLite).
- Any UI; end-to-end or browser tests.
- Python 3.11 on PostgreSQL: CI job `test-py311` (Python 3.11.17) covers the SQLite suite only; no local 3.11
  interpreter is installed.
- Upstream matrix (`docs/UPSTREAMS.md`, *Claims register*; slice 2 done for the exit, R-28): Ollama outbound calls
  in dependencies and at runtime (only the source at `0d0720e5` was grepped); `gemma4:12b` audio (inferred from the
  code and a partial projector metadata read, hash not verified; not run); Tier C feature
  claims (Hermes skills and gateway, Hindsight plugin and isolation, WeKnora retrieval and ACL); Digital-Secretary;
  Telegram terms; the licences of the images in WeKnora's compose file. Model fit on the 12 GB VRAM host is a
  measurement (slice 4).
- All live integrations (mail, Telegram, model providers/Ollama, Hermes, WeKnora, Hindsight).
- Model-provider contract (on `main` since `53f6f23`): simulated providers only. Not verified: Ollama's cloud-tag
  naming rule (`docs/cloud.mdx` at `28a9f8c…` gives one example and no rule; any name containing "cloud" is treated
  as cloud), any real endpoint, whether an `org_private` endpoint
  is really private, error messages, keys, spend caps and speech providers. The gateway is an application-level
  control only; Hermes and network-level egress are not covered. A local Ollama daemon contacts `ollama.com` by
  default unless cloud features are disabled (`docs/UPSTREAMS.md`, source read 2026-10-10).
- Whether the pinned PostgreSQL digest (`d74eeac9…`) is a multi-arch index or an amd64-only manifest; only amd64
  hosts have used it (local Docker Desktop and the CI runner).
- Image digest check (on `main` since `a7b90da`): CI runs as reported by the Admin; the job logs were not read. Known limits, listed in
  `scripts/check_image_digests.py`: `--build-arg` overrides, `COPY --from` and `RUN --mount ... from=` images, YAML
  flow mappings, anchors and multi-line scalars, images in scripts and documentation, and files not yet tracked (it
  reads `git ls-files`: `git add` a new file before running it locally). CI's ruff and mypy cover `apps/api` only,
  so `scripts/` is not linted or type-checked in CI (known gap; the script was checked by hand with both).

## Local material outside the repository

- A local candidate policy file exists outside version control. It is never loaded automatically and has no policy
  ID, version, effective date or approval; those must come from the policy owner and Top Management (R-9).
  Operational mode therefore reports `policy_missing`.
- Development reference `VREF-00` was inspected read-only via the GitHub API. Its identity and detailed paths are
  kept in a local, unpublished, git-ignored citation register; public files cite `VREF-nn` IDs only.
- Local backups are kept outside the repository.

## Publication and security

- The public history was rewritten under Admin authorisation before this baseline (R-11). Commits that are no
  longer on any branch may remain retrievable from GitHub by direct link until GitHub removes them.
- Before this update the tracked tree was scanned for known organisation identifiers, secret patterns, private
  paths and candidate policy values. Scan limits: pattern matching against known terms only; it cannot detect
  identifiers it does not know, secrets in unrecognised formats, or copies held outside this repository.

## Known mismatches (deferred)

- Code references to documents that do not exist: `apps/api/qms_os/knowledge/__init__.py` cites
  `docs/adr/0004-independent-knowledge-module.md` and `docs/05-knowledge-roadmap.md`. (`docs/adr/0003` exists on
  `main` since pull request #10, and the development-identity docstring it replaced is gone.) The provider ADR is
  therefore numbered 0005 and 0004 stays unused; `knowledge/__init__.py` is unchanged (Admin, 2026-10-09).
- `docs/SPECIFICATION.md` refers to `docs/decisions.md`; the file is `docs/DECISIONS.md`.
- The specification's repository layout is partly adopted: the code lives in `apps/api/` (R-1, decided); other `apps/` and `packages/` folders do not exist yet.
- The specification makes PostgreSQL the authority; the code still defaults to SQLite. PostgreSQL support (R-14) is on
  `main` and is tested locally and in CI (job `postgres`).
- The specification asks pull-request CI for formatter, type, lint and integration checks and a secret scan. On
  `main`, CI runs the tests on SQLite (3.12 and 3.11) and PostgreSQL, a secret scan, lint (ruff) and type checks
  (mypy on `qms_os`, with a per-module baseline of existing errors); no formatter is enforced (Admin
  decision, 2026-10-07: `ruff format` would rewrite about 4,400 lines).
- `CLAUDE.md` refers to a stage-prompt document that is held by the Admin and is not in this repository.

## Open decisions

- Unresolved engineering decisions: R-4 (`docs/DECISIONS.md`). R-2, R-3 (2026-10-06; on `main` via pull request #10)
  and R-14 are decided; R-7 gained `401`.
- Not yet decided for authentication: named owners for the session and lockout candidate values (R-4); a
  breached-password lookup; the payload-bound approval slice. The `account_admin` role is granted and revoked only
  with the operator CLI (ADR 0003; on `main` since pull request #14).
- `scripts\env.bat` temp and cache location — **decided (Admin, 2026-10-06):** keep the in-repo defaults (`.cache\`,
  `.tmp\`, both git-ignored) with an optional `QMS_TEMP_ROOT` override that moves TEMP/TMP (and pytest's temporary
  folders) to `<root>\tmp` and the pip cache and pycache to `<root>\cache`; a C: or relative root, or a folder that
  cannot be created, stops the scripts with exit code 1 (no fallback to C:). On `main` since pull request #12; see
  `docs/LOCAL-RUNTIME.md`.
- Proposed order of the next slices (a proposal, not a commitment): (1) the `env.bat` `QMS_TEMP_ROOT` override
  (done, pull request #12); (2) a CLI command to grant or remove `account_admin` (done, pull request #14); (3) CI:
  a secret scan and a PostgreSQL job (done, pull request #15); (4) the one-time link code (done, pull request #18)
  — it was **a blocker before any real person is onboarded**; at least two account admins are still required
  (`docs/ROADMAP.md`; ADR 0003, *One-time links need two parts*); (5) payload-bound approval.
- Decided 2026-10-07 (Admin): all six CI jobs are required status checks, with the up-to-date rule (R-13).
- Slice 1 blockers: the image-digest check (slice 3a, R-21) runs first; the object-store product (R-15, Admin
  decision) and scope proposal R-16 (Ollama first) stay open until the WeKnora spike (slice 3b, R-22).
- Decided 2026-10-09 (Admin): R-17 local providers by default, cloud only when an admin enables it and the data class
  permits; R-18 every model call logs provider, model and egress class, no content; R-19 confidential records only to
  `local` or `org_private` providers unless an admin allows otherwise; R-20 edge-tts off by default and never for
  confidential content; R-21 images by digest, models by digest or commit; R-22 WeKnora a candidate shared knowledge
  base, Hermes keeps its own vaults; R-23 real spike material stays on the Admin's machine, aggregates only in Git.
- Decided 2026-10-09 (Admin, slice 3 plan): R-24 data classes `public < internal < confidential` (Candidate
  values), cloud ceiling `public` by default; R-25 one account admin with step-up changes provider settings, live
  adapters refused until two-admin approval of widening changes exists; global cloud switch kept, off by default;
  `model_digest` optional until live adapters (R-21).
- Not yet decided: database-level append-only enforcement (for `audit_events`, and for `evidence_objects`
  beyond the R-52 triggers); production use of the psycopg binary wheel versus a local build
  (`docs/UPSTREAMS.md`).
- Unresolved organisational decisions: D-07, D-08, D-12, D-13, D-14, D-15, D-16.
- Candidate values (D-01, D-02, D-04, D-05, D-06) need named owners before any becomes policy (R-4).
- The organisation policy needs an ID, version and effective date from the policy owner, then Top Management
  approval (R-9).
- No external decision-routing or classification integration is approved for implementation.

## Next tasks

See *MVP-1 plan* in `docs/ROADMAP.md` (bundled pull requests, R-37). No dates or delivery commitments have been
made.

Open for slice 10 (2026-10-21):

- The Admin decides when `frontend` becomes a required check (R-13, R-71); it is green on `main` at `efaeec1`.
- Slice 10b (2026-10-21, local results): Python suite 568 passed, 2 skipped; PostgreSQL full suite 599 passed (at
  `6186328`); 34 component tests; 3 browser tests in Chromium 153 (smoke under the CSP; sign-in, reload, step-up
  with one retry, sign-out); lint, type check, build, bundle check, licence check (221 packages, 0 refused) and
  audit clean. Bootstrap guard mutations M-10b-1 and M-10b-2 caught (`apps/api/tests/test_test_bootstrap.py`).
  CI runs only on pull requests and pushes to `main` (and by manual dispatch); the `e2e` job first ran on pull
  request #42 (run 39562347176) and passed there and on `main` (run 39562889995).
  Locally the browser lives in `D:\QMS-OS-TEMP\ms-playwright` (`PLAYWRIGHT_BROWSERS_PATH`); the tests need
  `QMS_E2E_PYTHON` naming the virtual environment's Python and a fresh `pnpm run build`.
- Slice 10c (2026-10-21, local results, branch `feat/mvp1-admin-ui-org`): Departments and People screens behind an
  "Organisation" menu shown only with the org-admin hint; every action calls the existing org routes and is followed
  by a fresh load; errors read "Error <status>: <detail>", 403 and 404 as "Not available." (R-72). Python suite 587
  passed, 2 skipped; PostgreSQL full suite 618 passed; 48 component tests; 5 browser tests; `tests/test_org_ui_refusals.py` calls each of the ten
  actions directly: no permission 403, stale step-up 401 `step_up_required`, no session 401, missing or wrong
  `X-QMS-CSRF` 403 on a real cookie session, own record 403, unknown record 404, forbidden deactivation 422; no audit
  event is written by any refusal. No new route or dependency.
- Slice 10d (2026-10-21, local results, same branch): Role grants, Projects, Access preview and Agents screens; new
  route `GET /api/v1/org/projects` (org admin with a fresh step-up; every project with its current members; no audit
  event for the read), added to the org route set (`tests/test_org_admin.py`). The agent preview loads the agent's
  and its person's previews in one step and shows per kind "Agent only" counts and "Never wider than its person", or
  an alert if any count is not zero (D11). Python suite 607 passed, 2 skipped; PostgreSQL full suite 638 passed;
  63 component tests; 7 browser tests; the twelve 10d actions get the same direct-API refusals as 10c (plus agent
  principals 403); mutation M-10d-1 (the project list guarded by `current_user` instead of `org_admin`) is caught by
  1 test. No new dependency.
- Grant-governed workflow reads (R-64; ADR 0007, *Consequences*: open with the list routes
  `GET /api/v1/workflow/proposals` and `GET /api/v1/workflow/versions?status=`): to be decided in a new ADR 0008,
  not yet drafted.
- Remaining claims: the 16 admin web UI package licences (C-131 to C-146) are package metadata only, not verified
  against the licence text; C-147 flagged (lightningcss, R-73); C-148 (audit) is dated registry data.
- Stale text found on 2026-10-21 and corrected on `feat/mvp1-admin-ui-signin`: the claims register's header now
  says 10 flagged (9 kept as labelled on 2026-10-13, C-147 on 2026-10-15); the pnpm note in `docs/UPSTREAMS.md`
  (*Admin web UI*) records the 2026-10-21 re-run with pnpm 10.34.6; `docs/ROADMAP.md` *Current baseline*, the
  MVP-0 "as of" line and the *MVP-1 plan* status now name `efaeec1` and pull requests #40 and #41. The "9 flagged"
  figures in the MVP-0 exit evidence of `docs/ROADMAP.md` and in this file's *Stage* line are dated 2026-10-13 and
  were right then; they are left as they are.

## Binding design decisions

- Claude Code is the *interactive, human-operated* Superadmin and developer; normal Admin UI controls organization, people, departments, agents, provider policies and workflows. Claude Code is not an unattended Claude subscription API.
- Any development-reference repository designated by the Admin (`VREF-00`) is a **read-only development reference only** for now. The QMS OS MVP must not clone, bulk-copy, index, synchronize or depend on it at runtime/CI. Record its identity, inspected branch and SHA only in the local, git-ignored citation register and cite `VREF-nn` IDs here; never copy organisation identity or content into QMS OS; access only through an authorized GitHub read path if available. QMS OS builds its *own* governed knowledge infrastructure later.
- Local Windows/Docker/WSL2 first; GitHub code and synthetic CI; optional Vercel synthetic-data Admin UI previews only. Hermes agents receive scoped skills/memory and Admin-configured providers; Hindsight, WeKnora and vaults never approve controlled QMS state.
- Telegram voice replies pair a full written answer with a short, separately composed spoken explanation; verbatim reading only on explicit request.
- ISO 9001:2026 edition-specific mapping is human-validated against licensed text; no invented compliance or certification.

## Last sessions (2026-10-06 to 2026-10-10)

- Pull request #9 (run-tests exit code) merged as `997e55b`, CI passed.
- R-3 (local accounts + TOTP) merged as `23329f3` (pull request #10, squash of `5e5ada2` and `74a4460`); CI job
  `test` passed on the pull request and on `main`, on Linux, including the first install of its compiled
  dependencies. Before the merge, locally: `scripts\run-tests.bat` `155 passed, 1 skipped`, `scripts\run-pg-tests.bat
  full` `172 passed`; after the merge, `scripts\run-tests.bat` on `23329f3` `155 passed, 1 skipped`, exit 0.
- Pull request #11 (handoff after the R-3 merge) merged as `82d5897`, CI passed.
- Branch `feat/env-temp-root` from `82d5897…`: `scripts\env.bat` gains the optional `QMS_TEMP_ROOT` override and
  stops on a bad root; `run-tests.bat`, `run-pg-tests.bat`, `setup-venv.bat` and `where.bat` now stop if `env.bat`
  fails. Verified on 2026-10-06 (Windows): `QMS_TEMP_ROOT=C:\QMS-OS-TEMP`, `c:\temp` and a relative path each exit 1
  before pytest starts; with `QMS_TEMP_ROOT=D:\QMS-OS-TEMP`, `scripts\run-tests.bat` gave `155 passed, 1 skipped`
  (exit 0), wrote 59 temp and 881 pycache files under `D:\QMS-OS-TEMP` and none in the repo's `.tmp`/`.cache`, and
  `pip cache dir` reported `D:\QMS-OS-TEMP\cache\pip`; unset, it gave `155 passed, 1 skipped` (exit 0) with temp
  files in the repo's `.tmp` and none under `D:\QMS-OS-TEMP`; `scripts\run-pg-tests.bat` gave `17 passed, 155
  deselected` (exit 0); no pip, pycache or pytest file was written under `C:\Users` (other applications' own files
  in the Windows temp folder were not from these runs). Merged as `58bfd13` (pull request #12); the branch has been
  deleted. Synthetic mode.
- `.gitattributes` (`*.bat text eol=crlf`): batch scripts stay LF in the repository and are checked out CRLF on every machine, whatever its `core.autocrlf` (`git add --renormalize .` changed no file).
- Pull request #13 (`.gitattributes`) merged as `9b79841`, CI passed.
- Branch `feat/account-admin-cli` from `9b79841…`: operator CLI `grant-account-admin` / `revoke-account-admin`
  (`qms_os/auth/cli.py`, `service.py`); active account required, last active admin protected, typed e-mail
  confirmation for a grant, audit events with actor kind `operator` and channel `cli`; no API route. New tests:
  `tests/test_account_admin_cli.py` (12, SQLite) and one PostgreSQL test (two concurrent revocations leave exactly
  one admin; shown to fail 3 of 3 times against code without the row locks, scratch mutation run). On 2026-10-06:
  `scripts\run-tests.bat` `167 passed, 1 skipped, 1 warning` (exit 0); `scripts\run-pg-tests.bat full` `185 passed,
  1 warning` (exit 0). Merged as `d65b0c9` (pull request #14); the branch has been deleted. Synthetic mode.
- Branch `ci/secret-scan-and-pg` from `d65b0c9…`: `.github/workflows/ci.yml` gains jobs `postgres` and
  `secret-scan` and a `workflow_dispatch` trigger (job `test` unchanged); new `.gitleaks.toml` (default rules plus
  one allowlisted path, the vendored password list). Checked locally only: `actionlint` 1.7.12 passed; gitleaks
  8.30.1 found no leaks in the whole history (17 commits) and in the new files, and detected a fake key outside the
  allowlisted path in a scratch repository; `scripts\run-tests.bat` `167 passed, 1 skipped` (exit 0). Merged as
  `0f66d47` (pull request #15); all three jobs passed in CI on the pull request and on `main` (see *Verified
  state*, CI); the branch has been deleted.
- Branch `docs/handoff-ci-merged` from `0f66d47…`: this handoff, ROADMAP and UPSTREAMS update only. Merged as
  `816f574` (pull request #16), then the `CLAUDE.md` scan rule as `81d0cb8` (pull request #17); CI passed for both.
- Branch `feat/link-code` from `0f66d47…` (link-code slice; Admin decisions of 2026-10-07: option B, two-admin
  invitations, Argon2id, old links refused, tightened single-admin exception): verification code shown only to the
  initiator, link token only to the approver; invitations become two-step like resets; single-admin bootstrap
  invitation only while exactly one account-admin record exists (disabled accounts count), flagged
  `split_knowledge = false`; pending requests expire after 72 h, the code with the link (24 h); 5 wrong codes void the
  link; links without a code refused. Migration `c5ee69870dbb` (additive). Tests: `tests/test_link_code.py` (12) and
  three PostgreSQL race tests, each run against an unlocked mutation (wrong codes and parallel approvals fail 3 of 3
  without locks; the disable race passes without locks — the record count does not depend on them — and fails 3 of 3
  when the exception counts only active admins). On 2026-10-07: `scripts\run-tests.bat` `179 passed, 1 skipped, 1
  warning` (exit 0); `scripts\run-pg-tests.bat full` `200 passed, 1 warning` (exit 0); `alembic check`: no new
  operations at `c5ee69870dbb`. Committed as `5313008`, then rebased onto `81d0cb8`; after the rebase the same two
  commands gave the same counts and `alembic check` / `alembic current` showed `c5ee69870dbb (head)`. Merged as
  `eb3c583` (pull request #18, head `69a60d3`); CI passed on the pull request and on `main` (see *Verified state*,
  Git); the branch has been deleted.
- Branch `docs/refresh-status` from `eb3c583…`: documentation only — out-of-date status lines refreshed (link code
  merged, baseline, test counts, MVP-0 stage, upstream-matrix row) and the table of the six slices remaining before
  the MVP-0 exit added to `docs/ROADMAP.md`. On 2026-10-07: `scripts\run-tests.bat` `179 passed, 1 skipped, 1
  warning` (exit 0); `scripts\run-pg-tests.bat full` `200 passed, 1 warning` (exit 0).
  Merged as `31966a2` (pull request #19).
- Branch `ci/lint-types` from `31966a2` (MVP-0 slice 5; Admin-approved plan, 2026-10-07): ruff 0.16.10 with an
  explicit rule list (E, W, F, I, B, UP, DTZ; no formatter), mypy 2.4.0 on `qms_os` (Python 3.11 target,
  `warn_unused_ignores`, `warn_redundant_casts`) with a per-module baseline of the 99 existing errors in
  `apps/api/pyproject.toml`, new extra `lint`, `scripts\run-lint.bat`, and CI jobs `lint`, `types` and `test-py311`
  (Python 3.11.17, asserted in the job). Code changes are lint fixes only: automatic fixes (imports,
  `timezone.utc` → `UTC`, typing modernisation), 27 long lines wrapped, `noqa` with a one-line reason for five
  intentional DTZ cases, B017 (`pytest.raises(InvalidTag)`), B905 (`itertools.pairwise`, the same 2 pairs of 3
  cycles), one unused import. Merged migrations and `qms_os/auth/service.py` are unchanged (per-file ignores).
  Checked on 2026-10-07 (Windows, Python 3.12.7): `scripts\run-tests.bat` `179 passed, 1 skipped, 1 warning`
  (exit 0); `scripts\run-pg-tests.bat full` `200 passed, 1 warning` (exit 0); `scripts\run-lint.bat` ruff "All
  checks passed!", mypy "Success: no issues found in 38 source files" (exit 0). Scratch checks outside the repo: the
  B017 test fails when the ciphertext is not bound to the user and when a wrong user gives an error other than
  `InvalidTag` (the old `pytest.raises(Exception)` passed the latter); the mypy baseline still reports a new error
  in an unlisted module and a new error code in a listed one. Merged as `5b3e181` (pull request #20; CI run
  37648488409 per the Admin; Python 3.11.17 verified for the SQLite suite only). The Admin then made all six jobs
  required checks with the up-to-date rule.
- Branch `docs/upstream-matrix` from `5b3e181` (MVP-0 slice 2; Admin-approved plan, 2026-10-07): `docs/UPSTREAMS.md`
  gains the base application stack (Tier A: pinned versions, installed-metadata licences as a secondary source),
  the model runtime and local models (Tier B), one row per named service (Tier C) and a "named, not adopted, not
  inspected" list (Tier D); `docs/DECISIONS.md` gains R-15 (object store, Admin decision) and R-16 (slice 1 scope,
  proposal) and R-12/R-13 updates; out-of-date status lines refreshed here and in `docs/ROADMAP.md`. Network:
  read-only WebFetch, no credentials; the first request (FastAPI `LICENSE` at `0.141.1`) succeeded, the second
  (that tag's commit) returned `404`, and no further request was made. On 2026-10-07: `scripts\run-tests.bat`
  `179 passed, 1 skipped, 1 warning` (exit 0); `scripts\run-lint.bat` ruff "All checks passed!", mypy "Success: no
  issues found in 38 source files" (exit 0). Two local commits (`033b666`, `dd828a0`), later merged as `fe6eb05` (pull request #21). Synthetic mode.
- Same branch, second pass (Admin's corrected stop rule, 2026-10-07: stop only on network-level failures; a 404 on a
  guessed URL form is retried once with a documented alternative): tag commits from the GitHub ref API and licence
  files at those commits. Tier A: 24 of 25 verified (pluggy names no repository); FastAPI's commit is
  `95f8322e…`. Tier B: Ollama `v0.40.0` (commit `0d0720e5…`, MIT, installer and image digests); `gemma4:12b` exists
  with 256K published context (matches the specification; nothing recorded in DECISIONS), Apache-2.0 weights (licence
  layer hashed locally; Hugging Face revision `707f0a3b…`); conflicts recorded: two short IDs for the tag, and
  text-and-image (Ollama) versus text, image, audio and video (Hugging Face) inputs. Tier C: WeKnora, Hermes, Hindsight
  MIT, edge-tts LGPL-3.0 (one MIT file); edge-tts sends text to a Microsoft online service (from its source).
  Findings: Ollama auto-updates on Windows; cloud model tags exist; WeKnora's compose file brings its own MinIO,
  SearXNG and `:latest` images. No network-level failure occurred.
  Merged as `fe6eb05` (pull request #21; see *Verified state*, Git).
- Branch `docs/provider-decisions` from `fe6eb05` (2026-10-09, documentation only): `docs/DECISIONS.md` gains R-17
  to R-23 (Admin decisions of 2026-10-09); `docs/ROADMAP.md` gains slices 3 (provider contract scope), 3a (CI
  image-digest check), 3b (WeKnora spike) and the slice 4 audio benchmark plan (still not started); `docs/UPSTREAMS.md`:
  pluggy 1.6.0 verified MIT (`pytest-dev/pluggy`, tag commit `fd08ab5f…`; repository from the project's documentation
  and PyPI provenance), Tier A now 25 of 25; WeKnora `THIRD_PARTY_NOTICES.md` and `licenses/` read at `3e8b0bfc…`
  (MPL-2.0, Apache-2.0 and MIT components). Read-only WebFetch, no credentials, no network-level failure. A
  line-break corruption in the previous entry (`scripts\run-tests.bat`) was repaired. Synthetic mode.
- Pull request #22 (`docs/provider-decisions`) merged as `dae34ae` (see *Verified state*, Git).
- Branch `feat/provider-contract` from `dae34ae` (2026-10-09; ROADMAP slice 3; synthetic, simulated providers only;
  ADR 0005, R-24, R-25). Commit 1 `9322839`: `qms_os/providers/` (contract, egress rules, simulated providers,
  registry refusing `live` adapters, gateway), tables `provider_allow_entries`, `provider_egress_settings`,
  `model_egress_log`, additive migration `44bca21ba248` (down_revision `c5ee69870dbb`, autogenerated against the
  PostgreSQL test database and reviewed), `tests/test_providers.py`, one PostgreSQL test. Commit 2: admin service and
  routes under `/api/admin/providers` (account admin + step-up, audit events `provider.allowlist.*` and
  `provider.cloud_egress.*`), `tests/test_provider_admin.py`, docs. No new dependency. Ollama docs read once by
  WebFetch (no credentials). Mutation checks (patches kept in `D:\QMS-OS-TEMP\scratch\mutations`, not committed;
  each file restored byte-identical and checked by SHA-256 afterwards), each applied alone, with the failing output:
  - M1 no cloud-tag check: `test_ollama_cloud_tag_refused_while_cloud_is_off` 4 of 4 failed,
    `assert 'not_allowlisted' == 'cloud_tag'`.
  - M2 allow-list looked up by provider only: `test_provider_or_model_not_on_the_allow_list_refused` failed.
  - M3 no data-class check: `test_data_class_ceiling` 2 of 5 failed and
    `test_ollama_cloud_tag_allowed_only_with_switch_entry_and_public_data` failed, `DID NOT RAISE ProviderRefused`.
  - M4 prompt written to Python logging: the no-content test failed, `assert 'CANARY-…' not in 'INFO …'`.
  - M5 cloud switch ignored: the cloud-tag test 4 of 4 failed (`'not_allowlisted' == 'cloud_tag'`) and
    `test_cloud_provider_refused_by_default` failed (`DID NOT RAISE ProviderRefused`).
  - M6 `add_entry` at level `human` instead of `account_admin`: the access test failed for fixture person `ma`, and
    `test_approval_and_admin_routes_need_step_up` failed on `/api/admin/providers/allowlist`. (A first M6 attempt was
    invalid — its inline comment cut the signature, `NameError` — and was redone.)
  - M7 no audit event on add: `test_adding_an_entry_…_is_audited` failed, `assert [] == [('provider.a…`.
  - M8 log rows not committed in their own transaction: the SQLite rollback test and the PostgreSQL test
    `test_egress_log_commits_independently_of_the_callers_transaction` failed, `assert [] == ['dispatched'…`.
  - M9 `dispatched` written after the call: `test_dispatched_row_is_committed_before_the_provider_is_called`
    failed, `assert [] == ['dispatched']`.
- Pull request #23 (`feat/provider-contract`) merged as `53f6f23`; `main` CI run 37939344103 green (as reported by
  the Admin).
- Branch `feat/ci-image-digest-check` from `53f6f23` (2026-10-09; ROADMAP slice 3a; synthetic): stdlib-only
  `scripts/check_image_digests.py` (tracked files only; Dockerfile `FROM` with ARG defaults, compose and workflow
  `image:`, workflow `container:` and `docker://`), baseline `scripts/image-digest-baseline.txt` with one entry
  (`compose.yaml postgres:${POSTGRES_TAG:-17}`; slice 1 fixes it), a stale entry fails (ratchet); a step in the `lint`
  job and in `scripts\run-lint.bat`; `tests/test_image_digest_check.py` (29 tests, one against this repository).
  Shown failing once in a scratch git repository outside the project (`D:\QMS-OS-TEMP\scratch\digest-demo`, not
  committed): an unpinned `redis:7` gave "compose.yaml:3: image reference without @sha256 digest: redis:7", exit 1;
  after pinning it, the old baseline line gave "stale entry, remove it", exit 1. Separate carry-over from slice 3:
  `tests/test_providers.py` refuses a model name with a space and over-long hyphenated model and provider ids with
  `invalid_identifier`.
- Pull request #24 (`feat/ci-image-digest-check`) merged as `a7b90da`; pull request run 38024123786 and `main` run
  38024289981 (as reported by the Admin).
- Branch `feat/pin-compose-postgres` from `a7b90da` (2026-10-10; ROADMAP slice 1, PostgreSQL pin only; synthetic;
  merged as `e4ebfd3`, pull request #25; pull request run 38028183377, `main` run 38033037362, as reported by the
  Admin): `compose.yaml` image `postgres:17.11@sha256:d74eeac9a635390a49bc21bd49fccd973de707e2a53a76ac49b552b8712ec46f`
  (the CI reference; Admin decision 2026-10-10), `POSTGRES_TAG=17` removed from `.env.example`, the baseline line
  removed (header kept), the real-repo test renamed `test_this_repository_passes_with_an_empty_baseline`. With
  compose pinned and the line still present the check gave "image-digest-baseline.txt: stale entry, remove it:
  compose.yaml postgres:${POSTGRES_TAG:-17}", exit 1; after removing it "2 scanned in 2 files, 0 baselined, 0
  problems", exit 0. Commands run on Windows: `scripts\run-tests.bat` `261 passed, 1 skipped, 1 warning` (exit 0);
  `scripts\run-lint.bat` ruff "All checks passed!", mypy "Success: no issues found in 46 source files", digest
  check as above (exit 0); `scripts\run-pg-tests.bat full` `283 passed, 1 warning` (exit 0); `alembic check` "No new
  upgrade operations detected." (exit 0); compose start-up as under *Local runtime*. The Admin's local `.env` may still
  hold `POSTGRES_TAG=17`; Compose ignores it (not read or edited).
- Stop rule amendments (Admin, 2026-10-10), added to the corrected rule of 2026-10-07: on a `403` or `429`, switch
  once to `raw.githubusercontent.com` at the commit, then stop and report; a read-only source archive of a tag commit
  may be downloaded into `D:\QMS-OS-TEMP\scratch` (outside the repository, uncommitted, never built, installed or run;
  safe extraction; the top-level commit checked) and searched with local grep, citing `path:line` at the commit.
- Branch `docs/upstream-ollama-items` from `e4ebfd3` (2026-10-10; ROADMAP slice 2, the three Ollama items;
  documentation only; synthetic; merged as `686b12b`, pull request #26; pull request run 38035882422 (six jobs green,
  read from GitHub via the Perplexity GitHub connector, 2026-10-11) and `main` run 38110041414 (as reported by the
  Admin, not verified)):
  `docs/UPSTREAMS.md` gains a tier legend (A to D) and rows read from the source of
  Ollama `v0.40.0` (lightweight tag, commit `0d0720e5…`): the daemon contacts `ollama.com` by default (model
  recommendations every 4 h, cloud-model cache at start; signed with the installation key) unless `OLLAMA_NO_CLOUD=1`
  or `disable_ollama_cloud`; the desktop app checks for updates hourly (no setting found that disables the check);
  per-request `num_ctx` on native `/api/generate` and `/api/chat` only; audio input in the code, and the `gemma4:12b`
  projector metadata has `clip.has_audio_encoder = true` (HTTP Range read, partial read, hash not verified). Requests
  (read-only, no credentials, all `200`/`206`, no `403`, `429` or `404`): `git fetch`; `git ls-remote` and the GitHub
  ref and commit API for the tag; the codeload archive; the `gemma4:12b` manifest, config, params and template blobs;
  the model page; one Range read of the projector blob (one `307` redirect to a `*.r2.cloudflarestorage.com` host).
  ADR 0005, R-16, R-18 and R-21 were not edited; their effects were reported to the Admin. Commands run on Windows
  (no code changed): `scripts\run-tests.bat` `261 passed, 1 skipped, 1 warning` (exit 0); `scripts\run-lint.bat` ruff
  "All checks passed!", mypy "Success: no issues found in 46 source files", digest check "2 scanned in 2 files, 0
  baselined, 0 problems" (exit 0).
- Branch `docs/model-agnostic-providers` from `686b12b` (2026-10-11; documentation only; synthetic; merged as
  `a49baee`, pull request #27; pull request run 38115212746, six jobs green, read from GitHub via the Perplexity
  GitHub connector, 2026-10-11; `main` run 38115607032, six jobs green, run page checked by the Admin (screenshot,
  2026-10-11); commit a49baee8e46bb8ddc70e46968060741c5340c8f5 confirmed via GitHub): Admin decision
  R-26 (decided 2026-10-11): the architecture does not fix a model or runtime; models, runtimes and endpoints are
  provider entries; the three egress classes are unchanged; Gemma4 on Ollama is the first evaluated candidate; a new
  runtime or provider family needs its own `docs/UPSTREAMS.md` entry and an egress classification rule before its
  adapter may be enabled; consistent with `docs/SPECIFICATION.md:10` and `:55`, which is not edited. R-27
  (proposal): a live Ollama adapter or deployment runs with cloud features off. R-16 note (proposal): server-only
  or container Ollama for a shared deployment; the desktop app only on a developer's own machine with R-27 applied.
  ADR 0005's open sentence on the daemon's network contact now points to `docs/UPSTREAMS.md` and R-27; ROADMAP
  slice 4 is runtime-neutral with Ollama and `gemma4:12b` as the first case, and the recorded blockers gain R-27.
  R-17 to R-25 wording unchanged. No code, tests, CI or migrations changed. Commands run on Windows:
  `scripts\run-tests.bat` `261 passed, 1 skipped, 1 warning` (exit 0); `scripts\run-lint.bat` ruff "All checks
  passed!", mypy "Success: no issues found in 46 source files", digest check "2 scanned in 2 files, 0 baselined,
  0 problems" (exit 0).
- Branch `docs/benchmark-plan` from `fed244f` (2026-10-11; ROADMAP slice 4; documentation only; synthetic; merged as
  `b2c74ae`, pull request #29; pull request run 38146662152, read from GitHub via the Perplexity GitHub connector;
  `main` run 38147116486, run page checked by the Admin, screenshot):
  `docs/BENCHMARK-PLAN.md`, the plan only, with no measurement, recording, harness or adapter. Runtime-neutral
  (R-26), Ollama `v0.40.0` and `gemma4:12b` first, measured through the provider contract (ADR 0005); covers
  `docs/SPECIFICATION.md` section 7 (lines 99 to 103) and section 12 (line 158), which is not edited. Dimensions:
  context 8K to 256K, concurrency one then two, memory on the 12 GB host (no assumed co-running), JSON tool calls,
  latency, citation accuracy, an audio-input probe (the Ollama audio question stays open in `docs/UPSTREAMS.md`)
  and speech recognition. Every threshold is "proposed, Admin to set" unless the specification states it (it
  states test points and a measured cap, no numbers); data rules per R-23; a results template, the run order, the
  meaning of "not run" and the gates before a live adapter (R-25; R-27 a proposal); ten open questions for the
  Admin. ROADMAP: slice 4 and the MVP-0 benchmark row read "Plan written
  (`docs/BENCHMARK-PLAN.md`); thresholds proposed, measurements not started"; "as of" moved to `fed244f`. Dimensions
  are numbered B1 to B8 (not D-, to avoid a clash with decision IDs such as D-07). Admin's leans (not decided) on
  open items 1, 8, 9 and 10 are recorded in the plan; the rest stay open.
- Branch `docs/benchmark-host` from `b2c74ae` (2026-10-11; merged as `5a3e3e3`, pull request #30; documentation only;
  synthetic): `docs/BENCHMARK-PLAN.md`
  gains the benchmark host and Docker facts supplied by the Admin (not measured by Claude Code): i9-13900HX, 96 GB
  (95.7 GB usable), RTX 4080 Laptop GPU with 12,282 MiB, Windows 11 Home 10.0.26200, driver 617.14; Docker Desktop
  v4.94.0 on WSL2 with 45.82 GB and 32 CPUs for containers. The existing Ollama container (`ollama/ollama:0.32.1`,
  in the `n8n-services` stack with `cloudflare-tunnel`, `0.0.0.0:11434`, no `OLLAMA_NO_CLOUD`) is not the benchmark
  target. A pre-run checklist (dedicated container, Ollama `v0.40.0` pinned by digest, `127.0.0.1` only,
  `OLLAMA_NO_CLOUD=1`, RTX 4080 visible in the container, plugged in); the VRAM threshold in MiB (11,264 MiB,
  proposed) with MiB, GiB and GB defined; open item 2 answered, 3 decided by the Admin (80 clips), 4 proposed (10
  repetitions, 512 tokens), 11 added (slice 1b). The 48 GB peak-DRAM threshold stays proposed, with the caveat that
  container memory is capped by the Docker allocation (45.82 GB); each run records container and host peak memory.
  A tunnel hostname exists in the local Cloudflare configuration (Admin-supplied; not recorded); the dashboard route
  and any Access policy are not checked. ROADMAP: "as of" `b2c74ae`; slice 1b (dedicated benchmark container) added
  as not started.
- Branch `feat/benchmark-container` from `5a3e3e3` (2026-10-12; merged as `9e57e8b`, pull request #31; ROADMAP
  slice 1b; configuration only; synthetic):
  `compose.yaml` gains the service `ollama-bench` under the profile `benchmark` (never started by default, by
  `scripts/start-db.bat` or in CI): `ollama/ollama:0.40.0` pinned by the index digest
  `sha256:1bef6397…c18e1687` (R-21; read from the registry with `docker buildx imagetools inspect` on 2026-10-12;
  no `v0.40.0` tag exists), `127.0.0.1:11435:11434` only, `OLLAMA_NO_CLOUD=1`, a named model volume, one NVIDIA GPU
  reserved, `restart: "no"`. `docker compose --profile benchmark config` validated it (with a synthetic env file;
  no start, no pull). New `apps/api/tests/test_benchmark_compose.py` reads `compose.yaml` as text and checks the
  digest pin, the loopback-only port, `OLLAMA_NO_CLOUD` and the profile. This implements the proposals R-27 and
  the R-16 note for this benchmark-only container; both remain proposals. `docs/BENCHMARK-PLAN.md` lists the
  Admin's check commands; the container has not been started and the GPU inside it is not checked.
- Branch `docs/benchmark-checks` from `9e57e8b` (2026-10-12; merged as `2a385a9`, pull request #32; documentation
  only; synthetic): `docs/BENCHMARK-PLAN.md`
  records the Admin's container checks (2026-10-12; Admin-supplied output, not run by Claude Code): version 0.40.0, the
  digest-pinned image, `127.0.0.1:11435`, `OLLAMA_NO_CLOUD=1`, the RTX 4080 visible in the container, plugged in, compose
  project `qms-os` (outside `n8n-services`). A smoke test (not a benchmark result): `gemma4:12b` pulled (layer prefixes
  match `docs/UPSTREAMS.md`; the model ID is not comparable), one-word reply with visible thinking text, `ollama ps` 1.1
  GB and 100% GPU at context 4096, `nvidia-smi` 8,786 MiB of 12,282 MiB (one sample). Findings: thinking tokens count
  toward the cap and latency (open item 12; no per-request control verified); larger contexts may not fit on the GPU
  alone (to be measured). ROADMAP slice 1b: done (#31). Every benchmark cell stays `not run`.
- Branch `feat/benchmark-harness` from `2a385a9` (2026-10-13; ROADMAP slice 4b; code, tests and documentation;
  synthetic): new package `apps/api/qms_bench/` (`harness.py`, `prompts.py`, `__main__.py` and the test-mode adapter
  `ollama_adapter.py`; standard library only), outside `qms_os` because the application package holds no HTTP client
  (existing test) and never imports it (new test). The adapter: integration mode `test`, family `ollama`, egress `local`;
  loopback endpoints only, no redirects, no proxies. mypy now also checks `qms_bench`. B4 and B5 at `num_ctx` 4096 and
  8192, N repetitions (default 10) after one warm-up run, output cap `num_predict` 512; every call through
  `ProviderGateway.call` with a temporary SQLite egress log and allow-list, deleted after the run (benchmark runs bypass
  the Admin's audited allow-list; the application's database is never opened; both tested); the model digest is checked
  against `GET /api/tags` before any call (R-21). Raw records go to the untracked `bench-results/` (.gitignore, R-23);
  the aggregate table is printed only, with the provider, model and egress class. New `scripts\run-benchmark.bat` runs it
  from the repository root. The registry's refusal of `live` adapters (R-25) is unchanged and tested; no default registry
  registers the adapter. New `apps/api/tests/test_benchmark_harness.py` uses a fake server on 127.0.0.1.
  `docs/BENCHMARK-PLAN.md` section 7 "Harness"; ROADMAP slice 4b. No live run; every benchmark cell stays `not run`.
  Merged as `d7f1127` (pull request #33; see *Verified state*, Git).
- Branch `docs/mvp0-closure` from `d7f1127` (2026-10-13; documentation only; synthetic): `docs/DECISIONS.md` gains
  R-28 (decided, Admin, 2026-10-13): the MVP-0 exit is read as written in the specification; benchmark measurements
  are not an exit item; slice 2 closes when every feature claim is verified with source and date or labelled "not
  verified"; slice 1 is descoped for the exit; R-15, R-16, R-22, R-27 and the benchmark thresholds are unchanged.
  `docs/ROADMAP.md`: the remaining-slices table as of `d7f1127` (one exit slice remains: 6). Slice 2 labelling
  pass, done for the exit: `docs/UPSTREAMS.md` gains a *Claims register* (126 claims: 67 verified with source and
  date, 52 not verified, 7 flagged as not verified with no stage needing them, which the Admin kept as labelled on
  2026-10-13, none removed or researched); unsourced claims labelled
  "not verified" in place in `docs/UPSTREAMS.md`, `docs/adr/0003-auth-dev-identity.md`,
  `docs/adr/0005-provider-contract-and-egress.md`, `docs/LOCAL-RUNTIME.md` and `docs/BENCHMARK-PLAN.md`; the
  UPSTREAMS GPU-in-container row now cites the Admin's 2026-10-12 check; a stale LOCAL-RUNTIME line (Postgres
  image "pinned by tag") marked resolved. No new research, no code, tests, CI or migration changes;
  `docs/SPECIFICATION.md` not edited. Merged as `fa5c5f2` (pull request #34; see *Verified state*, Git).
- Branch `docs/mvp0-review` from `fa5c5f2` (2026-10-13; slice 6, the MVP-0 exit review; documentation only;
  synthetic): `docs/ROADMAP.md` *Current baseline* updated to `fa5c5f2` with counts from runs on 2026-10-13
  (`324 passed, 1 skipped` SQLite, `346 passed` PostgreSQL); the MVP-0 item table and the remaining-slices section
  agree with R-28 (upstream matrix and benchmark plan done for the exit, container configuration descoped, slice 6
  in review, "as of `fa5c5f2`"); new section *MVP-0 exit evidence* (one row per criterion of specification line 158,
  with its evidence and gaps). Out-of-date statements of current state fixed with dated wording (ROADMAP item 9 on
  required checks; UPSTREAMS on the postgres extra in CI, the first CI run of the authentication packages and the
  lint tools in CI; ROADMAP item-table text on per-request `num_ctx` and audio input, verified on 2026-10-10).
  Claims register: completeness search (method in its header) found 4 claims with no row (C-127 to C-130) and 4
  restatements (added to their rows); now 130 claims: 67 verified, 54 not verified, 9 flagged, kept as labelled by
  the Admin on 2026-10-13 (including C-129 the psycopg LGPL note and C-130 "pg8000 is BSD-licensed"). Admin
  decisions (2026-10-13): C-129 and C-130 kept as labelled; the screenshot-based CI evidence for run 38412392880
  accepted. MVP-0 is not declared complete; the Admin decides. Merged as `e1b5276` (pull request #35; see
  *Verified state*, Git).
- Branch `docs/mvp0-declaration` from `e1b5276` (2026-10-13; documentation only; synthetic): `docs/DECISIONS.md`
  gains R-29 (decided, Admin, 2026-10-13): the MVP-0 exit is declared met on the narrow reading (R-28), with its
  evidence (*MVP-0 exit evidence* in `docs/ROADMAP.md` and the claims register: 130 claims, 67 verified, 54 not
  verified, 9 flagged and kept as labelled) and its accepted gaps (startup on SQLite only, "safe" by the test's
  design, keyword-based completeness search, CI evidence from screenshots); R-15, R-16, R-22, R-27 and the benchmark
  thresholds unchanged. `docs/ROADMAP.md`: MVP-0 status "Declared met (R-29)" (status line, item table,
  remaining-slices section with no slices remaining, slice 6 done); baseline and "as of" `e1b5276` with counts from
  runs at `e1b5276` (unchanged: `324 passed, 1 skipped`; `346 passed`); post-merge check CI run 38434451817 added to
  the evidence section (Admin's screenshot); the `fa5c5f2` evidence rows unchanged. Merged as `59d4d5e` (pull
  request #36; see *Verified state*, Git).
- Branch `feat/mvp1-foundation` from `59d4d5e` (2026-10-14; MVP-1 pull request 1, slice 1; code, tests and
  documentation; synthetic): `docs/DECISIONS.md` gains R-30 to R-38 (Admin decisions of 2026-10-14: org-admin
  permission; grant model; baseline approval bound to the version digest; rules-only proposal form; R-15 decoupled
  from the WeKnora spike with an interim local content-addressed store for synthetic fixtures; `/api/v1` in pull
  request 2; frontend ADR before the UI; bundled pull requests; super admin operations as project skills), with a
  dated note on R-15 and R-16's topic reworded (slice 1 was descoped by R-28). `docs/ROADMAP.md` gains *MVP-1 plan*
  (bundle table with each slice's exit criterion) and *Super admin skills and documentation* (approved by the Admin
  on 2026-10-14 as written; no skill or documentation file created yet). Code: new
  `apps/api/tests/test_startup_smoke_pg.py` (marker `postgres`): the real server process starts in `demo` mode on
  `127.0.0.1` against the migrated PostgreSQL test database loaded with the synthetic fixture and answers
  `/api/health`; a permanent negative test shows the server
  refuses an unmigrated database (exit code 1, "database schema is at no revision"), with the rebuild in a
  `finally`. The helpers moved from `tests/test_startup_smoke.py` into `tests/server_process.py` (the server is
  stopped in a `finally`); the SQLite test keeps its name and behaviour (`1 passed` before and after). Scratch
  mutation (positive test pointed at an unmigrated database): it failed ("database schema is at no revision"), then
  the file was restored and its SHA-256 checked. Claims C-29 to C-34, C-48, C-50, C-64 and C-114 stay not verified.
  Baselines, the R-16 topic, the MVP-0 order statuses, the MVP-1 row ("using local model or rules"), *Next tasks*,
  the account-admin branch reference and two out-of-date `docs/LOCAL-RUNTIME.md` lines updated. Merged as `ded0fe8`
  (pull request #37; see *Verified state*, Git).
- Branch `feat/mvp1-org-grants` from `ded0fe8` (2026-10-14; MVP-1 pull request 2; code, tests and documentation;
  synthetic; one commit per part): (A) the API moves from `/api` to `/api/v1` (R-35), the session cookie path with
  it, no alias (R-45); no caller outside the tests (CI, `compose.yaml`, `scripts/` and Dockerfiles checked; Ollama's
  own `/api/...` paths in `qms_bench` unchanged); R-39 to R-46 recorded. (B) Slice 2: org directory administration
  under `/api/v1/org/` (departments and people: create, update, deactivate, reactivate; no delete, D-14; each change
  audited, personal fields recorded only as changed, R-42) for holders of the org admin permission
  (`platform_permissions`, migration `ba4ee531f3e8`), granted only by the operator CLI (R-39), never with account
  admin (R-40, deterministic PostgreSQL race test), fresh step-up on every org route (R-41). (C) Slice 3: grants =
  role + project + resource classification (R-31; migration `486e0d8197ea`), `services/access.py` with one decision
  function used by enforcement and the preview, denied single reads 404 (R-44), lists filtered (R-43); mailbox
  scope and delegation declared and empty. (D) Skills `housekeeping-check`, `review-org` and `access-segregation`
  (`.claude/skills/`, `docs/superadmin/`), backed by `apps/api/qms_superadmin` (read-only, synthetic database only,
  R-46) and `scripts\run-superadmin.bat`. (E) This housekeeping. Self-protection (R-47): an org admin cannot change
  their own person record, the grants of their own QMS role, or their own project membership. (F) Wording
  correction (Admin, 2026-10-14): a skill's `allowed-tools` only pre-approves tools and does not restrict them; each
  skill now also sets `disallowed-tools: Write, Edit, NotebookEdit` (accepted by the installed Claude Code 2.1.299
  and the VS Code extension's 2.1.296: both carry a skill frontmatter schema with that field). The boundary is the
  read-only scripts (R-46), the `SKILL.md` rules and the permission settings. Skills acceptance (2026-10-14): Claude
  Code refused to invoke the skills itself (`disable-model-invocation` honoured); the Admin ran `/housekeeping-check`
  (0 findings), `/review-org` and `/access-segregation` (first refused, R-46, then 0 findings on the demo database),
  each running only its one command.
- Pull request #38 merged as `6aa5246` (2026-10-14; see *Verified state*, Git).
- Branch `feat/mvp1-agents-store` from `6aa5246` (2026-10-14 and 15; MVP-1 pull request 3; code, tests and
  documentation; synthetic; one commit per slice plus this housekeeping): (4) slice 4, agent profiles (R-48, R-49;
  migration `295c530829ce`): zero by default, enrolled and revoked by an org admin under `/api/v1/org/agents` with a
  fresh step-up, at most one active agent per person, reads capped at what the person reads, refusals audited,
  revocation final; agents in the effective-access preview, `review-org` and `access-segregation`. (5) Slice 5, the
  interim evidence store (R-50 to R-54; migration `1145709a6ca6`): adapter interface and a local content-addressed
  store outside Git for synthetic fixtures, stored only by the operator CLI, read through `evidence_grants` with an
  identical 404 for denied, unknown and malformed hashes, hash checked before every read, no overwrite or delete
  (database triggers), and the `knowledge-integrity` skill. (D) This housekeeping: baselines to `6aa5246`, the PR 2
  CI evidence, and the `allowed-tools` wording (not relied on as a restriction; public documentation describes it as
  pre-approval only, the installed Claude Code schema wording is ambiguous; boundary unchanged).
- Pull request #39 merged as `caabb11` (2026-10-15; see *Verified state*, Git).
- Branch `feat/mvp1-workflow` from `caabb11` (2026-10-15; MVP-1 pull request 4, R-55; code, tests and
  documentation; synthetic; one commit per slice, a skill commit and this housekeeping): (6) guideline, template and
  versions, digest-bound baseline approval by a qualified non-contributor with step-up, frozen baselined versions
  (R-56 to R-59, R-63, R-64; migration `0e0fc698155b`; ADR 0006); (7) the completeness validator gating submission
  and approval (R-60); (8) cases pinned to a version, migration with a different qualified owner and a kept trace
  (R-61; migration `08e8ac87f38c`); (9) the rules-only proposal form, drafts only (R-62; migration `03c084021bfa`),
  and `tests/test_mvp1_exit.py`; (E) the `inspect-workflow-completeness` skill; (G) this housekeeping.
- Next: MVP-1 pull request 4 review and CI; then the frontend ADR (R-36) and the UI (slice 10), then the exit evidence
  (slice 11). Admin decisions still open: benchmark thresholds (plan open items 1, 4 and 12), R-27 and the R-16 note;
  the R-15 product before any real evidence (R-34); R-4 owners for the approver roles (R-56). Also: the Cloudflare
  route on the existing `ollama` container (open: dashboard route and any Access policy not checked); exit criteria
  for the WeKnora spike (3b) before it starts; payload-bound approval beyond baselines (later slice); harness
  extensions for B1 to B3 and tokens per second in the aggregate; the first benchmark results (the Admin's trial run
  of 2026-10-13 exists, untracked; no numbers are recorded).

## End-of-session update template

Replace the fields below with **verified** values every session. Keep the entire handoff brief (target 1–2 pages); reference commits or dated records for detail.

- Timestamp (UTC and local time):
- Current branch, HEAD SHA, `git status` summary:
- Stage and mode (`synthetic` / `approved live`):
- Implemented paths and behavior:
- Commands actually run and exact pass/fail/skip results:
- Source repo branch/SHA inspected and paths (if any):
- New/changed design decisions (link `docs/DECISIONS.md`):
- Security/privacy issues and remediation owner:
- Uncommitted work, blockers and unknowns:
- Required named human decisions:
- Next three ordered, runnable tasks:
- Suggested first prompt for next Claude Code session:

**Session hygiene:** Never silently overwrite failing tests, conflate fixtures with live integration, or push/PR without the Admin authorizing the exact target and change. A handoff update is a local documentation edit; publication to GitHub follows the normal review workflow.
