# Research session status — 2026-10-04

> Later owner-authorized exploration supersedes the pause state below. Read the
> [live exploration checkpoint](exploration-2026-10-04.md) first for in-flight work,
> result markers and the selected serving state.

Living resume point for this session; update it at each checkpoint. The
[2026-10-03 status](session-status-2026-10-03.md) keeps the completed evidence,
closed alternatives and the original next-session plan.

## Current checkpoint — 2026-10-04, about 13:15 local (read this first)

**Stop here at Julien's request so another agent can advise.** The complete
[handoff](handoff-2026-10-04.md) records the decision, compromises, evidence,
resource snapshot, closed dead ends and ideas left for review. Research is not
declared exhausted. No controller/evaluator remains running; one target stays
loaded for OpenCode.

**Selected and observed serving:** `flash-iq3s-256k-vision-tune-ownerswap`, v4
`ulmus/strata:99f3dbd-lendvram` (`24386fa3fb0e…`), healthy on loopback 19623,
262144 backend context, 253952 OpenCode window, low default. Driver R550 and
280 W policy unchanged; experts and PLE/ngrams in RAM. The launcher uses this
profile and returns `READY` naturally at low. The original 27B remains stopped.

**Qualification complete:** practical30 low 29/30, all natural with valid
controls (resident low seeds 28/29/30); exact original-request replay +6.17%;
matched 64K 110.0 vs 103.05 tok/s (+6.74%, non-overlapping launch ranges);
single 128K pair 104.5 vs 99.7 (+4.81%, small regression screen). All API checks
pass; all paired input hashes match. The separate changed-prefix screen is
still −2.07%, so the gain is not uniform.

**Accepted cost:** new-image TTFT +93 ms median, worst matched pair +118 ms;
cached images bypass staging. All sixty deck answers finish naturally with
equal 14/15 content; all swap operations succeed. On the selected instance,
two new maximum-budget images and a cached repeat also pass with 1/0/1
LEND/RECLAIM pairs. No model reload is needed for vision.

Loaded snapshot: 23.44 GiB VRAM, about 81.1 GiB engine/vision proportional host
RAM, 102.7 GiB host available. The cgroup 54.3 GiB counter does not include
every already-resident file page used by the processes. Idle CPU 0.24%; no new
active-CPU breakdown. Full 32K–256K remains relevant; 192K/256K v4 throughput
is unmeasured, no fresh 250K prefill was run, and no context limit was reduced.

All work since 5ac7889 remains local, uncommitted and unpushed; index untouched.
Upstream request unposted. Commit/push only when Julien asks. The Ulmus skill
reference and README include this checkpoint. Earlier closures below are
historical and superseded by this decision.

## Earlier handoff and continuation — about 12:10 local (historical)

**Final-checkpoint owner steering.** Stop at the next complete, documented
checkpoint so another agent can advise; do not start a new optimization line.
The entire 32K/64K/96K/128K/192K/256K range is relevant. Do not assume that
64K is the owner's typical context. Finish the current 64K A/B and use the
existing 32K–128K trend plus one fresh resident/swap 128K pair (three samples
each, same existing questions). Register before launch: requests/API checks
must match/pass and candidate median decode must not regress more than 5%.
This single pair is a regression screen, not proof of a repeatable gain.
No new 250K prefill is planned: context capacity and measured decode performance
are separate, and an estimate beyond measured sizes must be labelled as such.

**Owner steering after the first continuation: optimization remains active.**
The owner explicitly rejects trading away a repeatable +6% decode benefit just
because a new, uncached image costs about 100 ms more. The 100 ms engineering
target is superseded for selection; safety, natural completion, image quality,
one resident model and no minute-scale surprises remain requirements. Keeping
resident vision selected while investigating is a deployment decision, not a
reason to stop the overall optimization task. The earlier closure below is
superseded by this owner direction.

**Bounded diagnostic, fixed before launch.** Six fresh launches in order
resident / v3 / v4 / v4 / v3 / resident, with the original `swap-ab-v1` request
prefix, low/seed 42, three warmups, six 512-token decode cells and two uncached
32K prefills per launch. No new image build or sweep. All request hashes must
match the original screen. This isolates build changes from the changed
benchmark prefix; it does not establish broad performance parity by itself.
Evaluate each build against both resident controls (median of launch medians,
range overlap, acceptance, cache hits and API checks). A repeatable gain with
roughly 0.1 s per new image is an acceptable owner trade-off. If the original
gain fails to repeat, retain resident serving and continue with a concrete
decode-path hypothesis rather than declaring the whole task complete.
Runner: `scripts/run_swap_prefix_control_chain.sh`; selected resident vision
is restored on exit. Current results go to `swap-prefix-control-*`.

