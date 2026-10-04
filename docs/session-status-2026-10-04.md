# Research session status — 2026-10-04

Living resume point for this session; update it at each checkpoint. The
[2026-10-03 status](session-status-2026-10-03.md) keeps the completed evidence,
closed alternatives and the original next-session plan.

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

## Serving state at this checkpoint

The original IQ3 `ownervision` container launched for this baseline is still
running on Ulmus loopback port 19623. It is the same profile the OpenCode
launcher uses, and the launcher reuses it. Stop it with `bash stop.sh` when
the GPU is needed or the session ends.

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

## In progress: `--short-read` break-even probe

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

## Planned: second R&D machine

Owner request: later test this stack on an i7-6900K / X99 machine with three
RTX 3090 (PCIe 3.0 x16, x16, x8) and 96 GB DDR4. Porting gaps and inferences are
in the Ulmus skill's `model-experiments.md`; nothing is probed yet.

## Next options

From the 2026-10-03 plan and the annotated review, in recommended order:

1. Matched text/vision A/B, ABAB with identical prompts, logging expert-cache
   size: is the ~12% unmatched gap real and does it justify vision-lifetime work?
2. Real-workload decomposition on owner-approved OpenCode sessions: prefill,
   prefix reuse and >32K paging versus decode share of wall time.
3. Time-boxed critical-path trace (about 300 speculative windows), no sweeps.

ExLlamaV3/TabbyAPI, c2, 397B and DeepSeek 4.1 Flash remain later experiments.
