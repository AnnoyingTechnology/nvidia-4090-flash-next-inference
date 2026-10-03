# Vision comparison — 2026-10-03

IQ3_S passed all 15 initial image-content canaries with both low and off
reasoning. Luna low passed 14/15; Terra and Sol low passed 15/15. A harder
human-chart follow-up found one IQ3_S reading error: 19/20 reviewed cases,
versus 20/20 for both Terra and Sol. Ordinary chart arithmetic passed 5/5
for all three. These small sets do not establish general model parity or
separate Terra from Sol.

## First frozen deck

The [15 cases](../fixtures/vision15/cases.jsonl) contain terminal output,
code, charts, routing and access diagrams, document OCR, an embedded
untrusted instruction, spatial counting and three public-domain/CC0 photos.
Images, prompts, expected answers, hashes and attribution were frozen
before model requests. No tools or web access were used by the evaluated
models, and no transport failures or output caps occurred.

| Model | Effort | Image content | Correct fields | Expected JSON types | Plain JSON |
|---|---|---:|---:|---:|---:|
| GSQ IQ3_S | off | 15/15 | 34/34 | 14/15 | 15/15 |
| GSQ IQ3_S | low | 15/15 | 34/34 | 14/15 | 15/15 |
| `gpt-6-luna` | low | 14/15 | 33/34 | 11/15 | 15/15 |
| `gpt-5.6-terra` | low | 15/15 | 34/34 | 14/15 | 15/15 |
| `gpt-6.1-sol` | low | 15/15 | 34/34 | 14/15 | 15/15 |

All models returned the invoice's correct displayed amount as a numeric
string. Luna also used strings for a port and percentage. The prompts
did not mandate numeric JSON types, so a common post-run scorer accepts
exact numeric strings and a percent sign on the two percentage fields.
It does not fish numbers out of arbitrary text or coerce booleans.
Original typed verdicts remain in every raw report. Luna's substantive
mistake was counting two spoons instead of one in the coffee photograph.

The [derived report](../results/public/vision15-comparison.json) includes
each answer, both scores and source hashes. Run `python3
scripts/summarize_vision15.py --results results/public --out /tmp/vision15.json`
to recompute it from the public raw responses. Hashes identify the inputs
actually used; sanitized exports have their own hashes in the export manifest.

## Published human charts and ordinary arithmetic

The follow-up uses pinned [ChartQA human test data](https://github.com/vis-nlp/ChartQA/tree/044eabfc306abfe9340c5741f0093aefc5973d06/ChartQA%20Dataset/test).
The first 15 seeded unique-image questions cover lookup, comparison and
counting. A steering follow-up adds five ordinary arithmetic operations.
One initial selector matched the software noun “product”; that request
was retained as a lookup, and an actual multiplication question was
added. There are **21 requests**, not a full benchmark run.

| Model, all low | Original annotation/type match | Reviewed visual content | Ordinary arithmetic |
|---|---:|---:|---:|
| GSQ IQ3_S | 13/21 | **19/20** | **5/5** |
| Terra | 11/21 | **20/20** | **5/5** |
| Sol | 9/21 | **20/20** | **5/5** |

Raw annotation matching penalizes units, numeric formatting and short
explanations. It also inherits two annotation discrepancies and one
ambiguous question. It is retained for transparency, not used to claim
that IQ3_S outperformed the cloud models.

The manual source-image review happened after first responses and was
not blind. Corrections and exclusions apply uniformly to every model:

- Index 937: the label `10` counts years. The blue series changes from
  about 28.2 in 2010 to about 30.3 in 2019, around **2.1 points**. Terra
  and Sol answered 2.1; IQ3_S answered 1.9 and fails the 5% tolerance.
- Index 74: the chart displays **302.38%**; the annotation stores its
  fractional equivalent `3.0238`. All three read the displayed value.
- Index 1081: the image gives population shares, not absolute population.
  A sum of 100% and “not provided” are defensible interpretations. This
  case is excluded from the reviewed denominator for every model.

The common semantic scorer accepts numeric presentation, explicit units
and equivalent ratios, with 5% numeric tolerance. It accepts exact
categories or a leading yes/no answer. Original outputs are unchanged.
The [audit and per-case scores](../results/public/chartqa-comparison.json)
make the difference between source labels and reviewed answers explicit.
`scripts/prepare_chartqa15.py` reconstructs the pinned inputs locally;
dataset images/questions are not republished in this Apache-licensed repo.
Provenance manifests record source revision, selection seeds and hashes.

## Protocol and limits

Qwen uses the selected owner vision profile: original BF16 GPU projector,
4096 image-token budget and 4096 completion-token cap. Low uses temperature
1, top-p .95, top-k 20, min-p 0, presence penalty 0, repetition penalty 1
and seed 42. The initial off canary uses temperature 0 and seed 42. Its
greedy sampler is a deterministic test cell; OpenCode's off variant uses
Qwen's recommended .7/.8/1.5 temperature/top-p/presence settings.

Cloud requests use Codex CLI 0.160.0, explicit model IDs and low effort,
one image per independent call, an empty working directory and disabled
shell tooling. Identical PNG bytes and case prompts were used. Cloud
samplers, internal image processing and output budgets are not controlled
identically to Qwen. The CLI adds its own cached instruction context.
Its wall times include client startup and network; they are not bare
inference latency and are not compared with local tok/s. Qwen's first
low deck completed in about 1.86–3.41 seconds per case, median 2.59 seconds.

Current comparisons stay at low, with separately labelled off cells.
The model supports low, medium and xhigh plus disabled thinking; Strata's
high label maps to xhigh. These are effort instructions, not fixed
thinking-token quotas. Published full-size benchmarks can use different
efforts and budgets, so they are not a matched local low/off baseline.
[Official model controls](https://huggingface.co/Qwen/Qwen3.8-Flash-Next#api-usage)
and the [pinned runtime mapping](https://github.com/Niko1221/Strata/blob/99f3dbd0b21d1401b3769e0c0d963913607f380b/serve/frontend.py#L67)
document those levels.

Remaining work includes more real screenshots, documents, spatial scenes,
uncertainty and visual tool-use tasks, with independently reviewed ground
truth. The present small screens cannot measure a quantization-specific
vision loss or support a universal “Sol-level” claim.
