# Personal Flash-Next abliteration qualification

Owner request, 2026-11-08: adopt an abliterated Flash-Next on Ulmus using the same quality bar as the
27B dense qualification. Regressions beyond measured variation in canaries, tests or benchmarks are
unacceptable. A complete Huihui model is authorized when it can replace the existing service cleanly.

## Final decision: adopted after owner acceptance of the decode cost

Julien explicitly accepted the measured 3–4 tok/s long-context decode cost as insignificant compared
with removing refusals, while retaining the quality benchmark requirement. The tested weight-level
candidate is selected by `qwen3.8-flash-next.service` and both launcher copies. The normal OpenCode
low-variant launcher returned `READY`. The service is active, remains disabled at boot, and preserves
256K context, vision, loopback binding and the 280 W policy. See [the adoption record](huihui-adoption.json).

The selected model uses the official Huihui v2 edits, with missing tensor formats requantized into
the existing GSQ types. It is a derived quantization with **no runtime projection**. The original model
and profile remain available for rollback; the installed unit and launchers were backed up before switching.
No further benchmark runs or variants are authorized.

## Initial decision before the owner accepted the tradeoff

The interrupted baseline check was completed during the owner's ten-minute bounded resume.
At that point the original serving profile remained selected and the owned evaluation container was stopped.
No additional suites or variants are authorized.

The final matched long-context decode samples were:

| Cache-history position | Baseline fresh starts | Huihui fresh starts | Median change |
|---|---|---|---|
| First cold 261567-token prompt | 148.5, 146.2 tok/s | 144.7, 144.4 tok/s | −1.90% |
| Second cold prompt, warmed expert cache | 196.4, 193.9 tok/s | 190.8, 191.1 tok/s | −2.15% |

Inputs and 307-token answers match; every request recovered all sixteen facts with zero prompt-cache
reuse. The slowdown repeats in both positions and exceeds the measured baseline start-to-start spread
(approximately 1.56% and 1.28%). This caused the initial rejection; the owner subsequently accepted it.
The interrupted `baseline2` report is retained separately; `baseline-resume` is its complete replacement.

All other functional gates passed. The complete IFEval repeat scored baseline/candidate **71/80 → 72/80**
with no capped responses; the earlier capped case completed naturally. HumanEval was **38/40 → 39/40**,
knowledge **110/168 → 111/168**, and practical code **27/30 → 28/30 off**, **27/30 → 29/30 low**.
Benign English and Chinese historical questions refused by the original were answered by Huihui;
this confirms the intended behavior change underlying the owner's adoption decision.
See [the response-free evidence summary](abliteration-summary.json). Remaining sections preserve the
qualification history; their running/queued wording describes the earlier checkpoint, not current work.

The initial checkpoint used `flash-iq3s-256k-vision-tune-owner20261108`; the adoption record supersedes it.
The GPU remains at 280 W. All candidates use the selected runtime image, model/API identifiers,
256K context, RAM-resident experts/PLE, MTP, 15 workers and existing elastic vision budgets.
The work is confined to personal Ulmus; the work machines are outside scope.

Remote serving root: `~/Documents/MachineLearning/Qwen38-Flash-Next-Ulmus/stack`.
Progress and raw evidence are under `results/`. Inspect the running processes and reports before
resuming; all qualification drivers have now completed and should not be restarted.

## Huihui-derived runtime vector

Artifact: `alesha-pro/Qwen3.8-Flash-Next-abliterated-GSQ-RCO-Strata-GGUF` at
`d4af3be5701549435e0770d625f79dd2def1358f`, file
`Huihui-Qwen3.8-Flash-Next-refusal-direction-r.gguf`, 483520 bytes,
SHA-256 `59f9ae8b4372107ae79044278a4406bdfe8f8861fe599aa5848515f0d072be38`.
It is derived from Huihui v1, not v2. The existing engine supports projection directly.
Profile `flash-iq3s-256k-vision-tune-huihui20261108` uses strength 1.0, layers 4–44,
`project`, `per-layer`. Per-request on/off selects the paired arms in one owned evaluation container.

Completed screens: strict IFEval baseline/vector **72/80 → 75/80**; MMLU-Pro
**92/140 → 93/140**. The screens exchange individual successes and failures; repeats are queued.
All 16 distributed facts were retrieved from the near-256K document in both arms.
Four cold 32K prefill measurements per arm show a consistent approximately 1.5% projection penalty.
The vector has not earned adoption under the owner's performance requirement.

`abliteration_sequence.py` runs the main serial stages. `abliteration_followup.py` then repeats every
screen disagreement and checks operational decisions, multi-turn tools and independent histories.
The original vector evaluator is preserved as `abliteration_gate_vector_v1.py`; its byte hash matches
the vector reports. The extended `abliteration_gate.py` also supports single-arm weight candidates.