**Controlled replay complete.** All six launches finish, API 9/9 throughout,
and every request hash matches the original screen. Resident controls
100.95/104.05 tok/s (median 102.50); v3 108.50/108.15 (108.325, **+5.68%**);
v4 108.80/108.85 (108.825, **+6.17%**). Both candidate ranges lie above the
resident range. V3 and v4 produce identical completions in all twelve paired
decode cells, with equal aggregate cache hits and draft acceptance; the native
binaries differ. The earlier v4 rejection was too broad: the gain repeats on
the original inputs, while its behavior on the newer prefix remains a separate
negative result. [Replay evidence](../results/public/swap-prefix-control-comparison.json).

**Decision and next bounded qualification.** Prefer v4 over v3: same repeated
decode gain, lower measured new-image overhead (+93 vs +103 ms). The owner
accepts that one-time cost for an uncached image; cached images bypass staging.
Do not claim +6% uniformly, since the newer-prefix screen is −2.1%.
Before switching the OpenCode serving profile, run the frozen thirty DevOps
canaries at low/seed 42 with the same 32768 natural-completion guard, then four
fresh 64K-context launches S V V S using the existing three questions. Written
before launch: all thirty canaries must finish naturally with valid controls,
score at least 28/30 (inside the original 28–30 seed range), all API checks must
pass, request hashes must match across the 64K cells, and the candidate must
not regress their median decode by more than 5%. These qualify this unchanged
IQ3 runtime for a trial; they do not establish full-size or universal parity.
Runner: `scripts/run_swap_qualification_chain.sh`, restoring resident vision on
exit. The 64K check measures the cache/vision lifetime change on the owner's
common context sizes; it does not reopen the closed KV-window sweep.

**Continuation completed after the handoff.** The v4 deck S V V S is complete, exit 0,
and `ownervision` was restored. Median paired image first-token increase
**93.03 ms**; maximum per-case median 109.51 ms; worst individual paired
increase **117.95 ms**. All 60 responses finished naturally, with 14/15 strict
content on every launch. All 60 LEND/RECLAIM operations succeed, with no CUDA
error. Criterion (3) passes. The final matched decode chain V S S V
(`swap4-residency-*`, paired ID `swap-ab-v4`) also finished, exit 0, with 9/9
API checks on all four launches. It restored `ownervision`; both detached chains
are finished. The live probe confirms original owner-API image, loaded model,
vision, 262144-token capacity, R550 and 280 W.
The normal private OpenCode launcher then returned exactly `READY` at low,
exit 0, on the selected resident profile; its temporary tunnel closed normally.

| Final v4 check | Resident GPU vision | Swap v4 |
|---|---:|---:|
| Per-launch decode medians, tok/s | 108.20 / 106.45 | 105.25 / 104.95 |
| Median of launch medians | **107.325** | **105.10 (−2.07%)** |
| Expert-cache slots | 7605 | 8379 |
| Decode expert-cache hit rate | 86.0% | 87.8% |
| Short-prompt first token | 0.595 s | 0.547 s |
| Uncached 32K prefill | 4739 tok/s | 4763 tok/s |

The launch ranges do not overlap. **Criterion (1) fails; (2), (3) and (4)
pass. Do not adopt: the prototype is closed and `ownervision` remains selected.**
No OpenCode profile change, additional build or optimization run is scheduled.
The two proposed follow-up levers are retained as ideas, not next tasks.
[Final matched evidence](../results/public/swap-ab-v4-comparison.json),
[image evidence](../results/public/swap-deck-partial-comparison.json).

Within this final check, request hashes, weights, sampler, tokenizer, MTP,
projector and engine arguments (apart from the lend option) match. The original
v1 check used `swap-ab-v1`, while this check uses `swap-ab-v4`; `bench.py` puts
that ID in the system message, so their request hashes differ despite equal
prompt lengths. The change from +6.1% to −2.1% must not be attributed solely to
the v4 code. The benefit did not survive a second matched request set, which
is sufficient to reject adoption under the written rule; it does not establish
a universal slowdown or identify its cause.

V4 actually lends 1408 MiB on the first new image and 1600 MiB on the other
fourteen in each launch: partial lending helps only once here, not the predicted
per-image saving. Median LEND 27.0 ms, RECLAIM 82.6 ms (17.6–17.7 ms remapping,
65.0 ms refill/read-back). The summarizer now accepts both the legacy log and
v4's added MiB field, rejects incomplete/capped decks and mismatched image
inputs, and records the worst individual pair as well as per-case medians.
Its corrected deployment copy is synchronized after the measurement chains.

The following is the preserved handoff snapshot; completed deck steps must not
be rerun just because they remain in that original sequence.

Paused by the owner mid-iteration. Nothing is running on Ulmus except the
selected serving profile.

**Live state at pause (observed).** Container `ulmus-inference-test`, image
`ulmus/strata:99f3dbd-ownerapi`, profile `flash-iq3s-256k-vision-tune-ownervision`,
loopback port 19623, 280 W limit. This is still the selected OpenCode profile.
The swap prototype is **not** deployed for serving and must not be without the
adoption rule below or the owner's explicit acceptance.

