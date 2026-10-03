# Paused research status — 2026-10-03

Subsequent serving update: the owner requested OpenCode testing. The selected
original IQ3 vision profile was started, its 262144-token backend capacity was
checked and a real OpenCode request returned `READY`. Juniperus now exposes one
Ulmus Next-Flash model entry with 253952-token client context; the duplicate
answer-budget alias was removed. Optimization remains paused. Check live state
before resuming; the shutdown evidence below describes the earlier night pause.

Paused at the owner's request for the night. The owned experiment controller,
evaluator and `ulmus-inference-test` container are stopped. Live verification
after stopping shows **2 MiB GPU memory used**, the unchanged **280 W limit**,
and the original 27B vLLM container still stopped. No host shutdown was requested.

## Selected stack and decision

Retain pinned upstream Strata, complete **GSQ IQ3_S**, IQ4_NL PLE/ngrams in RAM,
original BF16 vision projector and verified MTP. The normal owner text/vision
profiles remain selected. Both provide 256K context capacity with 32K resident
int8 KV; the vision profile is already configured and checked in OpenCode.
Experimental dense-precision profiles have not replaced the client entries.

Published release benchmarks remain the full-size reference. Local Q4 is a
diagnostic, never an oracle. No local full-size or Q8 target reference inference
was run. The Q8 embedding/head below are small dense components of a mixed IQ3
experiment, not a Q8 model. Low/off remains the qualification policy.

## Completed evidence

| Complete local screen | Original IQ3 | Q4 diagnostic |
|---|---:|---:|
| 30 executable DevOps/Python canaries, low | 28/30; 9.12 s median answer | 30/30; 16.51 s |
| Same 30, off | 29/30; 3.40 s | 27/30; 6.60 s |
| Frozen 24 LiveCodeBench cases, off | 14/24; 13.83 s | 16/24; 40.42 s |

All generations in these rows stop naturally. Positive/negative grader controls
pass, and paired input hashes match. The canaries are bounded local functions,
not repository-scale agent qualification. The revised deck clarified interfaces
seen in a Q4 prototype, so it is not a blind preregistered benchmark.
[Canary evidence](../results/public/practical30-comparison.json)
[Coding evidence](../results/public/coding-checkpoint.json)

The 15 diverse vision images score IQ3 15/15 low and off, Luna low 14/15 and
Terra/Sol low 15/15 on content. The reviewed harder chart set scores IQ3 19/20
versus Terra/Sol 20/20; ordinary arithmetic is 5/5 each. These small sets do not
establish broad cloud-model parity. [Vision audit](vision-comparison.md)

Historical selected-profile speed is 110.8 tok/s text and 97.65 vision, with
uncached 32K prefill around 4.7–4.8K tok/s. The fresh paired precision control
measures **100.6 tok/s original vision IQ3**. These are distinct runs and cache
histories, not a demonstrated tuning gain or regression.

Loaded active vision IQ3 was measured at about **82.7 GiB container RAM**,
**23.45 GiB VRAM**, **103.7 GiB host RAM available** and **12 core equivalents**.
CPU occupancy includes polling/waits; it does not prove useful arithmetic
saturates every core. Q4 used about **103.6 GiB container RAM** and 23.44 GiB
VRAM, leaving about 78 GiB available. All experts and PLE already reside in RAM;
additional unused capacity does not remove bandwidth or compute constraints.

## Closed alternative: eddoursul native fork

| Matched 32K fixed-length decode | Upstream | Adapted fork |
|---|---:|---:|
| Q4, normal adaptation | 57.65 tok/s | 33.65 |
| IQ3, normal adaptation | 105.05 tok/s | 46.60 |
| Q4, adaptation disabled | 46.15 tok/s | 29.75 |

Component/API checks pass, but the fork loses every matched comparison.
**This path is closed: no further build, sweep or quality testing is scheduled.**
The unrun extra tuning profile was removed. Preserve the evidence; do not reopen
it without material new evidence or owner direction. The CUDA 12.4 adaptation
does not establish the author's newer-CUDA performance. Its older engine also
lacks the selected stack's KV paging. [Static control](../results/public/native-ab-q4-32k-static-comparison.json)

