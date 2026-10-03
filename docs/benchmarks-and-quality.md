# Ulmus Flash-Next: second checkpoint, 2026-10-03

The latest additions are summarized in the [README](../README.md): completed
[Luna/Terra/Sol vision comparisons](vision-comparison.md), the 24-case low-reasoning
coding screen, a loaded-memory/CPU snapshot and the [OpenCode client](opencode.md).
The measurements below retain their original protocols; higher-effort historical
cells are not used as matched low/off quality comparisons.

The current candidate is **unpruned GSQ IQ3_S with the release's IQ4_NL ngram table in RAM**.
The packaged owner profiles measured **110.8 tok/s for text** and **97.65 tok/s with GPU vision enabled**,
with uncached ~32K prefill near 4,700–4,800 tok/s. GPU vision now passes the five synthetic canaries,
including the previously misread printed code. The restored original BF16 ngram table fits, but did not
demonstrate a quality recovery; it remains an optional experiment rather than the default.

Julien's selection priorities are DevOps, SysAdmin and code, followed by general agentic help, vision,
knowledge and practical thinking. Pure math has low selection weight. Published full-size Flash-Next
results govern the quality reference; local Q4 is a diagnostic comparison, never the oracle.
No local Q8/full-size target inference was run. Downloading only the original BF16 ngram table did not
change the target's quantized transformer weights.

This is a preliminary qualification checkpoint, not a claim that the hardware is exhausted or that
full-size task quality has been certified. The first checkpoint is preserved in
the first local checkpoint.

## Usable profiles and measured performance

| Packaged profile | Decode median | Uncached prefill, two runs | Minimum available host RAM |
| --- | ---: | ---: | ---: |
| `flash-iq3s-256k-tune-ownertext` | **110.8 tok/s** | 4756.6 / 4780.9 tok/s | 104.01 GiB |
| `flash-iq3s-256k-vision-tune-ownervision` | **97.65 tok/s** | 4723.6 / 4716.3 tok/s | 103.58 GiB |

Each median covers six 512-token requests, after three warmups, with low reasoning, temperature 1,
top-p .95, top-k 20, min-p 0, presence penalty 0 and repetition penalty 1. Request hashes match between
profiles (`owner-profiles-v1`); prefill prompts contain 31,818 actual tokens with zero cached tokens.
Decode counts reasoning and answer tokens. A deliberately capped speed run does not measure finished
answer quality or end-to-end time to a useful solution. Both profiles use the same main weights and
engine binary. Prior workload/cache placement differed, so this is not an exact isolation of GPU vision's
cost. The observed difference is about 12%; earlier medium-reasoning text medians were 111.15–116.4.

Individual packaged text rates were 122.5, 111.7, 107.0, 114.0, 104.4 and 109.9; vision-enabled rates
were 120.1, 100.7, 95.6, 98.6, 94.6 and 96.7. Do not advertise the best run as sustained throughput.
Raw evidence: [text](../results/public/owner-text-perf.json), [vision](../results/public/owner-vision-perf.json).

Both profiles retain full-RAM expert and ngram residency, automatic VRAM expert-cache sizing, 11 CPU
workers, verified MTP with four draft tokens, PCIe fraction .35 and speculation min-p .7. Context capacity
is 262,144 tokens, with int8 KV and a 32K resident window. Adaptive expert caching is already active.
Experimental speed projection and coupled draft are disabled. No model disk tier is used during decode.

The vision profile uses the original BF16 projector on the GPU and a 4096-token image budget. The encoder
warms its largest supported workspace before the engine sizes its expert cache. This worked with the
existing CUDA 12.4 / SM89 build and R550 driver; no driver change was needed. The earlier CPU encoder's
"no CUDA device" message was caused by deliberately hiding CUDA for CPU mode, not a failed GPU backend.

The defaults are stochastic low reasoning with an 8192-token output budget, overridable by clients.
Both profile settings files are captured in launch records. The packaged image adds the existing
`jsonschema` validator and hash-locked dependencies: the baseline otherwise silently validates a
JSON-schema response only as an object. No HTTP or engine source was patched for this dependency fix.
The engine SHA-256 is identical in parent and child. Both profiles pass **9/9 live API checks** for model
alias, context/vision metadata, defaults, implicit thinking, explicit none/cap overrides, validated JSON
streaming, and rejection of unsupported request combinations. Upstream's **8 structured-output tests**
pass with the validator installed.

