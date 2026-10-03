# Claude Opus 5.5 review — 2026-10-03

Requested by the owner through **Claude Code**, model **`claude-opus-5-5`**,
**xhigh effort requested**. The successful result's model-usage record confirms
that model; the effort is recorded from the explicit CLI option. One turn,
195.05 seconds, with tools disabled and no model fallback. No independent web
verification or system changes occurred. The request, response JSON and invocation
provenance are retained privately in the canonical workspace.

CLI-reported usage: 7,271 input/cache-creation tokens and 18,792 output tokens,
including 15,133 thinking tokens. Its reported list-price estimate is $0.434;
this is not a claim of cash charged to the owner's subscription.

## How to use this advice

These are recommendations and hypotheses, **not new benchmark results or selected
changes**. Proposed thresholds/timeboxes are the advisor's suggestions. The owner
paused the work; do not execute them overnight or reopen the closed fork.

Corrections and qualifications for the next session:

- IQ3/Q4 speed differences do not isolate bandwidth from arithmetic/kernel costs.
  Overlapping stage timings and occupancy are insufficient to prove the critical
  path. The review's definitive wording about expert bytes is an inference.
- Sampled row cosines screen gross mismatches; they do not rule out every basis
  issue. A BF16-to-Q8 quantization-cell check establishes numerical consistency
  under a specified quantizer, not unique or exact checkpoint ancestry.
- Similar throughput does not prove identical MTP acceptance. Existing matched
  reports actually record **75.72% original / 75.98% head-only** aggregate draft
  acceptance. Exact sampling-equivalent verification still needs evidence; do not
  call a speculative setting quality-neutral merely from similar rates.
- The five-case disagreement deck is post-hoc and can reject a candidate, not
  select a winner. A complete multi-seed baseline is more useful for estimating
  variance. Do not turn incomplete generations into wrong answers or a survivor score.
- KTransformers is already in the [existing due-diligence record](research-and-pitfalls.md).
  That source audit records AVX2/AVX-512 paths; lack of Intel AMX alone is not grounds
  to dismiss Zen 4. Flash-Next/checkpoint/MTP compatibility remains unqualified here.
  The advisor had no tools and did not independently verify current project support.
- A default-mode change, a BF16-component download, hidden-state instrumentation
  or an alternate engine build is a proposal, not something performed at this pause.
  Broad agent reliability cannot be inferred from thirty functions. Selecting off
  as the default would need evidence appropriate to the actual client workload.

The current authoritative state and bounded resume plan are in
[session status](session-status-2026-10-03.md). The advisor's response follows
verbatim; the qualifications above take precedence when interpreting it.

---

# Second opinion: Qwen3.8-Flash-Next on 7900 + 4090 (advice only, no new measurements)

## 1. Diagnosis

**Facts from your evidence**
- IQ3 roughly doubles matched decode over Q4 (105.05 vs 57.65). Decode throughput is governed by expert bytes moved or cached, not arithmetic format.
- Within a 19–23 ms window, GPU-progress waits (~9 ms) exceed CPU cold-expert work (4.6–8.4 ms). PCIe at 26.9 GB/s is at the practical Gen4 x16 ceiling.
- On the 30 canaries, off is 29/30 at 3.40 s median and low is 28/30 at 9.12 s.
- Every recent tweak lands within ~1.5%. Your own unmatched baselines differ more than that (110.8 historical vs 100.6 fresh).

**Inferences, not proven**
- The critical path is probably GPU verify plus PCIe, with CPU cold work mostly hidden. That would explain why the CPU parallelism and thread sweeps did not reproduce.
- The largest *user-visible* gains are likely outside decode tok/s:
  - Mode choice: off is ~2.7× faster on canaries and was not worse on this deck.
  - Agentic prefill and prefix reuse, and behaviour past 32K resident KV. Your fixed 32K speed protocol measures neither.
