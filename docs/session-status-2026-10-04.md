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

## Next options

From the 2026-10-03 plan and the annotated review, in recommended order:

1. Matched text/vision A/B, ABAB with identical prompts, logging expert-cache
   size: is the ~12% unmatched gap real and does it justify vision-lifetime work?
2. Real-workload decomposition on owner-approved OpenCode sessions: prefill,
   prefix reuse and >32K paging versus decode share of wall time.
3. Time-boxed critical-path trace (about 300 speculative windows), no sweeps.

ExLlamaV3/TabbyAPI, c2, 397B and DeepSeek 4.1 Flash remain later experiments.
