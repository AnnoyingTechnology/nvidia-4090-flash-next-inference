# Operations and reproducibility

Use the README build/prepare/start sequence. The selected API stays on host
loopback port 19623, model `ulmus`. Required host components are a suitable
NVIDIA driver, Docker with GPU access, Git, curl and Python 3. Fresh builds
are substantial; model/source/cache paths stay within the checkout.

## Selected service lifecycle (2026-10-04)

Both deployments use on-demand systemd user services, with user lingering enabled:

```bash
systemctl --user start qwen3.8-flash-next.service
systemctl --user stop qwen3.8-flash-next.service
systemctl --user status qwen3.8-flash-next.service
journalctl --user -u qwen3.8-flash-next.service -f
# The 27B deployment uses the same commands with qwen3.8-27b.service.
```

Neither unit is enabled at boot. Both supervise foreground Docker clients, wait
for HTTP readiness and restart on failure with bounded restart attempts. No
mutual exclusion, GPU occupancy check or cross-service stopping is installed.
The Flash-Next container is `qwen3.8-flash-next`; its OpenCode launcher starts the
service. The 27B unit runs its existing Compose deployment without rebuilding.
Templates live in `scripts/systemd/`; both are installed under the owner's
`~/.config/systemd/user/`. The vLLM readiness helper is deployed in its own
project's `systemd/` directory. User units rely on the existing system Docker daemon.

`run.sh` records image/profile hashes. Its default detached experimental container
remains `ulmus-inference-test`; systemd selects foreground mode and the production
name via `ULMUS_FOREGROUND=1` and `ULMUS_CONTAINER=qwen3.8-flash-next`.
`stop.sh` stops the selected service and any old owned experimental container.
Historical benchmark runners assume the experimental container name: they must
be deliberately adapted before reuse. No new tuning is authorized by this change.
The 175 GiB memory budget remains specific to this 192 GB host.

The outer Flash-Next directory now points operators into `stack/`. Its obsolete
September vLLM files are preserved under `archive/vllm-prototype-2026-09-03/`.
Model assets remain in place. No driver, power policy or network binding changed.
The Flash-Next service was started and its API checked. The 27B unit was statically
validated but not loaded: its previously qualified runtime remains stopped.

Observed selection, 2026-11-08: `flash-iq3s-256k-vision-tune-owner20261108`, using
`ulmus/strata:146df3c-owner20261108`. The [build manifest](../updates/2026-11-08/build-manifest.json)
identifies the clean Strata source export and CUDA 12.4 overlay recipes. Do not build during
a performance measurement. The image sets `STRATA_ROUTE_TAIL_SKIP=0` and `STRATA_ADAPT_FETCH=2`.
The target remains loaded; native elastic vision starts its GPU reader on demand and stops it
after five seconds idle. Keep the 3072 MiB image budget and 1024 MiB engine reserve: a 2048 MiB
image budget failed GPU startup. Reader restart adds about 2.2 seconds after idle; cached
images do not restart it. Full-RAM experts/PLE, 256K capacity and original weights remain selected.

For an explicitly requested profile rollback, change the Flash-Next unit's
`ExecStart` profile and the matching profile assertion in `scripts/opencode.sh`,
then reload the user manager and restart that service. The direct pre-update rollback is
`flash-iq3s-256k-vision-tune-owner9950x3d2` with `ulmus/strata:99f3dbd-lendvram`.
The remote `updates/20261108/rollback/` retains the previous installed unit, template, launcher
and run script. Keep the workspace's client assertion aligned when restoring them.
The historical `ownerswap`
profile retains 96 adaptation slots per update; `ownervision` retains resident
vision. Do not use old experiment runners to manage the selected service.

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
python3 owner_api_check.py --profile flash-iq3s-256k-vision-tune-owneradapt24 \
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

The original 30-function prototype had three ambiguous interfaces and is retained
as an invalid comparison prototype. V2 specifies them and exposes one public
example per task. All private tests/controls are unchanged; every task is rerun.
This is a local canary deck, not a blind preregistered public benchmark.

```bash
python3 scripts/prepare_practical30.py
bash scripts/build_grader.sh
python3 practical_eval.py --cases eval/practical30-v2-cases.jsonl \
  --effort low --tokens 32768 --label practical30-low --out results/practical30-low.json
```

The evaluator verifies positive/negative controls for every function before model
calls and binds the run to the actual owned runtime. The output limit is a runaway
guard; exhausting it withholds full-cohort accuracy. Keep off and low runs separate.
Set `ULMUS_EVAL_CONTAINER` for an owned container other than `ulmus-inference-test`;
the fingerprint reads API sources from the configured runtime working directory.

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
