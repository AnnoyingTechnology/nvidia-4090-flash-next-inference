# Decode exploration — 2026-10-04

## Current checkpoint — completed and selected

**Selected and serving:** `flash-iq3s-256k-vision-tune-owneradapt24`, same qualified
v4 image `ulmus/strata:99f3dbd-lendvram`, with `--adapt-swaps 24`. Original
`ownerswap` retains 96 swaps as rollback. Both launcher profile occurrences and
`run.sh` image selection are updated. OpenCode returned `READY`, natural stop,
no tools, through the normal private wrapper. One client model entry and the
253952-token client / 262144-token backend capacities are unchanged. Final GPU
snapshot: 23966 MiB, idle, 280 W and R550 unchanged.

All six chain markers are **0**: `decode-explore`, `decode-routing`, `decode-host`,
`adapt-batch`, `adapt-quality`, `adapt-vision` (suffix `-20261004.done`). No experiment
remains running. Historical in-flight instructions below are superseded.
Do not rerun completed chains after interruption. The owner subsequently authorized
committing and pushing this checkpoint; Git history records the publication revision.

Performance ABBA: same inputs/build/sampler; API 9/9 per launch. At 32K,
119.05 -> 120.10 tok/s (+0.88%); at 128K, 107.95 -> 112.55 (+4.26%). Two launches
per side; candidate ranges exceed baseline, narrowly at 32K. Equal-output
aggregate over the deck is 113.29 -> 118.69 tok/s (+4.77%). The preregistered
mixed-context median statistic is +6.16%; prefer per-context and equal-output
figures, not a universal gain. New 64K/96K/192K/256K rates are not established.

Quality: practical30 **29/30**, all natural and controls valid; original v4 also
29/30. Candidate fails `literal-endpoint`; baseline fails `unit-dependencies`.
This remains inside original IQ3 seed variation. Median completed-answer time
8.62 s vs 9.13 s, with different output trajectories. Vision **14/15**, all
natural, same as baseline; no transport errors. Maximum-budget image staging
3/3, final API 9/9. [Selection evidence](../results/public/adapt24-selection-20261004.json).

**Remaining ideas, not started:** cost-aware adaptive cache admission/update
budget could improve on a fixed 24 cap, but needs a diverse frozen workload;
higher-precision MTP requires new conversion/kernel support and a VRAM trade;
one economical near-maximum-context capacity/speed qualification remains.
Cross-layer reallocation and CPU weight expansion are deprioritized by this
round's evidence. No new branch is needed before using the selected improvement.

**Recovery:** start selected `owneradapt24` with `run.sh` and wait for readiness.
For batch rollback, start original `ownerswap` and change both launcher profile
occurrences. Older experimental runners restore resident vision or original v4;
restore the selected profile explicitly after using one. Diagnostic image
`99f3dbd-decodehost-diag` is unselected; its timers must not be used as production
speed evidence. The original engine working tree and maintained runtime patch
are unchanged by this round; its new C++ patch is diagnostic only.

## Earlier resumption checkpoint (historical)

Status: **active**, resumed by Julien after the completed v4 handoff. Read this
record before the historical handoff. Canonical checkout is this project; remote
stack is the existing deployment directory from the private client wrapper.
Selected serving profile remains `flash-iq3s-256k-vision-tune-ownerswap` (v4).
Read-only entry check: healthy 262144-token API, GPU idle, 24002 MiB VRAM,
280 W, R550 unchanged; no established API connection. No new code is adopted.

Current plan: bounded existing 32K/128K context probes with per-request decode
aggregation, then GPU-stage diagnostic stamps. Restore uninstrumented selected
v4 after each chain, including failure. Diagnostic throughput is not production
performance evidence. No broad sweep, model conversion, driver or power change.
No commit/push or upstream publication authorized in this resumed task.

Questions: what lies on the accepted-token critical path; whether host-memory
bandwidth or CPU unpacking deserves investigation; whether cache placement or
MTP draft accuracy has a measurable opportunity. Known dead ends stay closed.

Planned runner: `scripts/run_decode_diagnostic_chain.sh`; detached remote log
`results/decode-explore-20261004.log`, exit marker
`results/decode-explore-20261004.done`. The runner restores selected v4 (unlike
older experimental runners which restore resident vision). If interrupted,
inspect the marker/log and live container before rerunning anything.

Memory configuration: actual DIMM rate and effective bandwidth remain unknown.
Host DMI table exists but is root-readable; inspect only memory type-17 fields,
not machine serials or unrelated identifiers. No BIOS change is in scope.

## First checkpoint — diagnostic chain running

Detached launcher reported PID 174080. Aggregate mode has completed its first
32K and 128K cells. Current rates are diagnostic, not new performance claims.
Firmware SMBIOS type 17 reports four 49152 MiB modules, all configured at
3600 MT/s (rated 5600); raw narrow capture: `results/host-memory-dmi-20261004.json`.
This implies a theoretical dual-channel ceiling of 57.6 GB/s, not measured
inference bandwidth. No firmware setting changed. A sequential read diagnostic
source is prepared in `scripts/host_memory_read_probe.c`; it must run only after
the inference chain is complete, never alongside measurements.