## Derived Huihui v2 weight candidate

Official source: `huihui-ai/Huihui-Qwen3.8-Flash-Next-abliterated-v2-GGUF` at
`6e298f56319a5735f88ae952dd27222369f2f44a`. Its 3561572544-byte patch has SHA-256
`f3a42f213edb9117fd7f3873e0b29a9a94033cb49b91e100e792f6344adec752`.
All downloaded assets are verified against pinned LFS hashes or Git blob IDs.

The official patch directly covers 45/96 intended GSQ dense tensors. The missing 51 use Q4_K or IQ4_NL.
Their published BF16 Huihui tensors were quantized with the pinned llama.cpp CPU quantizer into
the existing GSQ tensor formats. A supplemental patch feeds those entries to the unmodified official
patching program, mode 2, layers 0–47. This is a **derived quantization**, not an official Huihui release.

Integrity verification passed: exactly 96 dense tensors changed, all 1127 other first-shard tensors
are byte-identical, metadata is equal, and the ngram shard and vision projector share the original
inodes. The native pack was rebuilt. Target, supplemental and source checksums are retained in
`results/huihui20261108-weight-candidate-integrity.json` and model manifests.

Candidate: `flash-iq3s-256k-vision-tune-huihuiv220261108`, with no runtime projection.
`qualify_huihui_weights.py` waits for the vector follow-up, switches only owned evaluation containers,
runs two fresh starts per arm in ABBA order, then the complete matched quality/feature/tool gates.
Its progress is `results/huihui-weight20261108-sequence.log`; completion is explicitly marked in
`results/huihui-weight20261108-complete.json`. A completed driver is evidence collection, not adoption.

The weight candidate's ABBA performance phase completed: baseline/candidate pooled decode
**133.05 → 134.60 tok/s**, cold 31803-token prefill **5126.70 → 5117.55 tok/s**.
All request hashes, runtime image and chat template match. The +1.16% decode and −0.18% prefill deltas
are within the observed variation; no speed gain is established. Per-start decode medians were
132.20/133.05 baseline and 130.00/136.05 candidate.

The first weight-level cohort collected 70/80 IFEval passes (one capped response) versus 72/80,
93/140 knowledge versus 92/140, practical code 28/30 off and 29/30 low versus 27/30 in both modes.
The API, multi-turn tools, vision, history isolation and sixteen-fact retrieval checks passed.
The incomplete IFEval response and score loss prevent adoption until the full-cohort repeat resolves them.

`dense_bar_sequence.py` follows that driver with matched baseline/candidate runs of 40 frozen HumanEval
tasks and another two MMLU-Pro questions per category, bringing knowledge coverage to 168 questions.
HumanEval uses its official tests in the existing isolated grader, with correct and deliberately wrong
program controls. The frozen additional deck's SHA-256 is
`0798d5750755cb7c0e332050807b3e8c051204975e62c5af3811d97448d87cdc`.
Its completion marker is `results/huihui-weight20261108-dense-bar-complete.json`.

Dense-bar results: HumanEval **38/40 → 39/40**, extra MMLU **18/28 → 18/28**, thus total knowledge
**110/168 → 111/168**; all natural stops. `repeat_weight_ifeval.py` then repeats all 80 IFEval cases
on fresh baseline and candidate starts, rather than replacing the cohort with selected disagreements.
Its completion marker is `results/huihui-weight20261108-repeat-complete.json`.

`long_context_gate.py` follows with matched fresh starts, identical three-prompt warmups, and two cold
near-native-window requests per arm. This resolves a large decode-rate difference in the first retrieval
probe, where the baseline and candidate had different preceding cache histories. Completion is
`results/huihui-weight20261108-long-complete.json`. The original cold-prefill fixture is 261560 tokens,
and all arms returned the same 307-token sixteen-fact JSON answer. Retain the original timings alongside
the controlled follow-up; do not claim the earlier difference is explained until the follow-up finishes.

## Adoption requirements

Compare complete cohorts and natural stops. Retain all disagreements, caps and baseline variation;
do not treat a nonsignificant difference as proof of universal equivalence. Repeat material losses.
Exact operational, API, tool, vision, history-isolation and context canaries must pass. Compare matched
decode, cold prefill and resource use against the fresh baseline before changing the service.

After qualification, preserve the baseline profile and model, back up the installed unit and launchers,
update their selected-profile assertions together, and verify the normal OpenCode path. This is complete;
the adoption record above supersedes the earlier checkpoint's pending selection.