**Goal in progress.** A local engine change that lets GPU vision stop costing
decode speed: the encoder frees its weights and work buffers between new
images; the engine's expert cache uses that VRAM and lends a tail of it back
per new image. Design, rule and evidence: "Afternoon resume" below.

| Build (Ulmus image tag) | Change | Image first token vs resident, median (max) |
|---|---|---:|
| `…lendvram-v1` `0e968245675c` | prototype, LOAD reads the GGUF | +195 ms (+200) |
| `…lendvram-v2` `b63fd86a2982` | pinned host copy of the projector | +111 ms (+118) |
| `…lendvram-v3` `3e3faafd24d3` | async upload from the pinned copy | **+103 ms (+108)** |
| `…lendvram` = v4 `24386fa3fb0e` | lends only what the encoder lacks | **+93 ms median; +118 ms worst individual pair**; final decode −2.1%, rejected |

Matched decode (v1 engine; v2–v4 change only vision loading and lend sizing):
**107.15 vs 101.0 tok/s (+6.1%)**, ranges non-overlapping, 9/9 API checks per
launch, deck content equal (14/14 each, strict scorer), 120 of 120 LEND/RECLAIM
succeed. Adoption rule criteria 1, 2 and 4 pass; criterion 3 (median image delta
≤ 100 ms, none above +250 ms) fails narrowly at v3.

v3 per-image costs (engine log): LEND 0.9 ms; encoder LOAD 72–77 ms, of which
pinned upload 34 ms (PCIe line rate) and about 38 ms mtmd/clip init; UNLOAD 1–7 ms;
RECLAIM 86 ms = 16–23 ms `cuMemCreate` of 1.57 GiB plus 64 ms refilling 812 slots
(PCIe-bound). The faster prompt read with the larger cache offsets about 55 ms.

**v4 (untested) change.** The tail is mapped as 64 MiB chunks. `LEND <MiB>`
makes the engine read `cudaMemGetInfo` and lend only `need − (free − 256 MiB)`,
in whole chunks from the end; `need` = the encoder's measured release + 64 MiB
(1574 MiB here). The engine idles while lent, so its own free VRAM (about
676 MiB at steady state, observed on v1) counts. Expected: about 1.2 GiB lent
instead of 1.57, about 25 ms less per image. The server also retries a failed
RECLAIM five times at 200 ms.

**Next steps, in order:**

1. On Ulmus, in the deployed stack directory (`ULMUS_REMOTE_ROOT` in the private launcher):
   `setsid nohup bash -c 'bash scripts/run_swap_deck_chain.sh partial; echo $? > results/swap-deck-partial.done' > results/swap-deck-partial.log 2>&1 < /dev/null &`
   (about 10 minutes; fresh launches S V V S; it serves `ownervision` again at the end, also on failure).
2. Copy `results/vision15-partial-*` back and run
   `python3 scripts/summarize_swap_ab.py --decks results/vision15-partial-{1-swap,2-gpuvision,3-gpuvision,4-swap}.json --out results/swap-deck-partial-comparison.json`.
   Check the engine logs: `LEND done, <MiB> MiB` should be below 1574, with no `FAILED`.
3. If the median is ≤ 100 ms and no image exceeds +250 ms: run one final
   matched decode check on the v4 image (`bash scripts/run_ab_cells.sh swap-ab-v4 swap4-residency flash-iq3s-256k-vision-tune-ownervision flash-iq3s-256k-vision-tune-ownerswap flash-iq3s-256k-vision-tune-ownerswap flash-iq3s-256k-vision-tune-ownervision`, detached, then relaunch `ownervision`,
   then `summarize_swap_ab.py` with those cells and the partial decks), then
   adopt: OpenCode launcher and docs move to `…-ownerswap`, and the image is
   recorded in `docs/architecture.md`.
4. If it is still above 100 ms, stop optimizing and ask the owner: +6.1%
   decode on all text against about +0.1 s per new image (cached images cost
   nothing). Remaining levers, not built: keep the mtmd context and recreate
   only GPU resources (about −20–30 ms); defer the tail refill to the
   adaptive tier by treating empty slots as swap victims (about −40–60 ms, hot-path change).

**Code locations.**
- Canonical patches here: `patches/ulmus-lend-vram.patch` (engine cache VMM tail,
  `--lend-vram-mib`, `LEND`/`RECLAIM`, `strata-vision` `UNLOAD`/`LOAD`/`--host-copy`,
  server swap mode and tests) and `patches/llama-mtmd-host-copy.patch` (pinned
  projector copy, mtmd `keep_host_copy`). `Dockerfile.lend-vram` applies both to
  `ulmus/strata:99f3dbd-ownerapi` and rebuilds only `strata` and `strata-vision`.