- The text/vision profile gap is your only existing upper bound on what vision-lifetime work could buy. It is currently unmatched.
- At temperature 1, any logit perturbation reroutes trajectories. "Fixes two, breaks one" is exactly what noise looks like. You have no same-runtime seed-variance baseline, so 28/29/30 differences are unresolvable.

**Speculative**
- Above 32K, KV paging may contend with expert streaming on PCIe and degrade long agent sessions disproportionately.
- Per-position MTP acceptance may differ enough between low (T=1) and off (T=.7) that one depth is suboptimal for one mode. Your sweep history says to treat this sceptically.

## 2. Ranked experiments

Thresholds below are suggested pre-registrations, not derived values. Fix them before running.

**1. Head-local fidelity and ancestry test (deterministic, no sampling)**
- **Hypothesis:** under real IQ3 hidden states, the IQ3 head's error relative to the BF16 head is material, and the Q8_0 head removes most of it.
- **Measurement:**
  - Fetch only the original BF16 `lm_head` and embedding tensors. You already sourced BF16 PLE and projector.
  - Prove ancestry blockwise: every dequantized Q8_0 element must lie within half a quantization step of BF16 under its block scale.
  - Capture post-final-norm hidden states teacher-forced over ~20–50K positions of naturally finished low/off text, code and vision answers.
  - Offline, compute logits with the BF16, IQ3 and Q8 heads. Report KL, top-1 mismatch, and change rate of the top-k20/p.95 nucleus set.
- **Boundary:** this measures head-local error only. It cannot certify full-model quality.
- **Stop:** if the IQ3 head's top-1 mismatch vs BF16 is below ~0.1% and nucleus changes are rare, close the head variant with no further generations. If hidden-state capture needs more than ~2 h of engine work, abandon this test and decide the variant from the seed baseline (experiment 2) and its cost.

**2. Seed-variance baseline**
- **Hypothesis:** same-runtime seed flips on the 30 canaries are at least as large as the variant differences seen so far.
- **Measurement:** original IQ3, low and off, two extra seeds. That is roughly 7 minutes per seed pair, with natural stop required.
- **Boundary:** these are bounded functions, not agentic qualification.
- **Stop:** if ≥3 cases flip between seeds, record that this deck cannot select precision variants. If off stays ≥ low across seeds, document off as the DevOps/code default with low as escalation. This is the same model, so it involves no fidelity sacrifice.

**3. Matched text vs vision profile A/B**
- **Hypothesis:** the ~1.94 GiB vision residency costs ≥8% decode.
- **Measurement:**
  - Log cache arena size and hit rate for both profiles.
  - Use identical fixed-length prompts in ABAB order, ≥3 repetitions, same warm-up.
  - Take one image-latency sample.
- **Stop:**
  - If the gap is <5% or within run spread, close vision-lifetime redesign permanently.
  - If it is ≥8%, allow one design memo plus one time-boxed prototype session (cache refit on image arrival with stable pointers/graphs).
  - Reject the prototype if image time-to-first-token rises by more than ~100 ms or any graph/pointer instability appears. Never use per-image reload.

**4. Real-workload latency decomposition**
- **Hypothesis:** in agentic use, prefill, prefix misses or >32K paging account for ≥30% of wall time.
- **Measurement:**
  - Deterministically replay 3–5 private OpenCode sessions.
  - Per request, log prompt tokens, reused-prefix tokens, prefill ms, and decode tokens and ms.
  - Add fixed-length decode at 32K, 64K and 128K.
- **Boundary:** exact KV reuse is quality-neutral. Any template fix must leave the rendered prompt hash semantically identical.
- **Stop:** if decode is >70% of wall time, reuse is >90%, and 64K decode is within ~10% of 32K, close prefill/paging work.

**5. Bounded critical-path attribution**
- **Hypothesis:** GPU verify/PCIe finishes last in ≥70% of windows, and the CPU cold path is near the memory-bandwidth roofline.
- **Measurement:**
  - One trace of ~300 windows, using engine timestamps or nsys.
  - Classify which resource finishes last in each window.
  - Compare effective cold-expert GB/s against a measured host bandwidth figure.
  - Derive per-position MTP acceptance from the same trace.
