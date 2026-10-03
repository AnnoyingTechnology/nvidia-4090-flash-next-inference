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
  workspaces. The optional GPU BF16 vision encoder reserves its workspace before
  automatic expert-cache sizing.
- CPU: AVX-512 cold-expert work plus orchestration. PCIe fraction .35 splits
  cold-expert work with streamed GPU execution; it is a measured profile choice.
- Server: one execution slot with history/prefix reuse. Two independent parked
  histories were checked, but requests execute FIFO.

Int8 KV is a representation trade. Adaptive CPU/GPU expert arithmetic rounds
slightly differently; a fixed seed alone does not guarantee identical text.
The native context setting is capacity, not proof of useful reasoning at its
exact boundary. The published default is the tested 256K-capacity profile,
not a claim of full-reference arithmetic or universal equivalence.