- The working tree of the engine patch is the local clone
  `upstream/strata-v0.1.38` (branch `ulmus-lend-vram`, uncommitted, gitignored).
  The mtmd sources are in `/tmp/llref` (temporary; regenerate from the patch if gone).
- The deployed Ulmus copies of the patches, Dockerfile, run.sh, profiles and
  scripts match the canonical files (patch SHA-256 checked at the pause).
- Unit tests: `python -m unittest serve.test_server` in the clone (120 pass, needs `requirements.txt`).

**Pitfalls seen this session.**
- Run Ulmus chains detached (`setsid nohup … &`) and check them with short SSH
  calls; long foreground SSH calls hit the 2-minute tool timeout.
- `scp … results/` copies into the current shell directory: use absolute paths.
- Never build images during a measurement chain: compilation competes with the CPU expert pool.
- `owner_api_check.py --vision` checks status only and sends no image; use
  `scripts/swap_image_smoke.py` or the deck to exercise LEND/RECLAIM.
- New Dockerfiles must be whitelisted in `.gitignore` and their inputs in `.dockerignore`.

**Uncommitted and unpublished.** Everything since commit `5ac7889` (this
afternoon's scripts, patches, profiles, results and these notes) is local and
uncommitted. Nothing was pushed; the upstream feature request stays unposted
(owner approval required). The upstream `server.py`/engine changes are a candidate
upstream contribution only after adoption and owner approval.

## Live state at resume

Ulmus had just booted (08:34 local), idle: 2 MiB GPU, unchanged 280 W limit,
R550 driver, no containers or listeners. The 2026-10-03 OpenCode serving
container did not survive the power-off; no automatic startup exists.

## Owner real-work observation

After the 2026-10-03 night pause, Julien used the original IQ3 vision profile
through OpenCode for real code and maintenance work. The reviewing Claude session
judged the result solid senior-level work and requested no changes. This is
owner-reported, qualitative evidence from one session; the reasoning variant is
not recorded. It supports keeping original IQ3 selected; it is not a benchmark.

## Runtime fingerprint correction

After the reboot, the unchanged `ownervision` runtime no longer matched its
seed-42 fingerprint. The only difference was the overlayfs device number of the
image-layer `expert-profile.bin`; its SHA-256, size, mtime and inode were equal.
`scripts/evaluation_provenance.py` now identifies content-hashed files by path,
size and hash, and `require_matching` recomputes the stored identity's fingerprint.
Large weights keep device/inode/size/mtime identity. Tests cover both a tolerated
overlay change and rejected content or weight changes. Under the corrected
definition, all original-IQ3 v2 runs share `4f16d67202df`; head-only and Q4
remain distinct. The deployed Ulmus copy is updated only between evaluation batches.

## Completed: original IQ3 seed-variance baseline

Same `ownervision` profile, stable runtime fingerprint, deck, grader and
32768-token runaway guard as the seed-42 baseline. All 180 generations stop
naturally; every grader control passes.

| Original IQ3 | Seed 42 | Seed 7 | Seed 123 | Pooled | Cases changing verdict |
|---|---:|---:|---:|---:|---|
| Low | 28 | 29 | 30 | 87/90 | `environment-expansion`, `literal-endpoint`, `retry-after` |
| Off | 29 | 28 | 28 | 85/90 | `environment-expansion`, `idempotency-conflicts`, `json-pointer`, `path-route` |

No case fails under every seed. Median answer time: low 9.12/9.83/9.45 s,
off 3.40/3.86/3.54 s. Low seed 123's `backoff` answer finished naturally after
10,037 tokens and 107 s, above the 8192-token default output budget used by
OpenCode; one of ninety low generations here.

## Decisions

- Pre-registered rule, fixed before seed 123 completed: three or more verdict
  changes within one effort mean this deck cannot select precision variants.
  Low has three, off four. The head-only 29/30 lies inside 28–30, and original
  IQ3 passes both cases it "fixed" at other seeds. **Dense-precision line
  closed:** head-only and embedding-plus-head are not pursued without new
  evidence. The standalone embedding artifact and its profile are retained.
- **Low remains the default.** Off was not at least as good as low across
  seeds (28 vs 29 and 28 vs 30), and pooled 85 vs 87 is unresolvable. Off is a
  faster variant (about 2.6× shorter median answer time), not a demonstrated
  quality equal or superior for all work.
- The README worker-scaling paragraph written late on 2026-10-03 cited single
  requests as medians. Corrected to the recorded medians: 104.15 tok/s with 6
  workers and 107.1 with 11 at the PCIe .2 / min-p .5 placement.

## Serving state

Every experiment chain stops its own launches. The last chain relaunched the
selected original IQ3 `ownervision` profile, which stays loaded on Ulmus loopback
port 19623 as the single resident model; the OpenCode launcher reuses it. The
context-decode probe ran on it afterwards. Stop it with `bash stop.sh` only when
the GPU is needed or Ulmus is shut down.

## Completed: matched text/vision decode A/B

Checkpoint `c437cbb` (seed baseline, fingerprint fix) is pushed. Six fresh
launches, order T V V T T V, all 9/9 API checks, identical request hashes:

| | Text-only | GPU vision |
|---|---:|---:|
| Expert-cache slots | 8606 (16.32 GiB) | 7603–7605 (14.42 GiB) |
| Decode hit rate, median of launches | 91.0% | 87.3% |
| Per-launch decode medians, tok/s | 116.85 / 112.45 / 114.85 | 104.25 / 106.45 / 104.25 |
| Median of launch medians | **114.85** | **104.25 (−9.2%)** |
| Uncached ~32K prefill | 4799 tok/s | 4737 tok/s |
| Short-prompt first token | 0.53 s | 0.59 s |

Ranges do not overlap. Under the rule below, 9.2% permits one design memo and
one time-boxed prototype. Existing evidence for the memo: a CPU-vision launch on
2026-10-03 got 8604 slots, matching text-only, but used a 1024-token image budget
with no warm-up; its one image canary failed a strict exact-reply check. CPU
vision at the selected 4096 budget has no measured accuracy or image latency.
The pre-registered rejection bound (image first-token latency +100 ms) was written
for a GPU cache-refit prototype; CPU vision would almost certainly exceed it, so
choosing it would be an owner trade-off of image latency against ~9% decode.
[Evidence](../results/public/vision-residency-comparison.json)

Protocol: original IQ3 `ownertext` versus `ownervision`, fresh launch per cell in
counterbalanced order T V V T T V. Each cell runs the paired `bench.py`
protocol first (three warmups, six 512-token low decode cells, two uncached
~32K prefills, seed 42, paired ID `vision-residency-v1`), then the API checks,
then stops. Per-cell engine-log slices give cache allocation and per-request
decode hit rates. Runner: `scripts/run_ab_cells.sh`; summary:
`scripts/summarize_vision_residency.py`.

Decision rule, fixed before the first cell: compare the median of per-launch
decode medians. A gap below 5%, or overlapping per-launch ranges, closes
vision-lifetime redesign. A gap of 8% or more permits one design memo and one
time-boxed prototype, rejected if image first-token latency rises by more than
about 100 ms or any graph/pointer instability appears; never per-image reload.
Between 5% and 8%: record it and defer behind workload decomposition.

If interrupted: completed cells are `results/vision-residency-*-{perf,api}.json`
and `-engine.log` on Ulmus; rerun only missing cells, each from a fresh launch.

## Real-workload engine decomposition (owner's 2026-10-03 OpenCode session)

The engine log of the night serving launch holds per-request metadata only:
prompt/reused/read tokens, prefill and decode times, hit rates. No prompt or
response text and no per-request timestamps; it excludes tool and user time and
includes the short READY check. The private copy is
`results/opencode-serving-2026-10-03-engine.log`; only aggregates are published.

- 355 requests, 20.4 min engine time: **decode 70.3%, prefill 29.7%**.
- Prefix reuse **97.0%** of 19.6M prompt tokens. Prompt median 51K, p90 97K,
  max 111K tokens: real sessions routinely exceed the 32K resident KV window.
- Generated tokens median 150, p90 466: many short agent turns.
- **Short increments dominate prefill time.** 327 requests reading under 2000
  fresh tokens (median 113) took 229.5 s, a 679 ms median: about 19% of engine
  time. Cost scales with fresh tokens (0–50: 220 ms; 50–200: 632 ms; 500–2000:
  1382 ms), barely with context (about 0.8 ms per 1K). Small reads run near
  150–250 tok/s versus about 4.7K tok/s for large prompts.
- Decode by context band, confounded by content and answer length: 122.0 tok/s
  at 16–32K, 112.7 at 32–64K, 101.5 at 64–128K; KV VRAM hit rate stays 98–99%.

Against the review's stop rule (decode >70%, reuse >90%, 64K within ~10% of
32K), decode share and reuse barely pass and the band slowdown exceeds 10%, so
prefill/paging work stays open.