Source audit: adaptive expert swaps are **within each layer**; allocation across
layers is inherited from the initial profile. Candidates are ranked by decayed
usage gain, not elapsed miss cost. This gives a concrete cache-allocation
hypothesis, but no demonstrated optimization yet. MTP runtime conversion/kernel
path is hard-wired to Q2_0 experts: higher-precision drafting is not a config-only
experiment.

## Second checkpoint — profiling complete, routing capture running

Decode chain completed with marker **0** and restored healthy uninstrumented
v4. Six aggregate and six stamped cells at 32K/128K each produced 512 tokens
(performance only). Public summary: `decode-diagnostics-20261004-summary.json`.
Median aggregate round: 20.70 ms, 2.385 tokens, verify 17.62 ms, draft 2.045 ms,
other 1.165 ms. CPU expert work 5.175 ms overlaps GPU work; stamped exposed
waitCPU is only 0.63–0.94 ms. The `waitB` bucket is 1.89–3.12 ms and **includes
the kernel-based host-to-device expert copy**. DMA mode is explicitly avoided
upstream: host CUDA calls while the GPU spins can deadlock on a driver lock.
Do not enable it as a shortcut. At 128K sparse scores/top-k takes 1.73 ms/window
versus 0.59 at 32K; bounded KV residency does not make all context work constant.

Sequential-read diagnostic completed without overlapping inference: 1 GiB,
first pass excluded; single-thread median 51.84 GB/s, twelve-thread 43.29 GB/s.
This short synthetic read/reduction is not inference bandwidth or proof that
more workers slow actual experts. Source and trials retained in public
`host-memory-20261004-summary.json`. CPU expansion is deprioritized because
current exposed CPU wait is small.

Next discriminator: routing trace on unchanged v4 image, profile `...-ownerroute`,
PID **177531**, runner `scripts/run_routing_diagnostic_chain.sh`; log/marker
`results/decode-routing-20261004.log` / `.done`. Restores selected uninstrumented
v4 on exit. Six existing 32K/128K performance requests record per-request trace
byte boundaries, then API checks. Compare per-layer allocation with byte-budgeted
frequency allocation on held-out requests offline. No placement policy deployed.

## Third checkpoint — allocation screen complete, host-gap diagnostic running

Routing chain marker **0**, all API checks **9/9**, restored selected v4.
Raw trace and request boundaries copied back; actual cache 8379 slots, profile
SHA matches local upstream data. Offline three leave-one-question-out folds
(each holds out both contexts) reduce unique missed expert groups by only
0.44%, 1.54%, 2.90%; absolute coverage gains 0.07–0.32 percentage points.
Even test-fitted greedy allocation only reduces misses 4.2–5.5%. These compare
static frequency policies, not the live adaptive cache; no speed claim follows.
The document is shared synthetic input, so broad generalization is unknown.
Decision: **do not implement cross-layer cache reallocation on this evidence**.
Summary: `results/public/routing-allocation-20261004-summary.json`.

One final attribution: aggregate counters leave ~1.1 ms/window outside verify,
commit/emit and draft. Diagnostic-only `patches/decode-host-diagnostics.patch`
adds timers for suffix selection, pending cache publication, penalty-history
staging and adaptation-thread join. It changes no algorithm. New image
`ulmus/strata:99f3dbd-decodehost-diag`, based on selected v4, is unselected.
Detached PID **179477** builds while serving is idle, then runs three 32K
performance cells and API checks; no compilation overlaps measurement.
Runner `scripts/run_host_diagnostic_chain.sh`; log/marker
`results/decode-host-20261004.log` / `.done`. Restore selected original v4 on
exit. Build failure leaves original serving untouched. No production change
has been adopted; preserve the uninstrumented image as selected.

## Fourth checkpoint — actionable host-gap finding

Host timers locate ~1.1 ms/window in `apply_pending`, awaiting expert-cache
updates/publication. Suffix lookup ~0.0002 ms, join ~0.006–0.012 ms; history
staging negligible. Current adaptation allows 96 swaps every four rounds;
large batches can outlast the ~2 ms drafting overlap. Hypothesis: **24 swaps
per adaptation** may fit that overlap, at the cost of slower residency changes.
This is an attribution-driven single candidate, not a broad knob sweep.

Planned experiment `scripts/run_adapt_batch_chain.sh`: unchanged uninstrumented
v4 image, ownerswap / owneradapt24 / owneradapt24 / ownerswap, existing identical
32K/128K six-cell inputs per launch, all API checks. Detached log/marker
`results/adapt-batch-20261004.log` / `.done`; restore original selected v4 on exit.
Pre-registered selection gate: >=3% aggregate median speed gain, positive launch
median separation at both contexts, no context median regression >3%, API 9/9
on every launch. If it passes, natural practical30 and image staging checks
remain necessary before selection; otherwise reject and keep baseline. Quality
outputs are never scored from capped performance cells.

A/B/B/A is now **running**, PID **181064**. Host diagnostic completed with
marker 0, API 9/9, and restored original v4 before the A/B/B/A started.