Structured output uses prompting followed by validation, not constrained decoding. Structured streaming
is buffered until validation. Invalid or truncated JSON produces an error, not successful JSON.
`response_format` and tool calls cannot be combined in one request. An 8192-token default is a practical
latency budget, not the published model's maximum reasoning room.

Use the [README](../README.md) to launch either profile. No automatic startup or production routing was
added. Build and contract evidence: manifest (`owner-api-build-manifest.json`, retained locally),
text API (`owner-text-api.json`, retained locally), vision API (`owner-vision-api.json`, retained locally),
upstream tests (`owner-structured-tests.log`, retained locally).

## Published full-size quality reference

The [DASLab paired BF16-to-GSQ results](https://huggingface.co/ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-GGUF#results)
report:

| Benchmark | BF16 reference | GSQ IQ3_S |
| --- | ---: | ---: |
| GPQA Diamond | 91.92 | 92.93 |
| LiveCodeBench v6 | 87.43 | 86.86 |
| AIME25 | 100.00 | 100.00 |

The release's IQ4_NL ngram table is included in those results. The code difference is **−0.57 percentage
points** in that evaluation. Above-reference scores should be read as variance, not quantization making
the model smarter. Exact release prompts, effort, budget, seeds and grader revisions remain unknown.
The generic GSQ repository's greedy lm-eval script does not establish that release protocol.

[Qwen's official full-size card](https://huggingface.co/Qwen/Qwen3.8-Flash-Next#benchmark-results)
provides a separate harness-specific reference, including LiveCodeBench 91.9, SWE-bench Pro 62.5,
SWE-bench Multilingual 81.0, NL2Repo 48.1 and Toolathlon Verified 73.5. Its LiveCodeBench value must not
be substituted into DASLab's paired comparison. Neither public table certifies this runtime's DevOps,
tool reliability, vision or long-context reasoning. Do not convert token agreement or an average recovery
ratio into a universal percentage of retained intelligence.

The governing reference and uncertainty are recorded in [QUALITY-REFERENCE.json](../QUALITY-REFERENCE.json).

## Local quality and useful-answer latency

All three following knowledge runs used the same previously frozen 140 MMLU-Pro questions, zero-shot,
low reasoning, the stated stochastic sampler, seed 42 and a 4096-token cap. The IQ3_S/IQ4_NL report's
legacy label `iq3s-original-table-low` means the starting quantized release table, not the BF16 table.

| Local screen | IQ3_S + IQ4_NL | Q4 + IQ4_NL | IQ3_S + original BF16 |
| --- | ---: | ---: | ---: |
| Knowledge attempt: correct completed strict letters | 114 | 108 | 109 |
| Knowledge attempt: correct completed answer content | 115 | 115 | 112 |
| Incomplete cases / 140 attempted | 5 | 4 | 5 |
| Full-deck knowledge accuracy | **Unqualified** | **Unqualified** | **Unqualified** |
| Format failures | 7 | 15 | 10 |
| Knowledge median request time | **3.56 s** | 5.96 s | 3.53 s |
| Total knowledge screen time | **783 s** | 1277 s | 757 s |
| Practical executable code | **4/4** | **4/4** | **4/4** |
| Operations decision content | **8/8** | **8/8** | **8/8** |
| Operations strict letter | 6/8 | **8/8** | **8/8** |
| Multi-turn simulated tool cases | **3/3** | **3/3** | **3/3** |
| GPU vision, low reasoning, strict JSON and content | **5/5** | **5/5** | **5/5** |

Answer-content normalization accepts only an exact A–J letter or exactly `**A–J**`; it does not search
arbitrary prose for a convenient answer. Strict scores remain intact. The two original-table quants have
equal content totals but differ on ten questions: five correct only for IQ3_S, five only for Q4. This is
not identical behavior. The earlier greedy/non-thinking screen was Q4 100 versus IQ3_S 92; both sampling
and reasoning changed in this round, so the improved totals do not isolate reasoning or quantization.
The local bounded zero-shot protocol is not the published full benchmark protocol. Capped generations
are unusable quality tests. Original capture summaries used legacy pass/total counters; those counters
must not be interpreted as accuracy. We retain attempted coverage, completed correct/incorrect answers
and incomplete cases separately, and withhold full-deck accuracy when any case is unfinished.

### Coding completion protocol

The frozen 24-case LiveCodeBench v6 attempt at low/8192 has 13 completed, graded passes and 11 incomplete
generations. The first hard case also exhausted 32768 tokens entirely in reasoning, without answer code.
Thinking off completed that same case in about 18 seconds and passed. This single diagnostic does not
qualify the full coding deck. The complete off-mode run uses Qwen's recommended off sampler and the
unchanged frozen prompts; it is in progress.

Evaluator protocol v3 grades only naturally finished (`finish_reason=stop`) responses and publishes
full-cohort accuracy only when every selected case finishes and has a grader verdict. It does not force
thinking closure, count capped output as a model error, or substitute survivor accuracy. The output
limit remains a runaway guard; reaching it invalidates that quality run. Fixed-length throughput
measurements remain separate from answer-quality tests.

The code deck covers exact config-size parsing, recursive credential redaction, deterministic/idempotent
deployment reconciliation and IPv4/IPv6 CIDR handling. Generated functions are run through the retained
isolated grader with public/private tests and positive/negative controls. Original-table IQ3_S completion
times were 25.15, 7.96, 9.54 and 12.15 seconds, versus Q4 40.44, 14.75, 21.35 and 31.02 seconds.
These are four practical function tasks, not repository-scale coding or SWE-bench qualification.

The eight operations decisions cover systemd network readiness, atomic nginx changes, deleted open logs,
Ansible idempotence, TLS/SNI, PostgreSQL expand/contract, authoritative DNS/TTL and retaining SSH access.
The two IQ3_S strict failures were correct answers surrounded by bold markers. No generated command
was applied to infrastructure.

The tool cases test reading status/logs without changes, treating malicious log instructions as data,
and checking a proposed manifest change without applying it. All quants completed the cases without a
mutation. Original-table IQ3_S made two unnecessary manifest reads in the injected-log case; the result
still passed. Simulated tools preserve complete traces and flag wrong arguments/API errors. Three cases
are not comprehensive agent or adversarial qualification.

All five vision fixtures are synthetic: nginx error extraction, maximum `df` usage, loopback database
listeners, a directed architecture diagram, and the printed `ULMUS-731` with colored boxes.
With GPU vision and low reasoning, original-table IQ3_S took 2.12–3.57 seconds in the comparison run.
The packaged profile defaults passed again, taking **1.94–4.07 seconds**. Q4 low-reasoning GPU vision
took 3.52–5.96 seconds. Four large CPU-vision cases took roughly 40–56 seconds; the CPU IQ3_S ladder
was stopped after two passing cases and is explicitly incomplete. Cached-image repeat runs exclude
fresh encoder work, so do not interpret these timings as a universal GPU speedup ratio.

Non-thinking GPU vision got all image content right but only 2/5 strict JSON for IQ3_S and 1/5 for Q4,
mostly code fences. Low reasoning passed 5/5 strict for both. The original 1K-budget OCR failure is now
recovered in the tested 4K-budget path, but budget, encoder placement and reasoning were not all isolated.
No video, multi-image, fine handwriting, photo understanding or public vision benchmark was evaluated.

Earlier fresh 16-fact retrieval tests passed at 32K/128K/256K for both quants. The BF16 table passed the
same long-context and ten basic canaries. These establish retrieval canaries, not general 256K reasoning.
The packaged GPU-vision profile was measured through 32K text and the five image cases; combined 256K
text plus images is still unqualified.

All raw runs are retained. [second-round-summary.json](../results/public/second-round-summary.json) contains derived
metrics and source hashes; frozen decks and scoring logic are in this directory.

## What the 192 GB RAM allowed us to test

The original BF16 table stores 320,001,536 rows × 160 values, split into 128 shards: **95.37 GiB**.
It was extracted from validated exact HTTP byte ranges at official revision
`de4b8e4d43b917e7706784d8bb445c9af86a3540`, without downloading/loading the full target.
The assembled GGUF is 102,400,491,840 bytes and its computed SHA-256 is
`1df734318447adf7c02aed220e915c6f2c4f40a6922d9dd58eb46c45c8b60c1d`.
Per-tensor checksums and ranges are retained in the manifest (`ple-original-bf16.json`, retained locally).
These are computed extraction checksums; partial ranges were not verified against each publisher full-file
LFS checksum. Do not describe this as publisher checksum verification of whole safetensor files.

An isolated image adds upstream [BF16 loader PR 586](https://github.com/Niko1221/Strata/pull/586), pinned
to `36f829da8bc1396e8c8198e3c2e0c147c78d14ba`, on the same base. Reader self-tests pass; 4096 real rows
give bit-identical direct/mmap results. An independent 512-row check spanning every shard gives cosine
similarity .997079 and relative RMS error .076435 between BF16 and IQ4_NL, consistent with expected
quantization and no gross basis/row mismatch. Neither check certifies task quality.

The full table was locked in RAM during inference, leaving about **35.9 GiB available host RAM** for text
and 35.0 GiB with vision, with no swap/OOM. The same BF16-capable engine ran the A/B/A text comparison:

| Table | Median decode | Two uncached ~32K prefill runs |
| --- | ---: | ---: |
| IQ4_NL, before | 116.4 tok/s | 4784.6 / 4766.9 |
| Original BF16 | 107.5 tok/s | 4731.5 / 4808.9 |
| IQ4_NL, after | 111.15 tok/s | 4625.2 / 4775.8 |

All six decode and two prefill request hashes match. BF16 was below both baseline medians, but baseline
variation, changed generated text and adaptive placement prevent a precise fixed slowdown claim.
Its knowledge run gains five correct answers and loses eight versus IQ4_NL, net −3/140.
Small practical and tool cases do not distinguish it on content. It has **no demonstrated recovery** in
this screen, rather than proof that full-precision PLE is inherently worse. Keep the files and loader for
future paired work; do not spend the extra RAM by default. Q4 plus the original BF16 table was not tested.

## Optimizations tested but not selected

CPU intermediate activation quantization parallelization, upstream
[PR 500](https://github.com/Niko1221/Strata/pull/500), passes our real-geometry synthetic native-pool
parity harness: 18 configurations × four dispatches, including IQ3_S/IQ4_NL, IQ3_S/Q2_0 and Q4K/Q5_1,
three worker counts, forced parallel/serial thresholds and chunk-boundary/sleep coverage, with zero bitwise
failures. The upstream `pool_test` could not run without its missing S2 expert fixture; its failed attempt
is retained and is not counted as a pass. End-to-end 107.4 versus subsequent baseline 105.9 tok/s is
insufficient evidence to select the patch.

Native AVX-512 CPU code was already active via `GGML_NATIVE`; a disabled explicit cache option was not
proof it needed enabling. Coupled drafts were slower in the first checkpoint. A short aggressive
PCIe/speculation sweep's apparent 120.55 tok/s gain did not persist in longer repeated runs.
The existing conservative .35/.7/four-token policy remains selected.

Light decode profiling found roughly 19–23 ms speculative windows: CPU cold-expert work about 4.6–8.4 ms,
waiting for GPU progress about 9 ms, and draft work about 1.6–1.9 ms. Activation/job preparation was
under 1 ms. GPU timing indicates hybrid connections, GDN projections/recurrence, resident experts and
expert-wait stages all matter; the final head alone does not dominate. Timings overlap, and the printed
GPU total double-counts nested hybrid-connection stages. Do not sum these numbers into a percentage
breakdown. Logs are diagnostic evidence for CPU/GPU overlap and kernel work, not a speed improvement.

## Ranked remaining work and alternatives

1. **Broaden practical quality before calling the model a dependable primary agent.** Run at least 30
   held-out executable coding tasks and realistic repository repairs, plus a wider operations/tool deck
   with ambiguous observations, recovery and exact arguments. Use published full-size values for the
   matching benchmarks; keep local Q4 paired where diagnostic. Track failures, formatting and completed
   answer time separately. Repeat selected disagreements across seeds; five equal totals do not settle
   task fidelity. Extend IFBench/instruction and multimodal evidence.
2. **Recover bounded/format failures deliberately.** Re-run the capped knowledge cases with the owner
   ample output room and diagnose natural low/off completion on hard code/operations cases. Qualification must include
   completion latency, not just decode. Use native validated structured output for standalone machine-facing
   JSON, and qualify client tool schemas separately. Frozen controls are needed before attributing a gain
   to precision rather than sampler or output room.
3. **A/B eddoursul's Strata fork and improve the measured critical path.** The inspected fork pins to
   `3a19944130d93d204a845234bbb61c1f1fb3b57d`. Its [single-3090 measurements](https://github.com/eddoursul/Strata/blob/custom/docs/COMPARISON.md)
   put IQ3_S near our result and suggest useful Q4 work. Its advertised large gain compares an older
   upstream without Q4 kernels; we already use a newer baseline. The broad diff has not been built or
   qualified. Focus on cold-expert kernels, placement and overlapped transfers/GDN work, using profiles
   rather than assuming another dramatic doubling. Sensitivity-guided precision restoration of selected
   tensors is more promising to test than automatically restoring the entire PLE table.
4. **Qualify ExLlamaV3/TabbyAPI as an independent bootstrap.** Source audit at
   `d3739fd393337b1ff4d6c2a342b12f0c87a9592f` finds Flash-Next, vision, MTP and
   [AVX-512 CPU MoE offload](https://github.com/turboderp-org/exllamav3/blob/d3739fd393337b1ff4d6c2a342b12f0c87a9592f/doc/env_vars.md#cpu-moe-offload)
   with a CUDA 12.4 source route. Whole-layer CPU placement differs from Strata's expert cache and could
   win or lose. A new EXL3 checkpoint and build are required; there are no Ulmus performance measurements.
   Published two-5090 rates are not estimates for one 4090.
5. **Requalify c2 on the selected profiles.** Prior two-history parking passes isolation/cache reuse and
   gives 110 aggregate tok/s, but queues requests FIFO: the second waits about 4.52 seconds in that test.
   That profile used different tuning. There is no qualified simultaneous c2 execution or excellent
   c1+c2 compromise yet. Default to c1 until measured answer latency and cache cost justify a change.
6. **Keep broader alternatives scoped.** Same-Q4 stock llama.cpp, ik_llama and MoE-cache were built and
   measured; Strata wins the tested configurations. The separate Unsloth MTP fork is still worth a
   complete API-quality A/B; the current ik shared-MTP attempt failed API canaries. The dedicated 24 GB
   vLLM path is serious but its released CUDA 13/driver 580 stack is incompatible with the preserved
   R550 host. A supported rebuild or separately reviewed migration is required. The inspected SGLang
   24 GB recipe targets Blackwell; KT-Kernel merits a separate 397B qualification. The installed 397B
   probe's 12.42 tok/s remains a fit/speed result without quality qualification. DeepSeek 4.1 Flash is
   recorded for a later experiment.

The expanded [research matrix](research-and-pitfalls.md) records measured, source-only and incompatible routes.
The GSQ card also advertises a Coder variant with half the experts pruned; it needs independent general
and coding quality evidence and does not replace the unpruned target in this selection.

## Reproducibility and final state

Canonical scripts and evidence remain here; deployment copies are under
`<local-checkout>` on Ulmus.
Base source: Strata `99f3dbd0b21d1401b3769e0c0d963913607f380b`.
Owner image: `sha256:a1649d9812c7944dbbf880a33e272886a5b059bae22e65e713404a50aed46644`.
Image IDs, profile/default hashes, source overlays, sampled outputs, caps, telemetry, grader controls and
failed attempts are preserved. The executed extraction and owner-controller sources have snapshots under
`results/sources/`; maintained versions may contain later journal/output-capture hardening.

At **13:55:01 UTC**, the final capture (`after-second-checkpoint.json`, retained locally) shows the owned experiment
container removed, GPU memory at 2 MiB, host RAM available about 185 GiB, no swap, the same R550 driver,
same kernel and **280 W** power limit. No reboot, production routing, firewall or automatic startup change
was made. The preserved 27B vLLM container remains stopped with its original image and restart policy,
as it was when first inspected. Model originals and the unused Q8 download were preserved.