Source check of pinned Strata `99f3dbd`: the logged prompt time spans lending
cache slots, reading and refilling them. Upstream's own comment prices the batched
path at ~300 ms per run (it streams every routed non-resident expert over PCIe)
plus ~180 ms refill, versus "~16 ms a token" for verify windows. Reads of at most
`--short-read N` fresh text tokens (default 64, documented CLI option) take the
windows. On this host decode windows run near 3–4 ms per token, so the break-even
may sit well above 64; the measured median increment is 113 tokens.

## Owner constraint, 2026-10-04

Keep **one** model loaded. No profile switching and no surprise latency on the
order of a minute: a text-default/vision-on-demand split is excluded. Vision
choices are limited to what one resident profile can serve.

## Completed: `--short-read` break-even probe

`scripts/short_read_probe.py` builds an agent-like chain on a ~64K-token document:
each turn adds a fixed short assistant reply and a tool message of 1–48 lines,
seeded order, three repeats. Profiles `…-tune-ownersr0` (always batched) and
`…-tune-ownersr4096` (always windows) differ from `ownervision` only by
`--short-read`; launch order sr0, sr4096, sr4096, sr0.

Decision rule, fixed before the first launch: the threshold is the largest
fresh-token size at which the windows median prompt time is below the batched
median in both launches of each. Adopt it in the owner profiles only if it cuts
median prompt time by 20% or more for reads between 65 tokens and the threshold,
keeps 9/9 API checks, and the thirty canaries at low finish naturally at 28/30 or
better (inside the measured seed range). Otherwise keep the default 64.

