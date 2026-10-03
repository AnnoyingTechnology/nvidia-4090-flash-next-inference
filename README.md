# NVIDIA RTX 4090 Flash-Next inference

This repository records the optimization and bounded quality qualification of
**Qwen3.8-Flash-Next on one 24 GiB RTX 4090, Ryzen 7900 and 192 GB RAM**.
The selected unpruned GSQ IQ3_S path measured **110.8 tok/s** for text and
**97.65 tok/s with GPU vision enabled**, with roughly **4,700–4,800 tok/s**
on uncached 32K prefill, at an unchanged **280 W GPU limit**.

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

## Result

The recorded profiles expose model `Qwen3.8-Flash-Next`, alias `ulmus`, through
an OpenAI-compatible API on **127.0.0.1:19623**. No production service or
network exposure was changed. The measured profiles are:

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
at 512 tokens; first streamed token is not a completed answer. The vision
profile costs about 12% decode in this comparison, but cache history differs,
so the difference is not an exact isolation of projector residency. No
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

## Bandwidth reference and remaining headroom

Observed PCIe 4 x16 host-to-device bandwidth is **26.9 GB/s**. RAM capacity
lets the complete expert set and ngram table stay resident, but does not
remove CPU-memory bandwidth or transfer costs. Light decode profiling found
roughly 19–23 ms speculative windows: 4.6–8.4 ms of CPU cold-expert work,
about 9 ms waiting for GPU progress and 1.6–1.9 ms of draft work. These
stages overlap; do not add them into an invented percentage breakdown.

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

The two owner profiles share GSQ IQ3_S and the release's IQ4_NL table:

| Profile | Purpose |
|---|---|
| `flash-iq3s-256k-tune-ownertext` | Faster text-only code, operations and agent work |
| `flash-iq3s-256k-vision-tune-ownervision` | General assistant including GPU BF16 vision, 4096-token image budget |

On an NVIDIA Linux host with Docker and the NVIDIA Container Toolkit:

```bash
git clone https://github.com/AnnoyingTechnology/nvidia-4090-flash-next-inference
cd nvidia-4090-flash-next-inference
bash scripts/build.sh
python3 scripts/prepare_models.py
bash scripts/prepare_packs.sh
bash run.sh flash-iq3s-256k-vision-tune-ownervision
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
`ai-ulmus-flash-next/qwen3.8-flash-next`, with low/off variants and an
optional larger output reserve. The prior 27B default is preserved.
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
3. A/B the eddoursul Strata fork, then profile cold experts, cache placement,
   transfers and GDN/hybrid-connection critical-path work.
4. Build and qualify ExLlamaV3/TabbyAPI with a separate EXL3 checkpoint. Its
   whole-layer CPU offload could win or lose against per-expert caching.
5. Requalify c2 on selected profiles. Current history parking is not simultaneous serving.

A complete power sweep, practical bandwidth ceiling and exact-context/image
boundary are not yet measured. The 397B partial-offload probe fit and produced
12.42 tok/s, but its quality remains unqualified. DeepSeek 4.1 Flash is a later
experiment. [Research and alternatives](docs/research-and-pitfalls.md)

## Documentation

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
