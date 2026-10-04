# Architecture and pinned inputs

Observed campaign hardware, 2026-10-03: Ryzen 7900 (12 physical cores, 24 threads),
192 GB installed RAM (187 GiB usable), one RTX 4090 (24,564 MiB reported VRAM,
SM89), PCIe 4 x16, no swap, 280 W GPU limit. The recorded driver is 550.163.01;
engine builds use CUDA 12.4. Four 48 GB DDR5 modules are owner-declared;
current DDR5 frequency and effective CPU-memory bandwidth are not measured.

## Source and image pins

| Component | Pin |
|---|---|
| Strata | `99f3dbd0b21d1401b3769e0c0d963913607f380b` |
| llama.cpp reference | `3cf03257f219afbe7334045ff7c6a06ac68c627d` |
| NVIDIA CUDA base | `sha256:622e78a1d02c0f90ed900e3985d6c975d8e2dc9ee5e61643aed587dcf9129f42` |
| Recorded base engine image | `sha256:8f933353f8a8c5617c8dc37775db03bf168e4a483f20ce34197f892b54cc7c05` |
| Recorded owner API image | `sha256:a1649d9812c7944dbbf880a33e272886a5b059bae22e65e713404a50aed46644` |
| Engine binary in both recorded images | `a4d403dc589c656121c33960314da0fc9e728c60802a07f51d1a62e1cbf5c676` |
| Official MTP / optional BF16 table source | `Qwen/Qwen3.8-Flash-Next@de4b8e4d43b917e7706784d8bb445c9af86a3540` |
| GSQ target/projector source | `ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-GGUF@ed59f92082b1e93c0e96d60a8b11aab089b52f09` |

Rebuilding source can produce different image IDs. These IDs identify the measured
images, not published pullable images or a bit-reproducible build guarantee.
The owner image adds only hash-locked validator dependencies; no inference or HTTP
source changes. The optional BF16 loader and CPU-quantization overlays are retained
as upstream patches with their MIT notice and pinned heads in the benchmark report.

### Selected lend-VRAM v4 — 2026-10-04

Later qualification selects profile `flash-iq3s-256k-vision-tune-owneradapt24`,
using the identical v4 image/binaries/weights below, with `--adapt-swaps 24`.
The original `ownerswap` profile retains its 96-swap default for rollback.
Matched ABBA gives +0.88% at 32K and +4.26% at 128K; practical30 29/30 natural,
vision 14/15 natural, all API and maximum-image staging checks pass.
[Evidence and limitations](exploration-2026-10-04.md).


`Dockerfile.lend-vram` adds the engine's CUDA VMM cache tail, vision LOAD/UNLOAD
and pinned host projector staging to the owner image. V4's measured image ID is
`sha256:24386fa3fb0e4d7ff2680174d5a126090293920c4556f1cf289a6af9d24bdefe`;
engine SHA-256 `c8036c3b4f539701061835677377a564a6728aefa88435b390ac93729cfd3a29`.
Its engine/server patch SHA-256 is
`4edcf118309596200c8bf37c656c072a6602dac4a5f96838a40e956da4ca7105`;
mtmd host-copy patch SHA-256
`7c8119143f0b36813ac4bb0194da7a2072024eba13c2514de9c7ee97236ca4f7`.
Vision binary SHA-256 is
`4a695b5099016fdc0e2d762ac9a194581eb80cc45d560ee8981a52c8262103f0`.
These identify the **selected serving image**, profile
`flash-iq3s-256k-vision-tune-owneradapt24`. The original owner API image remains the
resident-vision rollback, with unchanged target/projector/defaults. This custom
engine/server/mtmd patch is additional to the dependency-only owner API base.

The original identical-request replay confirms +6.17% decode; matched 64K
gives +6.74%, and a single 128K pair gives +4.81%. The changed-prefix screen
still gives −2.07%: selection does not imply a uniform gain. Practical30 low
scores 29/30 with all natural completions, inside the original seed range.
The owner explicitly accepts +93 ms median once per uncached image; the earlier
100 ms engineering target is superseded. Cached images bypass staging.
[Replay](../results/public/swap-prefix-control-comparison.json),
[64K](../results/public/swap64-comparison.json),
[128K](../results/public/swap128-comparison.json),
[canaries](../results/public/practical30-swap-v4-comparison.json).

The expert arena has stable CUDA VMM addresses and a lendable tail. Under the
request FIFO, uncached image groups run LEND → LOAD → encode → UNLOAD → RECLAIM;
text generation is refused while the tail is lent. The worker keeps a pinned
host copy of the projector. Partial lending is 1408 MiB on the first image;
later images lend 1600 MiB. The model is never reloaded for vision. Two new
maximum-budget 2048×2048 images and one cached repeat pass on the selected
serving instance, including matched LEND/RECLAIM counts and natural completion.
[Staging check](../results/public/swap-v4-large-image-smoke.json).

## Target files

| File suffix / asset | Bytes | SHA-256 |
|---|---:|---|
| IQ3_S `00001-of-00002.gguf` | 54817524224 | `4c1eb2ceb4915e1192f4f386021897bde56a97f40a0bb78bb86465e0f7d2aca3` |
| IQ3_S `00002-of-00002.gguf` | 28800138432 | `316b46f3a2dbd68c900f43136ab9449f9dcc3725dfd8c794847c204bc161e113` |
| BF16 mmproj | 907543008 | `b1a82259702816a5330d7bd7607cd9676b11780e79ff7348c21103ff3ce49bd0` |

The second GGUF contains the IQ4_NL ngram table. `scripts/prepare_models.py`
verifies these immutable inputs. `scripts/prepare_packs.sh` exports the native
pack/tokenizer and builds the pinned Q2_0-expert MTP runtime assets. Main target
weights are not rewritten by preparation. The MTP runtime uses Q8 projections
and Q2_0 experts for its draft; this is not Q8 reference-target inference.

## Runtime placement

- Host RAM: complete expert working set, complete ngram table, bounded pinned
  buffers and long-context state. The disk is a load source, not a decode tier.
- GPU: dense target work, verified MTP, resident hot experts, KV window and
  workspaces. The selected GPU BF16 vision encoder stages only for new images;
  its cache tail is reclaimed before generation. The preserved resident-vision
  baseline reserves its encoder workspace before automatic expert-cache sizing.
- CPU: AVX-512 cold-expert work plus orchestration. PCIe fraction .35 splits
  cold-expert work with streamed GPU execution; it is a measured profile choice.
- Server: one execution slot with history/prefix reuse. Two independent parked
  histories were checked, but requests execute FIFO.

Int8 KV is a representation trade. Adaptive CPU/GPU expert arithmetic rounds
slightly differently; a fixed seed alone does not guarantee identical text.
The native context setting is capacity, not proof of useful reasoning at its
exact boundary. The published default is the tested 256K-capacity profile,
not a claim of full-reference arithmetic or universal equivalence.