Result, launch medians within about 1% of each other:

| Fresh tokens | 27 | 41 | 69 | 97 | 124 | 234 | 453 | 676 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Batched, ms | 472 | 522 | 626 | 722 | 766 | 904 | 1028 | 1111 |
| Windows, ms | 238 | 308 | 492 | 801 | 1093 | 2225 | 4014 | 7285 |

Windows win up to 69 tokens and lose from 97; linear interpolation puts the
break-even near 87 tokens at 64K context. Windows read at about decode speed
(9–11 ms per token here), so the hypothesis of a much higher break-even is
refuted. The 20% condition holds only at the 65–69-token edge, and it is
necessary, not sufficient. Projected on the real session, 40 of 344 resumed
requests fall in 65–87 tokens: about 4.7 s of 1225 s engine time (0.38%).
**Decision: keep upstream's default 64; the knob is closed.**

The remaining floor is structural: about 450 ms per batched read (expert
streaming plus slot refill), paid by 213 of 344 real requests. Inference, not
measured: `--no-prefill-borrow` removes the refill but permanently shrinks the
expert cache and caps chunks at 2048, likely costing more decode and large-read
prefill than it saves. Lowering the floor needs upstream engine design.
[Evidence](../results/public/short-read-comparison.json)

## Completed: CPU vision at 4096 image tokens (the permitted prototype) — rejected

- Decode, matched T C C T: CPU vision keeps 8604 slots (text 8606) but runs
  **113.4 vs 117.3 tok/s (−3.3%)**, hit rate 89.5 vs 90.7%; ranges do not overlap.
  The vision-enabled engine path costs something beyond VRAM; not identified.
  Against this morning's GPU vision median (104.25, another chain) it is about 9% faster.
- **Image latency**, 15-image deck at low, run back to back the same morning:
  CPU vision first token **35.5 s median, 49.4 s max**; GPU vision **1.57 s
  median, 1.81 s max**. Added latency per image: median +34 s, 11 of 15 above
  30 s. Content is 15/15 on both, so the cost is latency, not accuracy.
  [Decode](../results/public/cpuvision-residency-comparison.json),
  [deck](../results/public/vision15-cpu-gpu-20261004.json)
- Fails the pre-registered thresholds (decode within 3%: 3.3%; no image above
  30 s) and the owner's no-minute-scale-surprise constraint. **GPU vision stays;
  its ~9% decode cost is accepted.** Recovering it needs an upstream engine
  feature (resizing the expert cache when the vision worker is idle), not a local
  patch or a profile switch.

Setup record:

Profile `…-tune-ownercpuvision` differs from `ownervision` only by
`vision.gpu: false` (12 encoder threads, same 4096-token budget). One detached
chain: matched decode cells T C C T (`cpuvision-residency-*`, same paired
requests), then the 15-image deck at low on CPU vision, then the same deck on
GPU vision. The chain ends with `ownervision` loaded for serving.

Recommendation thresholds, fixed before launch; the choice remains the owner's:
recommend CPU vision only if its decode is within 3% of text-only, its median
per-image first token rises by at most 5 s over GPU vision with no image above
30 s, and its deck content score is at most one image below GPU vision's.

## Completed: fixed-length decode at 32K, 64K and 128K

`scripts/context_decode_probe.py` on the loaded `ownervision` profile: document
fixtures of each size plus one of three questions, 512-token low generations,
order 32/64/128/128/64/32/32/64/128. Rule, fixed before running: if the 64K
median decode is within 10% of 32K, close long-context paging work. If not, the
next candidate is the supported `--kv-resident` window, a VRAM trade against
expert-cache slots that needs its own matched A/B.

| Context (prompt tokens) | Decode tok/s, three questions | Median | Draft acceptance | Board power |
|---|---|---:|---:|---:|
| 32K (31803) | 105.7 / 110.5 / 111.3 | 110.5 | 76.1% | 246–250 W |
| 64K (64571) | 115.6 / 104.4 / 102.3 | 104.4 (−5.5%) | 72.1% | 268–270 W |
| 128K (130107) | 106.2 / 103.4 / 99.6 | 103.4 (−6.4%) | 74.6% | 241–275 W |

