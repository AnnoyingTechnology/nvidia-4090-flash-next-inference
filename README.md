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

Decode counts reasoning and answer tokens. The speed cells intentionally stop
at 512 tokens; first streamed token is not a completed answer. The vision
profile costs about 12% decode in this comparison, but cache history differs,
so the difference is not an exact isolation of projector residency. No
wall-plug energy claim or power sweep is inferred from board-power samples.

Prior original-table text profiles measured 111.15–116.4 tok/s with medium
reasoning. Earlier fresh 130K prefill measured about 4,850 tok/s, with 27.2 s
TTFT. A small same-history cache check reduced TTFT from 1.67 to 0.173 s,
with 3,124 cached tokens; those are separate historical cells, not values
measured on the final vision profile.

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
| Original BF16 ngram table, RAM resident | 107.5 tok/s; **112/140** answer-content correct vs 115 | Fits with about 35.9 GiB RAM available; no demonstrated quality recovery, not selected |
| CPU activation-quantization parallelization | 107.4 vs subsequent 105.9 tok/s baseline | 18 native-pool parity configurations pass; gain not established, not selected |

These rows use several protocols. Their percentages are not multiplied, and
no target-weight or KV precision change is described as lossless. Verified
MTP proposals are always checked against the quantized target.

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
| 140-question knowledge, strict letter | **114/140** | 108/140 |
| Same screen, answer content | **115/140** | **115/140** |
| Practical executable functions | **4/4** | **4/4** |
| Operations decisions, content / strict | **8/8 / 6/8** | **8/8 / 8/8** |
| Multi-turn simulated tool workflows | **3/3** | **3/3** |
| Synthetic GPU vision, strict JSON and content | **5/5** | **5/5** |

Knowledge uses zero-shot low reasoning, the stated sampler, seed 42 and a
4096-token cap. IQ3_S/Q4 reached the cap five/four times. Answer-content scoring
only accepts a single A–J letter, optionally surrounded by bold markers.
The equal totals hide ten differing answers. The broader official agent and
vision benchmarks were not run; four function tasks do not qualify repository
repair. No generated operations command was applied to infrastructure.

## What might still be left

1. Expand executable code/repository and operations/tool qualification, including
   output caps, exact arguments, recovery, instruction compliance and answer latency.
2. Complete the frozen 15-image comparison against low-reasoning Codex Luna,
   Terra and Sol, plus Flash-Next with none/low reasoning; record exact model versions.
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
- [Research and pitfalls](docs/research-and-pitfalls.md): measured and unqualified alternatives.
- [Public evidence](results/public/export-manifest.json): explicit export set and original/export hashes.

The complete private captures remain local. Public evidence deliberately excludes
host/container inventory and benchmark question/test payloads; export hashes differ
where local paths and per-sample telemetry were removed. This is not a dump of
private session history. Original code is Apache-2.0; upstream patch, dataset,
model and sample-image licenses remain separate, as recorded in [NOTICE](NOTICE).