- **Timebox:** ~3 h, no sweeps.
- **Stop:**
  - If no component holds >30% of the critical path with a concrete, exactness-preserving remedy, close decode work. File any finding upstream; do not fork.
  - Change MTP depth only if the trace predicts >5% gain and a fresh confirmation run reproduces it.

**6. Embedding+head launch, only if experiment 1 shows material head error**
- First confirm whether the 675 MB embedding is host-resident (lookup-only) or consumes VRAM.
- **Stop:** close it if it shrinks the expert cache, or if the BF16 component distance shows the IQ3 embedding is already close.

## 3. Challenge to dense restoration

- **What the screen shows:** row cosines rule out rotation or permutation mismatch, nothing more. The blockwise Q8_0-vs-BF16 check proves ancestry exactly and is cheap.
- **Co-adaptation risk:** if GSQ/RCO tuned scales, norms or other non-quantized parameters end-to-end, the IQ3 head may be co-adapted to the quantized trunk. Then local closeness to BF16 is necessary but not sufficient. Check the method description. If that tuning is confirmed, treat the hybrid as a new, uncertified model and close it unless it shows unusually strong non-regression evidence.
- **The five-case disagreement deck** was selected because those cases differed, so regression to the mean is built in. Five cases × two seeds can **reject** (head-only failing the cases it "fixed") but cannot **select**. Run it, if at all, after experiment 1.
- **MTP:** with exact sampling-equivalent verification, a head change alters only acceptance, not the target distribution. Confirm that your verify path is exact. The 100.3 vs 100.6 matched result suggests acceptance did not change.
- **Select only by dominance:**
  - ancestry proven, and
  - head-local error materially reduced, and
  - no matched speed/VRAM cost, and
  - 9/9 API, and
  - low/off canary non-inferiority within the measured seed variance, and
  - vision non-regression.
- **Close** if any of these holds: ancestry fails, IQ3 head-local error is already negligible, co-adaptation is confirmed, or there is any matched cost.

## 4. Bootstraps

I cannot support a missing strong bootstrap from verifiable primary sources for this model on this hardware.

**Research lead only: KTransformers (kvcache-ai)**, a CPU/GPU hybrid MoE engine.
- Its flagship CPU kernels target Intel AMX, which Zen 4 lacks.
- Support for this architecture (PLE/ngram), for MTP and for CUDA 12.4 is unverified.
- Verify from source before considering any build.

**Defer all alternate engine builds, ExLlamaV3 included, until experiment 5 reports.**
- Entry bar:
  - source evidence of per-expert (not per-layer) GPU caching or an equivalent,
  - MTP plus this architecture,
  - a critical-path estimate at or above current Strata.
- Every measured alternative is ~4× slower. A full-layer offload design must beat an adaptive expert cache plus MTP, which is a weak prior.

## 5. Next-session order

1. Verify live state and that nothing is running.
2. Experiment 1: ancestry and head-local test. It may close the precision line with zero generations.
3. Experiment 2: seed baseline. Make the off-default decision.
4. Experiment 3: text/vision A/B.
5. Experiment 4: workload decomposition.
6. Experiment 5: time-boxed trace.
7. Experiment 6 only if the head line survives.

Keep the partial seed-7 capture labelled as incomplete. Resume it only on an exact fingerprint match.

**Do not reopen:**
- the eddoursul fork or its CUDA 13 path
- CPU activation-quant parallelism
- unconfirmed thread or speculation sweeps
- BF16 PLE restoration
- per-image reload
- stock llama.cpp, ik, MoE-cache or ik-MTP Q4 paths
- CUDA-13 vLLM wheels on R550
- pruning or router approximations
- raising effort to escape caps
- Q4 as oracle
- local full-size or Q8 reference runs
- 397B and DeepSeek probes until this decision closes