All nine cells stop at exactly 512 tokens. **Long-context paging work is closed**:
64K is within 10% of 32K. The 17% band slowdown in the real session was mostly
content and answer-length confounding. Per-question spread (about ±6%) exceeds
the context effect, so the medians are indicative. Observation, not a cause:
board power approaches the 280 W limit at 64K and above.
[Evidence](../results/public/context-decode-20261004.json)

## Planned: second R&D machine

Owner request: later test this stack on an i7-6900K / X99 machine with three
RTX 3090 (PCIe 3.0 x16, x16, x8) and 96 GB DDR4. Porting gaps and inferences are
in the Ulmus skill's `model-experiments.md`; nothing is probed yet.

## Afternoon prototype (completed; rejected on final decode)

Direction, from the owner's 2026-10-03 brief ("build our own stack… juice our
hardware"): pursue the remaining engine-level gains in our pinned build rather
than only filing upstream requests. The GitHub issue stays unposted until the
owner approves it. Upstream main is still the pinned v0.1.38 (`99f3dbd`).
`run.sh` accepts `ULMUS_TRACE=1` (engine `STRATA_TRACE`) for decomposition runs.

**Short-read floor decomposed, local refill work closed.** One traced launch of
`ownervision`, the same chained 64K probe, 21 batched turns
(`scripts/run_trace_chain.sh`, `scripts/summarize_short_read_trace.py`):

| Fresh tokens (median) | 97 | 124 | 234 | 453 | 676 |
|---|---:|---:|---:|---:|---:|
| Prompt time, ms | 589 | 641 | 771 | 898 | 985 |
| Batched read, ms | 515 | 562 | 694 | 812 | 908 |
| Slot refill, ms (slots) | 25 (316) | 25 (316) | 25 (316) | 28 (360) | 31 (399) |
| Header windows (6 tokens), ms | 30 | 33 | 34 | 27 | 38 |
| Lend + other (checkpoint, API), ms | 19 | 20 | 19 | 19 | 18 |

Upstream's "~180 ms refill" comment does not hold here: refill is 25–31 ms. The
floor is the batched read itself (about 470 ms intercept plus about 0.65 ms per
token), i.e. streaming the routed non-resident experts. An async refill would
save about 0.4% of real engine time: not pursued. Lowering the streaming floor
needs a hybrid CPU/GPU small-chunk prompt path, a large engine project worth an
estimated ~3% of engine time: deferred, not scheduled.

**Vision encoder VRAM breakdown** (`scripts/vision_memory_probe.py`, idle GPU,
fresh container): bare CUDA context 390 MiB (58 ms); `strata-vision` resident
1946 MiB, so about 865 MiB BF16 weights and about 690 MiB work buffers and pools;
start to READY 2.36 s including a 1.85 s warm-up encode at 4096 tokens. Encodes:
4096 tokens 1.85 s, screenshots of 850–1035 tokens 125–174 ms, 256 tokens 26 ms.
Per-image process restart is therefore excluded. Host-resident weights with
ggml's op offload would not save VRAM: the pinned scheduler allocates every split
input copy as a never-overwritten graph input, so the copies would coexist.
In progress: in-process UNLOAD/LOAD cost (`patches/strata-vision-unload-load.patch`,
measurement image `ulmus/strata:99f3dbd-visionunload`), which decides whether an
engine-side releasable cache tail is worth building.

**In-process UNLOAD/LOAD measured** (`results/vision-reload-r20261004.json`, four
cycles): UNLOAD 6–7 ms frees about 1510 MiB (440 MiB context stays); LOAD 124–128
ms (GGUF from page cache plus pageable upload); the first encode after LOAD has
no penalty (154–166 vs 162–171 ms). VRAM after LOAD is 1310 MiB, 1484 after a
1035-token image and 1954 after a 4096-token image.

**Design memo: lend the expert cache's tail to the encoder per new image.**
This is the review's permitted "cache refit on image arrival with stable
pointers/graphs" prototype. It does not restart or re-sample anything per image;
images already encoded stay cached by hash and cost nothing. "Never per-image
reload" is read as no process restart and no profile switch; reloading the
encoder's weights per new image is the owner-endorsed 27B design (49 ms staging).

- Engine (`patches/ulmus-lend-vram.patch`, image `ulmus/strata:99f3dbd-lendvram`):
  `--lend-vram-mib N` reserves the expert-cache arena as one CUDA VMM range with
  two physical allocations; the last N MiB are lendable. Slot addresses and every
  captured graph stay valid. Serve commands between requests: `LEND` waits for
  adaptive swaps and the device, marks the tail's experts non-resident, uploads
  the residency table and unmaps/frees the tail; `RECLAIM` maps it again, refills
  those experts from their host blobs, verifies the first and last slot by
  read-back and restores residency. A request arriving while lent is refused.
