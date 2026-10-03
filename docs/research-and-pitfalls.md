# Ulmus inference candidates

Research snapshot: 2026-10-03. Published speeds below are authors' observations on their hardware, not Ulmus measurements. Runtime selection must use local measurements with the same model, prompt, context and output length. Strata was one discovery lead; it is not a requirement.

Observed hardware: Ryzen 7900 (12 physical cores, AVX-512/VNNI/BF16), RTX 4090 (24 GiB, SM89), 192 GB installed RAM (187 GiB usable), PCIe 4 x16. The GPU power limit remains 280 W and the NVIDIA driver remains 550.163.01. No swap is configured. Current RAM capacity enables full expert residency and full PLE/ngram residency; bandwidth still limits CPU expert work.

Owner constraints, declared 2026-10-03: optimize c1 first; consider c2 only with an excellent compromise. Preserve quality, using published full-precision benchmark references and local quantized-model comparisons with objective canaries. Do not run a Q8 or full-size reference locally. A Q8 download completed before this clarification, but those files have never been loaded. DeepSeek 4.1 Flash is a later experiment, recorded separately in the Ulmus skill backlog.

| Candidate | Relevant implementation | Qualification on this host |
| --- | --- | --- |
| [Strata](https://github.com/Niko1221/Strata) | Flash-Next-specific runtime; GPU expert cache, AVX-512 CPU misses, streamed prefill, MTP, prompt lookup, conversation state, native GGUF | Built CUDA 12.4 / SM89; expert, attention and state component checks passed; full-RAM Q4 and GSQ inference measured; see both dated reports. Native `--ple-io ram` supplies the ngram placement we need. GPU vision and effective owner defaults now pass bounded API/canary checks. |
| [ik_llama.cpp](https://github.com/ikawrakow/ik_llama.cpp) | CPU kernels, CPU MoE with GPU prefill, Qwen4Exp and Qwen3.5, MTP | Built CUDA 12.4 / SM89 with explicit AVX-512 flags. Installed 397B GGUF has no F16 tensors, so the documented Unsloth XL/F16 objection does not apply. Q4 and 397B loaded and measured; shared Q4 MTP also tested, with unresolved API canary failures. |
| [GenerelSchwerz llama.cpp MoE cache](https://github.com/GenerelSchwerz/llama.cpp/tree/moe-cache) | Frequency-aware/LRU GPU expert cache, grouped CUDA decode, host pinning, speculative context controls; Qwen4Exp and Qwen3.5 | Source acquired and all 3,648 tracked paths verified after transfer. CUDA 12.4 build and same-Q4 local baselines completed. Adds a strong dynamic-cache alternative to both stock llama.cpp and Strata. |
| [llama.cpp](https://github.com/ggml-org/llama.cpp) | General GGUF runtime; mature server and multimodal interfaces; reference CPU/GPU split | Built from the same pinned reference used by Strata. Same-file baseline measured. |
| [ExLlamaV3 / TabbyAPI](https://github.com/turboderp-org/exllamav3) | Flash-Next, vision, MTP, quantized KV, ngram RAM residency and AVX-512 CPU expert offload; source install supports CUDA 12.4 | Added in the resumed source audit; not previously qualified. Master pinned to `d3739fd393337b1ff4d6c2a342b12f0c87a9592f`. Needs separate EXL3 weights and c1 qualification; its CPU offload selects whole MoE layers, unlike Strata's per-expert cache. Published two-5090 speeds are not a 4090 estimate. |
| [Unsloth llama.cpp MTP fork](https://huggingface.co/unsloth/Qwen3.8-Flash-Next-GGUF/blob/38bb39ee97821de2c9009abb7e93950eec396e66/MTP/README.md) | Published standalone shared Q4 MTP GGUF; supported fork supplies Qwen4Exp graph and tensor sharing | Strong remaining bootstrap. Sidecar verified and loaded in ik_llama; fork itself not yet built/qualified. The earlier presumed converter gap is resolved. |
| [Single-GPU Flash-Next vLLM](https://github.com/DominikBucko/qwen38-flash-next-3090) and [dual-GPU version](https://github.com/DominikBucko/qwen38-flash-next-2x3090) | AutoRound INT4 target, FP8 PLE, CPU/GPU cold experts, streamed prefill, MTP, hybrid-state fixes; single 24 GB profile exists | Strong additional bootstrap. Published single-GPU image needs CUDA 13 / driver 580. Current driver is incompatible with that released path; a supported rebuild or a separately authorized driver migration is required before qualification. Do not copy an old overlay onto a different vLLM version. Its 64 GB disk tier would be replaced with full RAM residency here. |
| [KTransformers / KT-Kernel](https://github.com/kvcache-ai/ktransformers) | Hybrid CPU/GPU experts; AVX2/AVX-512 and SM89 supported; native BF16, FP8, GPTQ INT4 and GGUF CPU paths | Potential 397B candidate, not dismissed for lacking AMX. Documented GGUF route still requires a separate SGLang-compatible GPU checkpoint; no directly qualified Flash-Next recipe found in inspected workflow. Need validate architecture, loader peak RAM and a suitable checkpoint before a large additional download. |
| [Flash-Next 24 GB SGLang](https://github.com/HaberstrohSystems/qwen3.8-flash-next-24gb-sglang) | Elastic expert cache, mixed CPU/GPU, quality oracle, MTP; reported ~56 tok/s | Published path targets SM120 Blackwell, CUDA 13 and custom 2-bit experts. Useful design and validation reference; not a drop-in RTX 4090 recipe. |
| [HyperQwen](https://github.com/syv-ai/HyperQwen) | vLLM kernel/speculation improvements; continuation of the earlier 27B bootstrap | Relevant to preserving/updating the 27B fallback. No qualified Flash-Next offload profile found; current 27B environment is preserved. |
| [NInfer](https://github.com/Neroued/ninfer) | Specialized dense/compact-MoE runtime | Current source requires SM120a / RTX 5090 and has no weight offload. Not a supported Ulmus route. |
| [Splash](https://github.com/incoai/splash) | Hybrid MoE inference on Apple hardware | Metal / Apple M3+ runtime; not executable on Ulmus. |
| [Flash-Next inference research](https://github.com/starsder/qwen3.8-flash-next-inference-research) | Detailed PLE, expert prefetch, CPU/GPU placement experiments and withdrawn incorrect results | Useful failure evidence, not a qualified general runtime. Published conservative baseline is explicitly experimental and reports about 19 tok/s on a different 16 GB system. Do not adopt unverified research switches. |

## What changes for 24 GiB / 192 GB

- Keep every routed expert in host RAM; no low-RAM resident budget and no decode-time expert disk tier.
- Lock the complete PLE table in RAM and verify startup residency. RAM capacity does not justify gratuitous copies of weights.
- Size the expert cache from VRAM left after dense weights, MTP, KV and working buffers. Leave a measured safety margin for actual requests.
- Test 6, 8 and 12 CPU workers and the GPU share of cold experts. Measured PCIe host-to-device bandwidth is 26.9 GB/s; an automatic share chosen for another CPU can be wrong.
- For long context, compare pinned host KV with a bounded VRAM window against full VRAM KV. Use remaining VRAM for experts when it produces a measured benefit.
- Tune prefill chunk size and MTP acceptance together with decode and memory. Preserve precision and expert routing; do not use the experimental speed projection.
- Compare the existing Unsloth Q4 checkpoint with GSQ IQ3_S as separate quality/performance points. Q4 needs rounded small-projection conversions. The resumed GPU vision canaries pass for both; broader vision quality remains unqualified.

## Upstream vLLM re-check

The earlier blanket maturity conclusion is stale. [PLE UVA support, PR 54371](https://github.com/vllm-project/vllm/pull/54371), merged on 2026-09-09. However, [block-table bounds PR 54296](https://github.com/vllm-project/vllm/pull/54296) remains open; inspection of current `vllm/v1/worker/block_table.py` still found the unguarded load from that diff. This is evidence about that source path, not proof that every current Flash-Next configuration fails. The dedicated vLLM projects include their own scheduler/state fixes and deserve separate qualification.

All operational artifacts are in this directory and synchronized to `<local-checkout>` on Ulmus. Model originals and the existing 27B service are preserved. New test endpoints publish only on Ulmus loopback.

## Preliminary measurements, historical checkpoint

The first bounded experiment stopped at its checkpoint. Read the first local checkpoint for that record and [follow-up results](benchmarks-and-quality.md) for the resumed work and final profile selection.

Strata GSQ IQ3_S measured 112.55 tok/s across six 512-token thinking-sampler runs, versus Q4 60.65. Uncached 32K prefill was 4774.6 and 4377.8 tok/s respectively. Same-Q4 plain engine baselines were 23.63 stock llama.cpp, 24.38 ik_llama and 21.91 MoE-cache. An additional ik shared-Q4-MTP configuration measured 24.55 sampled / 28.56 greedy and failed strict API canaries; other configurations remain unexplored.

The 397B partial-offload probe fits and measured 12.42 tok/s, with ~3K prefill at 68.81. Quality is not qualified. c2 history parking works, with 110.0 aggregate tok/s, but FIFO queues the second request for the first request's duration.

Local Q4 / GSQ screens were MMLU-Pro 100/140 versus 92/140; IFEval 69/80 versus 74/80; selected AIME 4/4 each; selected code 2/3 each. Sixteen distributed facts were recovered at 32K/128K/256K by both. Vision OCR failed one character. Preserve the mixed evidence; no full-precision parity or overall quality winner is established.

## Published quality reference

[DASLab's paired BF16 / GSQ results](https://huggingface.co/ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-GGUF#results) report BF16 to IQ3_S: AIME25 100.00 to 100.00, GPQA Diamond 91.92 to 92.93, and LiveCodeBench v6 87.43 to 86.86. The IQ4_NL ngram table is included in these evaluations. Above-reference scores are benchmark variance, not evidence of improvement from quantization. This is stronger evidence than an unrelated full-model headline, but does not certify our runtime or our sampled protocol. Keep published and local scores separate.

[Qwen's generation guidance](https://huggingface.co/Qwen/Qwen3.8-Flash-Next#best-practices) recommends stochastic thinking sampling and sufficient output room. The final profile should supply suitable generation defaults; an empty Strata sampling configuration decodes greedily. A fixed seed does not make adaptive CPU/GPU expert placement exactly reproducible because CPU and GPU arithmetic round differently.

## Resumed experiments, 2026-10-03

The owner resumed work after the preliminary checkpoint and explicitly prioritized DevOps, SysAdmin and code,
then general agents, vision, knowledge and practical thinking. Pure math has low selection weight.
[QUALITY-REFERENCE.json](../QUALITY-REFERENCE.json) records the governing published full-size reference,
unmatched protocol details and local qualification requirements.

- Original BF16 PLE table: the pinned official checkpoint stores 128 shards, totaling 102.4 GB. The extraction
  downloads their exact byte ranges, not the full target checkpoint. Main weights remain GSQ IQ3_S. The isolated
  loader image applies [upstream PR 586](https://github.com/Niko1221/Strata/pull/586), pinned to
  `36f829da8bc1396e8c8198e3c2e0c147c78d14ba`; reader self-tests and real rows pass.
  The knowledge attempts produced 112 correct completed answers versus 115 with IQ4_NL, with five capped
  cases in each; full-deck accuracy is unqualified and no quality recovery has been demonstrated.
  Matched text speed is 107.5 tok/s versus the baseline's 116.4 and 111.15 before/after runs.
  Keep the restored table optional; retain IQ4_NL as the default.
- CPU intermediate quantization: [upstream PR 500](https://github.com/Niko1221/Strata/pull/500), pinned to
  `8eacd97390dc286e81af046f4a9bd8332c84ed1d`, passes the retained synthetic native-pool parity test.
  Its first six-run 107.4 tok/s median versus a subsequent 105.9 baseline is insufficient evidence to adopt it.
- [eddoursul's Strata fork](https://github.com/eddoursul/Strata/blob/custom/docs/COMPARISON.md) is a serious
  remaining A/B candidate. Published single-3090 IQ3_S thinking decode around 111 tok/s is close to the current
  Ulmus result, while its Q4 result suggests a useful path. Its dramatic gain compares an older upstream base
  without Q4 kernels; Ulmus already runs a newer base. Neither dual-GPU nor cross-CPU numbers transfer directly.
  The pinned native engine now builds for SM89/CUDA 12.4 behind the existing qualified API/vision frontend.
  The compatibility patch guards CUDA 13 batch copies and cuBLAS 12.5 grouped GEMMs; older libraries use
  ordered copies and the fork's existing per-expert GEMM/side-stream fallback. This loses newer batching
  features, so it is an adapted-fork A/B rather than the author's original software configuration.
  All **9 component checks pass**, including exact ordered copy checks, four heterogeneous GEMM stream
  configurations, sampler, PLE reader, QSA/GDN/router, and real native IQ3/Q4 experts. End-to-end API,
  quality and performance remain separate gates. Its older engine lacks `--kv-resident` and treats
  `auto:32768` as zero; experimental profiles instead use 32K context and numeric `--prefill 32768`.
  Both engines reduce that prefill ceiling as needed. The matched Q4 32K A/B passes all nine API
  checks per engine but measures **33.65 tok/s fork vs 57.65 upstream**, with similar ~4.4K prefill.
  The same IQ3 comparison measures **46.60 versus 105.05 tok/s**. The fork is slower for both tested quants.
  It is not selected. These adapted-build results do not establish the author's newer-CUDA performance.
  Build with `bash scripts/build_eddoursul.sh`; retain the component and matched measurement records.
- [ExLlamaV3's CPU-offload documentation](https://github.com/turboderp-org/exllamav3/blob/d3739fd393337b1ff4d6c2a342b12f0c87a9592f/doc/env_vars.md#cpu-moe-offload)
  specifies mul1-codebook eligibility, CPU resident experts and GPU streamed prefill. It is a plausible supported
  bootstrap, not a measured performance improvement. A separate EXL3 download and source build remain.

The public GSQ repository's `eval_model.py` uses generic lm-eval completions and greedy generation;
it does not establish the exact Flash-Next AIME/GPQA/LiveCodeBench release protocol. Do not silently apply
that generic script's defaults to the published paired results.

## Vision weights on demand

The earlier [4090 27B A/B](https://github.com/AnnoyingTechnology/nvidia-4090-llm-inference/blob/main/results/vision-offload-ab.json)
measured 1.03277 seconds with the pinned-RAM vision blocks versus .98371 seconds resident: **49.06 ms**
extra on that image/cell. Its roughly 879 MiB BF16 tower copied each block/merger to the GPU only for
image forward. The offloaded profile remained stable; this is separate hardware/runtime evidence, not
a measured Flash-Next implementation. Host-mapped zero-copy was much slower than bulk staging there.

Current Strata holds about **1.94 GiB** in its persistent vision worker, including about .85 GiB weights
and maximum-image workspace. It warms that workspace before sizing the main fixed expert-cache arena.
Unloading the worker does not dynamically enlarge an already allocated expert cache. A useful
implementation must stage weights with bounded workspace, or explicitly coordinate shared memory and
cache invalidation; CPU image inference is a different, much slower measured alternative.

[llama.cpp discussion 20246](https://github.com/ggml-org/llama.cpp/discussions/20246) identifies a concrete
new bootstrap: [PR 28320](https://github.com/ggml-org/llama.cpp/pull/28320), from CachyLLama, frees the LLM
scheduler's scratch, encodes with a temporary GPU projector, then retains host-owned embeddings through
`mtmd_batch_set_ctx`. Its server switch is `--mmproj-vram-swap`. The reported V100 path spends substantial
time parsing/initializing the projector; it is not evidence of a 50 ms Flash-Next path. Strata's custom
persistent graphs and monolithic expert allocation do not directly use those llama-context APIs. Preserve
parsed host weights and qualify encoder embeddings, peak memory, repeated images, cancellation and
maximum image geometry before selecting a related design here.

The [GSQ release card](https://huggingface.co/ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-GGUF)
also advertises a separate Coder model with 256 of 512 experts retained per layer. It is a task-specialized,
pruned candidate requiring separate code and general-task qualification, not a substitute for the current
unpruned target. Its linked card was unavailable in the final web fetch; no execution or quality claim follows.

## Targeted precision diagnostic

Observed header inventory: 1224 identical tensor names/shapes, with 906 source type differences.
The IQ3 token embedding is IQ4_XS (337.72 MB) versus Q4 Q8_0 (675.43 MB); the IQ3 output head is
Q6_K (521.47 MB) versus Q4 Q8_0 (675.43 MB). Restoring these two to the available Q4 precision would
add about 338 MB embedding storage and 154 MB output-head storage, before runtime workspaces/cache
effects. This is a **planned diagnostic**, not an implemented or measured recovery. The embedding's
actual GPU placement must be checked before treating all added storage as VRAM.

IQ3 routers are already BF16; hyper-connection projections are mostly BF16, while Q4 source stores
many as Q8_0 and rounds compatible projections into its runtime pack. Source bit-width labels therefore
do not monotonically rank all dense components. Same types do not prove equal values. Preserve common
tensor basis/layout, shape/type checks, target routing, sampler and PLE; a loader-supported overlay and
complete paired canaries are required before selecting any restoration. Do not mix expert matrices
from different quantization recipes without establishing their basis compatibility.

A sampled dense-row coordinate screen reads 15.23 MB of tensor payload without
inference. IQ3/Q4 output heads have mean cosine **.999814** over 518 rows,
relative L2 **.01928**; embeddings have mean cosine **.996951**, relative L2
**.07800** over 518 rows. Adjacent output hyper-connection matrices also align
closely, and the full norm vector is identical. The five tokenizer files have
identical content hashes. This screens out a gross hidden-state rotation/layout
mismatch; it does not establish exact original-BF16 ancestry or certify a mixed
model. The existing head override is a potential small diagnostic; embedding
replacement requires a supported loader extension. Neither has been selected.
[Sample evidence](../results/public/dense-row-compatibility.json)
