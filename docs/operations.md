# Operations and reproducibility

Use the README build/prepare/start sequence. The selected API stays on host
loopback port 19623, model `ulmus`. Required host components are a suitable
NVIDIA driver, Docker with GPU access, Git, curl and Python 3. Fresh builds
are substantial; model/source/cache paths stay within the checkout.

`run.sh` refuses to start while any GPU compute workload is active, records
its actual image ID and profile/default hashes, then launches the owned
`ulmus-inference-test` container. `stop.sh` waits for its removal before a
profile switch. It preserves model files and images. The 175 GiB container
memory budget is for this 192 GB host; smaller machines need separate tuning.
No power policy, driver, firewall or automatic startup is changed by these tools.

## Requests

```bash
curl -fsS http://127.0.0.1:19623/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"ulmus","messages":[{"role":"user","content":"Explain a safe nginx reload procedure."}],"max_tokens":2048}'
```

Defaults use low reasoning and stochastic sampling. Clients can explicitly
request `reasoning_effort: none` or a larger budget/effort. The shared settings
are a supported Strata sidecar, not a request-rewriting patch. Machine-facing
JSON uses native prompt-and-validate `response_format`; do not combine it with
tool calls. Invalid/capped JSON returns an error. Ordinary tool requests work
separately, with the runtime's native parser.

An SSH tunnel permits remote use without changing the listener:

```bash
ssh -N -L 19623:127.0.0.1:19623 <user>@<host-address>
```

## Benchmarks

Generate synthetic prefill fixtures inside the runtime image:

```bash
docker run --rm --user "$(id -u):$(id -g)" \
  --mount "type=bind,src=$PWD,dst=/work" \
  ulmus/strata:99f3dbd-ownerapi python /work/fixtures.py \
  --tokenizer /work/packs/iq3s/tokenizer --out /work/fixtures
python3 owner_api_check.py --profile flash-iq3s-256k-vision-tune-ownervision \
  --vision --out results/api-check.json
python3 bench.py --out results/perf.json --repeats 2 --decode-tokens 512 \
  --fixtures fixtures --prefill-k 32 --paired-id owner-profiles-v1 \
  --sampling '{"temperature":1,"top_p":0.95,"top_k":20,"min_p":0,"presence_penalty":0,"repetition_penalty":1,"reasoning_effort":"low"}'
```

The tokenizer options above follow `fixtures.py --help`; use the pinned model
pack, not another tokenizer. Actual engine token counts and cache-hit accounting
are returned with each request. Repeat namespaces and output limits matter;
compare request hashes, sampler, effort, context and caches before claiming a gain.

The practical-code grader uses pinned LiveCodeBench evaluator source in an
isolated container with no network, no capabilities, read-only filesystem,
bounded memory/CPU/PIDs and positive/negative controls. Dataset question and
private-test payloads are downloaded separately and never published here.
The standalone synthetic vision deck contains its own ground truth and sources.

## Public evidence

`python3 scripts/export_public.py` exports a fixed allowlist of checkpoint
results and drops per-sample telemetry/local paths. It does not export host
inventory, private logs or dataset payloads. Stage the intended files and run
`python3 scripts/check_public.py` before committing. Generated private results
are ignored; new public evidence must be explicitly reviewed and exported.

The checked-in JSON includes full synthetic benchmark outputs and scoring
summaries. Its manifest records both private-original and public-export hashes.
A sanitized export's checksum is not the original checksum. Raw private captures
remain local for diagnosis; downloaded dependencies and weights are not Git assets.
