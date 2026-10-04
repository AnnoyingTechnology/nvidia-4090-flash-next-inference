# NVIDIA RTX 4090 Flash-Next inference

This repository records the optimization and bounded quality qualification of
**Qwen3.8-Flash-Next on one 24 GiB RTX 4090, Ryzen 7900 and 192 GB RAM**.
The selected unpruned GSQ IQ3_S path with on-demand GPU vision measured
**120.10 tok/s at 32K** and **112.55 tok/s at 128K** in the latest matched
context probes, with roughly **4,700–4,800 tok/s** on uncached
32K prefill, at an unchanged **280 W GPU limit**.

The stack is based on pinned [Strata](https://github.com/Niko1221/Strata),
compiled for CUDA 12.4 / SM89. All experts and the ngram table stay in RAM;
VRAM holds dense weights, verified MTP state, an adaptive expert cache and
a bounded KV window. Selection prioritizes DevOps, SysAdmin and code, then
general agents, vision, knowledge and practical thinking. Pure math has low weight.

This is an active research checkpoint, not a claim of full-size quality parity
or exhausted hardware headroom. It complements the earlier
[RTX 4090 27B](https://github.com/AnnoyingTechnology/nvidia-4090-llm-inference)
and [Intel Arc Pro B70](https://github.com/AnnoyingTechnology/intel-arc-b70-llm-inference)
projects. Their rates concern different models and cannot be treated as a
same-target comparison.

**Frozen checkpoint, 2026-10-04.** The owner has frozen this Ulmus deployment
as-is. Do not resume tuning or alter its serving configuration without a new
explicit request. Work on other hardware belongs in a separate checkout. Selected profile is
`flash-iq3s-256k-vision-tune-owneradapt24`: the qualified lend-VRAM v4 image,
with expert-cache updates capped at 24 experts instead of 96. The model,
precision, reasoning defaults and context capacity are unchanged.
OpenCode has been verified through the normal launcher; no experiments remain running.
[Resumption record and decisions](docs/exploration-2026-10-04.md),
[selection checks](results/public/adapt24-selection-20261004.json).

| Latest matched ABBA, low reasoning | V4 / 96 swaps | V4 / 24 swaps | Change |
|---|---:|---:|---:|
| 32K context, median of launch medians | 119.05 tok/s | 120.10 tok/s | +0.88% |
| 128K context, median of launch medians | 107.95 tok/s | 112.55 tok/s | +4.26% |
| Equal-output aggregate over the mixed deck | 113.29 tok/s | 118.69 tok/s | +4.77% |

Two fresh launches per side, identical inputs/build/sampling, API 9/9 on all
launches. Candidate launch medians exceed baseline ranges at both contexts,
though the 32K margin is tiny. These are workload-specific measurements, not a
universal gain. Practical30 **29/30** at low, all naturally completed, matching
baseline's score; different failed cases remain within known seed variation.
The fifteen-image deck matches baseline **14/15**, all natural; new/cached/new
maximum-budget staging passes 3/3. Candidate median canary answer time is 8.62 s
versus 9.13 s, but differing output trajectories prevent attributing all of that
to decoder speed. [Performance](results/public/adapt-batch-20261004-summary.json),
[canaries](results/public/practical30-adapt24-comparison.json),
[vision](results/public/vision15-adapt24-low.json).

Profiling found about 1.1 ms/window awaiting cache updates; smaller batches
reduce the amount copied per adaptation, trading slower adaptation for less
potential exposed waiting. CPU wait is only 0.63–0.94 ms/window, so expanding
CPU weights is deprioritized. Offline cross-layer cache allocation reduced
misses only 0.4–2.9%, insufficient to justify implementation on this deck.
Firmware reports DDR5-3600 across four 48 GiB DIMMs. A short sequential-read
probe measured 51.84 GB/s on one thread and 43.29 on twelve; this is synthetic
bandwidth, not inference bandwidth. No hardware setting changed.
[Diagnostics](results/public/decode-diagnostics-20261004-summary.json),
[RAM](results/public/host-memory-20261004-summary.json).

The following v4-versus-resident results predate this batch-size refinement;
do not multiply gains across the different workloads.

**Earlier decision: select lend-VRAM v4**, original profile `flash-iq3s-256k-vision-tune-ownerswap`.
The same IQ3 target stays loaded. Between images the encoder lends its GPU
memory to the expert cache: about **8,379 slots versus 7,603–7,605** with resident
vision. The owner accepts the measured **+93 ms median per new, uncached image**
(worst individual paired increase **+118 ms**); cached images bypass staging.

| Matched low-reasoning decode | Resident vision | V4 swap | Change |
|---|---:|---:|---:|
| Original requests replayed, two launches per build | 102.50 tok/s | 108.83 tok/s | **+6.17%** |
| 64K context, S V V S, three questions per launch | 103.05 tok/s | 110.0 tok/s | **+6.74%** |
| 128K context, one launch per side, three questions | 99.7 tok/s | 104.5 tok/s | **+4.81%** |
| Separate changed-prefix screen, V S S V | 107.325 tok/s | 105.1 tok/s | **−2.07%** |

The original-request and 64K launch ranges do not overlap. The 128K pair is a
small regression screen, not proof of a repeatable gain. All hashes match within
each A/B; all API checks pass. The changed prefix means the negative screen does
not isolate a v4 code regression, but it remains evidence that gains vary by
workload. V3 recovered +5.68% on the original requests and produced identical
paired completions to v4; v4 has lower image overhead.
[Replay](results/public/swap-prefix-control-comparison.json),
[64K](results/public/swap64-comparison.json), [128K](results/public/swap128-comparison.json),
[negative screen](results/public/swap-ab-v4-comparison.json).

V4 scores **29/30 practical DevOps canaries at low**, all naturally completed,
with valid positive/negative grader controls. Resident IQ3 scores 28/29/30
across seeds 42/7/123; these results show no resolved quality regression, rather
than an improvement or full-size parity. The matched image deck gives **14/15
content on every launch**, all sixty natural completions and no swap failure.
[Canaries](results/public/practical30-swap-v4-comparison.json),
[image latency/integrity](results/public/swap-deck-partial-comparison.json).

The entire **32K/64K/96K/128K/192K/256K** range remains relevant. Sampled decode
and configured capacity are separate: 192K/256K v4 speed is unmeasured, and no
new 250K prefill was run at this checkpoint. The backend remains 262,144 tokens,
with a 253,952-token OpenCode window. Traced short reads show slot refill is only
25–31 ms; their floor is expert streaming, so refill tuning is closed.
The selected launch passes 9/9 API checks and a new/cached/new maximum-budget
image staging check; OpenCode returned `READY` naturally at low. Loaded after
these checks: **23.44 GiB VRAM**, about **81.1 GiB engine/vision proportional host
RAM**, with **102.7 GiB host RAM available**. Idle CPU was 0.24%; the earlier
active-decode sample used about twelve core equivalents. The 54.3 GiB cgroup
counter here excludes some already-resident file pages charged elsewhere.
[Serving API](results/public/swap-v4-serving-api.json),
[staging](results/public/swap-v4-large-image-smoke.json),
[handoff and next options](docs/handoff-2026-10-04.md).

## Result

The recorded profiles expose model `Qwen3.8-Flash-Next`, alias `ulmus`, through
an OpenAI-compatible API on **127.0.0.1:19623**. No production service or
network exposure was changed. The following table preserves the **2026-10-03
baseline**; the selected 2026-10-04 swap measurements are above:

| Measurement at 280 W limit | Text profile | GPU vision profile |
|---|---:|---:|
| Decode, six diversified 512-token low-reasoning runs | **110.8 tok/s** median | **97.65 tok/s** median |
| Cold prefill, 31,818 tokens, two runs | **4756.6 / 4780.9 tok/s** | **4723.6 / 4716.3 tok/s** |
| Cold 32K first streamed token | **6.75–6.78 s** | **6.83–6.84 s** |
| Short-prompt first streamed token, median | **0.548 s** | **0.604 s** |
| Median of per-run decode board-power medians | **236.5 W** | **221.8 W** |
| Minimum available host RAM across these cells | **104.01 GiB** | **103.58 GiB** |
| Effective profile defaults and API checks | **9/9 pass** | **9/9 pass** |
| Vision with default low reasoning | Not enabled | **5/5 strict JSON and content**, 1.94–4.07 s |
| Loaded vision container RAM, 30-second decode sample | Separate text cell not sampled | **82.7 GiB**, about **103.7 GiB** host RAM available |
| VRAM, same sample | Separate text cell not sampled | **23.45 / 23.99 GiB** |
| CPU, same sample | Separate text cell not sampled | **12 core equivalents**; one thread on each physical core busy, SMT siblings mostly idle |

Decode counts reasoning and answer tokens. The speed cells intentionally stop
at 512 tokens; first streamed token is not a completed answer. The table's
two columns come from separate runs with different cache histories. A matched
A/B on 2026-10-04 (three fresh launches per profile, T V V T T V, identical
requests) isolates GPU vision residency: **114.85 versus 104.25 tok/s (−9.2%)**,
with 8606 versus about 7604 expert-cache slots and a 91.0% versus 87.3% decode
hit rate. Per-launch ranges do not overlap; 32K prefill is unchanged.
[Matched evidence](results/public/vision-residency-comparison.json) No
wall-plug energy claim or power sweep is inferred from board-power samples.
The later resource sample covers an active coding decode, so its board draw
is a different cell. CPU occupancy includes worker polling and coordination;
it does not prove all busy cycles perform useful expert computation. Adaptive
expert caching intentionally fills VRAM, while all experts/ngrams already fit
in RAM. Container RAM and host-used RAM overlap and must not be added.

A later five-second loaded Q4 vision decode sample used **103.59 GiB container
RAM**, **23.44 GiB VRAM**, with **77.96 GiB host RAM available** and **11.98 CPU
core equivalents**. The earlier IQ3 sample used 82.7 GiB RAM. Docker's headline
memory counter excludes inactive file pages; the comparable cgroup measurement
includes them, which explains the lower number shown by `docker stats`.

Prior original-table text profiles measured 111.15–116.4 tok/s with medium
reasoning. Earlier fresh 130K prefill measured about 4,850 tok/s, with 27.2 s
TTFT. A small same-history cache check reduced TTFT from 1.67 to 0.173 s,
with 3,124 cached tokens; those are separate historical cells, not values
measured on the final vision profile.

## Quality and vision checkpoint — 2026-10-03

Current comparisons use **low reasoning**, with separately labelled off-mode
cells. The selected target remains the complete GSQ IQ3_S model with its
IQ4_NL ngram table and original BF16 vision projector.

| Frozen screen | IQ3_S | Luna low | Terra low | Sol low |
|---|---:|---:|---:|---:|
| 15 diverse screenshots, diagrams, documents, spatial tasks and photos: image content | **15/15 low; 15/15 off** | **14/15** | **15/15** | **15/15** |
| Same 15: exact requested keys and expected JSON types | **14/15 low; 14/15 off** | **11/15** | **14/15** | **14/15** |
| Harder published human charts: reviewed visual content | **19/20 low** | Not run | **20/20** | **20/20** |
| Ordinary chart arithmetic: addition, subtraction, multiplication, division, average | **5/5 low** | Not run | **5/5** | **5/5** |

Exact cloud models are `gpt-6-luna`, `gpt-5.6-terra` and `gpt-6.1-sol`.
All returned plain JSON on the first deck. Numeric strings explain several
typed-contract differences; Luna also miscounted a spoon. The harder round
contains 21 requests: one ambiguous population question is excluded from the
reviewed score, and two published annotations need unit/value corrections.
Original responses and annotation scores are retained. IQ3_S misread a line
chart's change; this set does **not** separate Terra from Sol or establish
broad cloud-model parity. Read the [vision protocol and audit](docs/vision-comparison.md).

The 24-case frozen LiveCodeBench attempt at **low / 8192 output tokens** is
**incomplete: 13 finished and passed, 11 exhausted the cap**. It has no usable
full-deck quality score. A separately labelled 32768-token retry of the
first capped case also exhausted its cap without producing code. The same
case finished and passed with thinking off. The matched full off-mode runs
completed naturally on **all 24 cases**: **IQ3_S 14/24, Q4_K_XL 16/24**.
All 24 request hashes match. Q4 gains four cases and loses two; this small,
single-seed screen does not establish a broad quantization advantage. Median
completed-answer latency was **13.83 s IQ3_S / 40.42 s Q4**; total generation
time **16.06 / 25.32 minutes**. These are answer-length-sensitive quality
cells, separate from fixed-length decode throughput. Q4 remains a diagnostic
alternative; the extra latency is substantial. A separately labelled IQ3_S
low-mode retry with presence penalty 1.5 also exhausted 32768 tokens.
Q4 completed and passed that same hard low-mode case in **195.24 s / 13,285
tokens**; this one case suggests a precision-sensitive difference worth
repeating, while its latency remains far above the off-mode IQ3 answer.
Capped cases are neither correct nor incorrect, and finished-case counts do
not establish accuracy for the whole deck. The historical 140-question low
knowledge attempts also had caps: IQ3_S/Q4 produced 115 correct completed
answers each, with five/four incomplete cases; their full-deck quality remains
unqualified. Four practical code functions and eight operations
decisions passed on content. Published paired full-size coding/knowledge
references remain the quantization anchor in the quality section below.

The off runs use the official floating sampler values (temperature .7,
top-p .8, top-k 20, presence penalty 1.5), but Strata's **effective penalty
window is 64 consumed tokens, including prompt context**. This is not
established as equivalent to the full-reference harness's penalty semantics.
The model's low effort is a soft instruction, not a thinking quota. Frozen
executable DevOps canaries and longer-window sampler checks are the next
qualification steps. See the [coding evidence](results/public/coding-checkpoint.json).
Ten low/off prompt fixtures render byte-for-byte identically to the pinned
official Qwen template, including system, multi-turn, tools and image messages.
This checks prompt serialization; it does not certify all native numerical paths.

| Thirty executable DevOps/Python canaries, v2 | IQ3_S | Q4_K_XL |
|---|---:|---:|
| Low: complete correct functions | **28/30** | **30/30** |
| Off: complete correct functions | **29/30** | **27/30** |
| Low median completed-answer time | **9.12 s** | **16.51 s** |
| Off median completed-answer time | **3.40 s** | **6.60 s** |

All completed IQ3/Q4 runs stop naturally; each function has positive/negative isolated
grader controls. V2 repairs three interfaces found ambiguous in the Q4 prototype
and includes one public example per prompt. All 30 are rerun; private tests and
controls are unchanged. This is a local canary deck, not a blind public benchmark
or repository-scale agent qualification. [Protocol and results](results/public/practical30-comparison.json)

All 30 input hashes match within each effort. IQ3's low-mode failures accept
unbracketed IPv6 and raise an exception through incorrect regex group indices
in Retry-After parsing; Q4 low passes both. IQ3/Q4 off both mishandle the
missing-variable return contract; Q4 off also misses root-route and IPv6-zone
rules that IQ3 off handles. More precision does not uniformly win across
efforts. These single-seed results support repeating specific disagreements,
not a universal retained-quality percentage.

**Seed variance, 2026-10-04.** Original IQ3 on the same runtime, deck and
grader with seeds 42/7/123 scores **28/29/30 low** and **29/28/28 off**; all 180
generations stop naturally. Three low and four off cases change verdict across
seeds, and none fails under every seed. One- or two-case single-seed differences
on this deck are therefore not resolvable: Q4's 30/30 low and 27/30 off sit
inside or next to that spread. Pooled low 87/90 and off 85/90 do not separate
the efforts either; median answer time is 3.4–3.9 s off and 9.1–9.8 s low.
One low `backoff` answer finished naturally after 10,037 tokens and 107 s,
beyond the profiles' 8192-token default output budget.
[Seed evidence](results/public/practical30-comparison.json)

An **experimental IQ3 + Q4-source output head** completed **29/30 low** in
**9.45 s median** at seed 42, versus 28/30 and 9.12 s for original IQ3. Original
IQ3 itself passes both of those failures at other seeds, so this is no
demonstrated quality gain. Fresh matched 512-token decode measures **100.6 tok/s
original / 100.3 head-only**: no throughput gain. The mixed checkpoint also
changes the shared MTP head and is not the exact published GSQ release.
**Closed 2026-10-04:** neither head-only nor embedding-plus-head is pursued
without new evidence. [Matched performance](results/public/precision-iq3-head-comparison.json)

## Bandwidth reference and remaining headroom

Observed PCIe 4 x16 host-to-device bandwidth is **26.9 GB/s**. RAM capacity
lets the complete expert set and ngram table stay resident, but does not
remove CPU-memory bandwidth or transfer costs. Light decode profiling found
roughly 19–23 ms speculative windows: 4.6–8.4 ms of CPU cold-expert work,
about 9 ms waiting for GPU progress and 1.6–1.9 ms of draft work. These
stages overlap; do not add them into an invented percentage breakdown.

More CPU workers bought little decode speed. At the PCIe .2 / min-p .5
placement, six 512-token requests per setting gave medians of **104.15 tok/s
with 6 pool workers** and **107.1 with 11**: 83% more workers, about 3% more
speed, with overlapping per-request ranges (97.5–111.2 and 98.6–120.6).
This was not repeated at the selected .35 / .7 placement. The busy hardware
thread on each physical core includes polling and waits, so occupancy does
not show saturated arithmetic. Inference, not a measured critical path:
cold-expert reads from the RAM-resident set and GPU progress probably bound
decode more than core count, so a wider CPU on the same dual-channel memory
is unlikely to help much. Whether fewer workers keep speed at lower wall
power is not measured. [6 workers](results/public/sampled-iq3s-workers6spec4.json),
[11 workers](results/public/sampled-iq3s-workers11spec4.json)

The native build already uses AVX-512. Hybrid connections, GDN work,
resident experts and transfer/wait stages all matter; the output head alone
does not dominate. There is no established practical roofline percentage
for this mixed CPU/GPU runtime. Further gains need measured critical-path
work, not a claim that an unused RAM allocation makes inference faster.

## Optimization ladder

| Decision or experiment | Measured result | Integrity boundary |
|---|---:|---|
| Stock / ik / MoE-cache llama.cpp, same Q4 | 23.63 / 24.38 / 21.91 tok/s | Three 256-token greedy baselines; tested configurations, not exhaustive runtime rankings |
| Strata Q4 with realistic thinking sampler | **60.65 tok/s** | Six 512-token runs; engine path differs from plain baselines |
| Strata GSQ IQ3_S with the same sampler | **112.55 tok/s** | Quantized target changes; published full-size evidence and local screens required |
| CPU worker, prefill, PCIe and MTP tuning | Selected 11 workers, auto:32768, .35 PCIe / .7 min-p, four draft tokens | Aggressive short-sweep gains failed longer confirmation |
| GPU BF16 vision, 4096 image-token budget | **5/5** initial and profile-default canaries pass | Budget, placement and reasoning not fully isolated; no broad vision parity claim |
| Effective low/stochastic defaults and JSON validator dependency | **9/9 API checks per profile**, upstream 8 tests pass | Identical engine binary; prompt-and-validate JSON, no grammar decoder |
| Original BF16 ngram table, RAM resident | 107.5 tok/s; 112 correct completed knowledge answers vs 115, with caps in both runs | Fits with about 35.9 GiB RAM available; full-deck quality unqualified, no demonstrated recovery, not selected |
| CPU activation-quantization parallelization | 107.4 vs subsequent 105.9 tok/s baseline | 18 native-pool parity configurations pass; gain not established, not selected |
| eddoursul native fork, CUDA 12.4 adaptation, Q4 at 32K | **33.65 vs 57.65 tok/s upstream**, 9/9 component and API checks pass | Slower in this matched configuration; not selected. Its older engine lacks the selected stack's 256K KV paging |
| Same adapted fork, IQ3 at 32K | **46.60 vs 105.05 tok/s upstream**, 9/9 API checks per engine | Identical target/arguments/requests; not selected |
| CPU vision encoder, same 4096 image tokens, one resident profile | Decode −3.3% vs text-only (GPU vision −9.2%); image first token **35.5 s median vs 1.57 s** on GPU; 15/15 content on both | Rejected: minute-scale image latency in a single resident profile. GPU vision kept. [Decode](results/public/cpuvision-residency-comparison.json), [deck](results/public/vision15-cpu-gpu-20261004.json) |
| Fixed-length 512-token decode at 32K / 64K / 128K context, vision profile | Medians **110.5 / 104.4 / 103.4 tok/s** across three questions each | 64K within 10% of 32K: long-context paging work closed. Per-question spread exceeds the context effect. [Evidence](results/public/context-decode-20261004.json) |
| `--short-read` window/batched threshold, chained turns at 64K | Windows faster up to 69 fresh tokens, slower from 97; break-even about 87 | Default 64 kept: projected 0.38% of real-session engine time. [Evidence](results/public/short-read-comparison.json) |

These rows use several protocols. Their percentages are not multiplied, and
no target-weight or KV precision change is described as lossless. Verified
MTP proposals are always checked against the quantized target.

The native-fork Q4 A/B uses fresh launches, identical request hashes for three
warmups, six 512-token low-mode decode cells and two uncached 31,823-token
prefills. Both engines use a 32K fully resident int8 KV allocation, identical
weights, frontend, image encoder and sampling. Prefill is **4386 / 4548 tok/s
upstream**, **4512 / 4324.5 fork**. Short-prompt TTFT medians are **1.04 / 2.63 s**.
Aggregate MTP acceptance is similar, **73.98% / 73.63%**; the fork has a slightly
larger expert cache, **14.12 vs 13.76 GiB**, yet slower decode. This measures
the CUDA 12.4 adaptation, not the author's newer-CUDA build, and does not isolate
one kernel. [Matched evidence](results/public/native-ab-q4-32k-comparison.json)
The same controlled IQ3 comparison also favors upstream; its 32K results are
separate from the selected 256K profile's earlier measurements.
[IQ3 matched evidence](results/public/native-ab-iq3-32k-comparison.json)
Disabling adaptive refill does not remove the fork's Q4 regression: **46.15
tok/s upstream / 29.75 fork**, with both slower than their adaptive runs. Keep
adaptation enabled. This does not identify the cause of the remaining stall.
[Static-cache control](results/public/native-ab-q4-32k-static-comparison.json)

## Boundaries

- One RTX 4090, Ryzen 7900 and 192 GB RAM; preserve the measured driver/kernel
  and 280 W policy when reproducing this campaign.
- Optimize one active request first. Two cached histories work, but execution
  queues FIFO; simultaneous c2 and an excellent c1+c2 compromise are unqualified.
- Keep all experts and the IQ4_NL ngram table in RAM; no decode-time model disk tier.
- Use published full-size benchmark references. No local Q8/full-size target inference.
- Advertised context is 262,144 tokens. Text retrieval canaries passed near
  32K/128K/256K, but the exact native boundary and combined 256K plus images
  are not yet qualified.
- The API is unauthenticated and published on loopback only. Use an SSH tunnel
  for remote access. No automatic startup service is installed.
- Downloaded weights, private deployment captures, dataset question/test payloads
  and binary dependencies are excluded from Git.

## Profiles and quick operations

The owner profiles share GSQ IQ3_S and the release's IQ4_NL table. One
vision-capable model remains loaded; routine use does not switch profiles:

| Profile | Purpose |
|---|---|
| `flash-iq3s-256k-tune-ownertext` | Faster text-only code, operations and agent work |
| `flash-iq3s-256k-vision-tune-ownervision` | Preserved resident-GPU-vision baseline and rollback |
| `flash-iq3s-256k-vision-tune-owneradapt24` | Selected v4, 24-expert update batches; GPU BF16 vision on demand, 4096-token image budget |
| `flash-iq3s-256k-vision-tune-ownerswap` | Original v4 / 96-expert batch rollback |

On an NVIDIA Linux host with Docker and the NVIDIA Container Toolkit:

```bash
git clone https://github.com/AnnoyingTechnology/nvidia-4090-flash-next-inference
cd nvidia-4090-flash-next-inference
bash scripts/build.sh
docker build -f Dockerfile.lend-vram -t ulmus/strata:99f3dbd-lendvram .
python3 scripts/prepare_models.py
bash scripts/prepare_packs.sh
bash run.sh flash-iq3s-256k-vision-tune-owneradapt24
python3 wait_ready.py
curl -fsS http://127.0.0.1:19623/health
```

The source build is substantial. The selected model download is about 83.6 GB,
plus a 0.91 GB projector, MTP assets and local build/cache space. The preparation
steps verify immutable file hashes and preserve unexpected existing files.
The tested build is CUDA 12.4 / SM89, compatible with the campaign's existing
R550 driver; do not substitute CUDA 13 merely because it is newer.

Stop the owned container before switching profiles:

```bash
bash stop.sh
bash run.sh flash-iq3s-256k-tune-ownertext
python3 wait_ready.py
```

`ULMUS_ROOT` can override the checkout root, `ULMUS_LIBRARY` an optional
read-only legacy GGUF library, and `ULMUS_EXPECTED_HOST` can enforce an expected
hostname. No host path or private address is required by the selected profiles.
`stop.sh` removes only the owned inference container, preserving models and images.

For OpenCode on Juniperus, the installed model is
`ai-ulmus-flash-next/qwen3.8-flash-next`, with low/off variants and a
**253952-token context window**. The duplicate output-budget entry was removed.
The prior 27B default is preserved.
[Client configuration and SSH launcher](docs/opencode.md)

## Production invocation and settings

The profiles execute the following engine command inside the container;
the vision profile additionally supplies `--vision` and starts the GPU encoder:

```bash
/opt/strata-build/strata \
  --pack /work/packs/iq3s \
  --native /work/models/gsq-iq3_s/Qwen3.8-Flash-Next-GSQ-RCO-IQ3_S-00001-of-00002.gguf \
  --expert-profile /opt/strata/data/expert-profile.bin \
  --expert-cache auto --ple-io ram --prefill auto:32768 \
  --spec 4 --spec-min-p 0.7 --mtp /work/mtp/rt \
  --max-context 262144 --kv int8 --kv-resident 32768 \
  --pool-workers 11 --pcie-frac 0.35 --stats
```

| Setting | Purpose |
|---|---|
| Full-RAM experts and `--ple-io ram` | Avoid decode-time disk paging |
| `--expert-cache auto` | Use VRAM left after dense weights, MTP, KV and workspaces |
| `--prefill auto:32768` | Stream substantial prefill chunks without sacrificing the expert cache |
| `--spec 4`, min-p .7 | Verified MTP with the selected acceptance policy |
| `--pool-workers 11`, PCIe fraction .35 | Tested CPU/GPU cold-expert balance |
| int8 KV, 32K resident window | Bound VRAM KV while keeping long-context capacity |
| BF16 GPU projector, 4096 image tokens | Tested image path; maximum workspace warmed before expert-cache sizing |

The default sampler is temperature 1, top-p .95, top-k 20, min-p 0,
presence penalty 0 and repetition penalty 1. The shared settings default
reasoning to **low** and output room to **8192 tokens**. Explicit client
settings override these values; hard cases may need more effort or room.
`GET /settings` and `GET /props?model=ulmus` show effective defaults.

Machine-facing JSON supports `response_format: json_object` or `json_schema`
with the packaged validator. It prompts then validates; it does not constrain
decoding, buffers structured streaming and errors on invalid/capped output.
Structured format and tool calls cannot be combined in one request.

## Model and quality contract

Published full-size Flash-Next is the quality reference. DASLab's paired
BF16/IQ3_S results report LiveCodeBench v6 **87.43 / 86.86** and GPQA Diamond
**91.92 / 92.93**, with the IQ4_NL table included. Those are harness-specific
comparisons, not a universal retained-intelligence percentage.
[Published paired results](https://huggingface.co/ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-GGUF#results)

| Frozen local low-reasoning screen | IQ3_S | Q4 |
|---|---:|---:|
| Knowledge attempt: correct completed strict letters | 114 | 108 |
| Knowledge attempt: correct completed answer content | 115 | 115 |
| Incomplete knowledge cases / 140 attempted | 5 | 4 |
| Full-deck knowledge accuracy | **Unqualified** | **Unqualified** |
| Practical executable functions | **4/4** | **4/4** |
| Operations decisions, content / strict | **8/8 / 6/8** | **8/8 / 8/8** |
| Multi-turn simulated tool workflows | **3/3** | **3/3** |
| Synthetic GPU vision, strict JSON and content | **5/5** | **5/5** |

Knowledge uses zero-shot low reasoning, the stated sampler, seed 42 and a
4096-token cap. IQ3_S/Q4 reached the cap five/four times, so these are completion
diagnostics rather than representative full-deck scores. Answer-content scoring
only accepts a single A–J letter, optionally surrounded by bold markers.
The equal totals hide ten differing answers. The broader official agent and
vision benchmarks were not run; four function tasks do not qualify repository
repair. No generated operations command was applied to infrastructure.

## What might still be left

1. Expand executable code/repository and operations/tool qualification, including
   output caps, exact arguments, recovery, instruction compliance and answer latency.
2. Expand beyond the completed 15-image and human-chart comparisons with
   independently reviewed screenshots, documents, spatial scenes and visual tool use.
3. Profile the selected upstream's cold experts, cache placement, transfers and
   GDN/hybrid-connection critical path. The measured eddoursul fork is closed;
   no further tuning or qualification is scheduled.
4. Build and qualify ExLlamaV3/TabbyAPI with a separate EXL3 checkpoint. Its
   whole-layer CPU offload could win or lose against per-expert caching.
5. Requalify c2 on selected profiles. Current history parking is not simultaneous serving.
6. Port and qualify the stack on a second machine: i7-6900K on X99, three RTX 3090
   (PCIe 3.0 x16/x16/x8) and 96 GB DDR4. It needs an SM86 / AVX2 build; multi-GPU
   expert placement there is unqualified.

A complete power sweep, practical bandwidth ceiling and exact-context/image
boundary are not yet measured. The 397B partial-offload probe fit and produced
12.42 tok/s, but its quality remains unqualified. DeepSeek 4.1 Flash is a later
experiment. [Research and alternatives](docs/research-and-pitfalls.md)

## Documentation

- [Current handoff](docs/handoff-2026-10-04.md): selected serving state, decisions and next-agent questions.
- [Architecture](docs/architecture.md): pinned sources, model hashes and placement.
- [Benchmarks and quality](docs/benchmarks-and-quality.md): protocols, full-size references and caveats.
- [Operations](docs/operations.md): build, start, requests, measurements and rollback.
- [Vision comparisons](docs/vision-comparison.md): Luna, Terra, Sol, low/off protocols and annotation audit.
- [OpenCode](docs/opencode.md): naming, output reserves, reasoning variants and SSH access.
- [Research and pitfalls](docs/research-and-pitfalls.md): measured and unqualified alternatives.
- [Public evidence](results/public/export-manifest.json): explicit export set and original/export hashes.

The complete private captures remain local. Public evidence deliberately excludes
host/container inventory and benchmark question/test payloads; export hashes differ
where local paths and per-sample telemetry were removed. This is not a dump of
private session history. Original code is Apache-2.0; upstream patch, dataset,
model and sample-image licenses remain separate, as recorded in [NOTICE](NOTICE).