- `strata-vision`: `UNLOAD` (reports freed MiB) and `LOAD`.
- Server swap mode (`"vision": {"swap": true}`): at start the encoder warms up at
  the largest picture, unloads, and its freed MiB + 64 sizes `--lend-vram-mib`; the
  engine then sizes its cache with that VRAM free. New images in a request are
  encoded inside one `LEND`, `LOAD`, encodes, `UNLOAD`, `RECLAIM`, under the request
  FIFO; a failed load still reclaims. Vision restart in swap mode stops the engine
  first. Upstream server tests 118/118 plus 2 new swap tests pass.
- Profile `flash-iq3s-256k-vision-tune-ownerswap` = `ownervision` + `swap: true`.
- Expected: about 775 more cache slots; per new image roughly LEND ~5 ms + LOAD
  125 ms + UNLOAD 7 ms + RECLAIM ~60 ms. LOAD can drop to ~40 ms with pinned
  staging if the latency bound requires it.

Pre-registered adoption rule, fixed before the first matched cell: matched cells
V S S V V S (`ownervision` vs `ownerswap`, paired `bench.py`, API checks with
images). Adopt swap as the owner vision profile only if (1) the median of
per-launch decode medians is at least 5% above V with non-overlapping ranges;
(2) every API check passes and every LEND/RECLAIM in the engine logs succeeds
with verified read-back and no CUDA error; (3) on the 15-image deck at low, run
S V V S on fresh launches, the median paired first-token increase is at most
100 ms and no image rises by more than 250 ms; (4) deck content equals V's.
If (3) fails only on latency, the next step is pinned LOAD staging, then a rerun
of (3); otherwise the prototype is rejected and recorded.

**Matched A/B result, prototype v1** (`results/swap-ab-comparison.json`,
`scripts/summarize_swap_ab.py`; image `…lendvram-v1`, LOAD from the GGUF):

| | Resident GPU vision (V) | Swap prototype (S) |
|---|---:|---:|
| Expert-cache slots | 7603–7605 | 8381 |
| Per-launch decode medians, tok/s | 101.0 / 100.85 / 102.15 | 107.15 / 102.9 / 107.15 |
| Median of launch medians | **101.0** | **107.15 (+6.1%)** |
| Decode hit rate, median of launches | 84.4% | 87.5% |
| Short-prompt first token | 0.592 s | 0.548 s |
| 32K prefill | 4748 tok/s | 4755 tok/s |
| API checks | 9/9 ×3 | 9/9 ×3 |
| 15-image deck content (strict scorer) | 14, 14 | 14, 14 |
| Image first token, median paired delta | | **+195 ms** (max +200) |
| LEND / RECLAIM | | 60 of 60 succeed; 0.9 ms / 86 ms, 812 slots |

(1), (2) and (4) pass; (3) fails on latency only, so the pre-registered next
step applies: pinned LOAD staging (`patches/llama-mtmd-host-copy.patch`, mtmd
`keep_host_copy`, `strata-vision --host-copy`, image v2), then rerun (3). If
the median remains above 100 ms, RECLAIM (86 ms) is the remaining target.
Reproducibility is the same on both sides: two of three launches per profile
produce byte-identical decode outputs, and one launch per profile diverges.

**Latency reruns of criterion (3)** (deck S V V S on fresh launches, deck-only
summaries `results/swap-deck-pinned-comparison.json` and
`results/swap-deck-async-comparison.json`): v2 pinned host copy +111 ms median
(max +118); v3 asynchronous upload +103 ms (max +108). Content 14/14 on all
eight decks; 60 of 60 LEND/RECLAIM succeed per build. V4 passes latency (+93 ms)
but fails the final decode check (−2.1%); the prototype is closed. See the
continuation at the top for the complete evidence and request-set caveat.

The unused steady-state VRAM after startup is 425 MiB with the default 700 MiB
`--vram-reserve-mib`; lowering it would add at most ~150 slots (≈1% decode,
below matched-A/B resolution). Recorded, not pursued alone.

## Next options

The matched A/B, real-session decomposition, short-read probe, CPU-vision
prototype, context-decode probe, short-read trace and lend-VRAM prototype are done.
The lend-VRAM prototype is closed; do not schedule more variants without new
evidence or the owner's explicit direction. Remaining options:

1. Optionally, an upstream feature request or contribution with the measured
   evidence. The short-read part is now known to be expert streaming, not refill.
   Outward-facing: owner approval first.
2. Time-boxed decode critical-path trace, only if a concrete hypothesis appears;
   light profiling suggests GPU progress dominates each window.

The second R&D machine, ExLlamaV3/TabbyAPI, c2, 397B and DeepSeek 4.1 Flash
remain later experiments.