## Experimental precision result and unfinished work

The **head-only IQ3 + Q4-source Q8_0 output head** passes 9/9 API checks and
completes **29/30 low** in **9.45 s median**. It fixes both original IQ3 failures
(unbracketed IPv6 acceptance and Retry-After regex indices), but introduces a
zero-base backoff failure. Fresh matched decode is **100.3 versus 100.6 tok/s**,
so it has no demonstrated speed advantage. The head also serves MTP. It remains
unselected, and the published exact-GSQ quality scores do not certify this hybrid.
[Matched performance](../results/public/precision-iq3-head-comparison.json)

The embedding-plus-head variant initially failed startup because `--embd-gguf`
requires a standalone file rather than an individual split-model shard.
A supported one-tensor `strata-embd` file now exists: **675,430,400 bytes** of
Q4-source Q8_0 embedding copied without requantization, with matching source and
destination payload hashes. Its profile points to the standalone artifact.
**The corrected profile has not been launched or qualified.**
[Copy provenance](../results/public/dense-embedding-extraction.json)

A post-hoc five-function disagreement deck is frozen privately, derived unchanged
from the thirty cases: environment expansion, root routing, backoff, IPv6 endpoint
parsing and Retry-After. Planned low-mode seeds are 7 and 123. The original IQ3
seed-7 run saved **two naturally completed passing answers** before the owner
requested pause; the next backoff generation was interrupted. It has **no usable
five-case quality score**. Seed 123 and both precision variants' repetitions have
not started. Keep the partial capture; never call it 2/2 accuracy or reuse it for
another runtime. Resume only with the evaluator and exact runtime fingerprint
checked, or start a separately labelled fresh attempt.

Earlier low-mode coding and knowledge attempts reached output caps. They remain
completion diagnostics with no full-deck accuracy. Do not raise thinking effort,
grade partial output, or substitute finished-case accuracy to qualify low/off.

## Next session

1. Read the [README](../README.md), this status, and the
   [annotated Claude Opus 5.5 xhigh review](claude-opus-5.5-review-2026-10-03.md).
   Check live service state before any launch; no experiment should be left running.
2. Complete a bounded decision on dense precision. First establish original IQ3
   variance with complete thirty-case low/off seed runs, or use a cheap component
   consistency check if it requires no substantial engine instrumentation. The
   post-hoc five-case deck can reject a variant but cannot select it. Launch the
   corrected embedding-plus-head profile only if the evidence justifies continuing
   this line. Require API checks, matched performance and complete naturally finished
   paired canaries before claiming benefit. Publish all failures and incomplete
   coverage; close a variant without a repeatable gain that justifies its cost.
3. If a precision variant survives, qualify off-mode and vision before selecting
   it or changing OpenCode. Leave original IQ3 selected otherwise.
4. Use measured critical-path profiling for upstream decode work. Investigate
   persistent vision staging only if freed VRAM can actually enlarge the expert
   cache: merely killing the vision worker leaves the cache arena fixed. The
   earlier 27B ~49 ms staging result is not proof for this stack.
5. ExLlamaV3/TabbyAPI CPU offload remains a source-audited independent bootstrap,
   requiring a separate checkpoint/build. It has no measured Ulmus gain. c2 remains
   lower priority; existing history parking is FIFO rather than concurrent serving.
   The 397B probe measured ~12.4 tok/s but has no quality qualification.
   DeepSeek 4.1 Flash remains a later experiment.

The checkpoint including the fork closure and head-only evidence was pushed as
`ea93cab`. Raw evaluations, partial captures and the Claude request/transcript
stay private in the canonical workspace; only allowlisted evidence is public.
The requested Claude review completed successfully and is saved with corrections
and explicit uncertainty. Its recommendations are proposals, not new measured results.
