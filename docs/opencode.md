# OpenCode on Juniperus and Ulmus

Both clients use the dedicated Huihui services. The `ai-ulmus/qwen3.8-27b` default
is preserved, with 245760 input and 8192 output tokens inside a 253952-token client window.
Ulmus uses loopback port 19622 for 27B; remote clients supply or preserve its LAN endpoint.
The obsolete local LM Studio 27B entries are retired by `--local-services`.
Flash-Next is labelled Huihui v2-derived GSQ IQ3_S; its endpoint remains loopback port 19623.

Installed shortcuts on both owner clients are `opencode-flash-next` and `opencode-27b`.
On Juniperus the Flash shortcut starts the service and owns an SSH tunnel for the session.
On Ulmus it starts the service and connects directly, using `scripts/opencode-local.sh`.
The 27B shortcuts start only its dedicated unit; neither launcher stops other workloads.
Selecting a model in ordinary OpenCode requires the corresponding service to be running,
and remote Flash-Next also requires the SSH tunnel.

The selected IQ3_S stack is the best measured Flash-Next path on Ulmus in
this campaign. Unbuilt alternatives remain experiments, not established
improvements. One client entry follows the existing 27B naming style:

- `ai-ulmus-flash-next/qwen3.8-flash-next`: low by default, 8192 output
  tokens, 245760 input tokens inside a 253952-token client window.

The **253952-token context window** is separate from the maximum answer length.
The backend supports 262144 tokens; the client leaves an additional reserve.
The previous duplicate `-long` entry changed the answer budget, not the context
capacity, and has been removed.

The model exposes image attachments and tool calls. Off, low, medium and xhigh
variants are available; Strata maps high/xhigh to the same native xhigh
level. A larger answer budget does not guarantee that a difficult coding problem
finishes: the first capped 8K coding case also capped at 32K in separate evaluations.
Current quality comparisons use low, with off cells kept separate.

The API model ID remains `Qwen3.8-Flash-Next`; the lowercase OpenCode keys
are client names mapped through the supported `id` field. Reasoning
history is preserved through `reasoning_content`. Sampling options are
sent as native compatible-API fields, not a runtime rewriting patch.

`docs/opencode-example.json` contains both owned providers. The installer
merges it into the user's existing configuration, keeps the previous
default model and unrelated settings, writes atomically and retains a
private rollback copy inside this workspace. No credential is required
for the loopback model API.

```bash
python3 scripts/install_opencode.py
export ULMUS_SSH_TARGET='<user>@<host-address>'
export ULMUS_REMOTE_ROOT='<absolute remote stack directory>'
bash scripts/opencode.sh
```

On Ulmus, install with `python3 scripts/install_opencode.py --local-services`.
For a new remote client, pass `--dense-base-url` with its trusted-LAN 27B URL.
The existing Flash shortcut uses the private workspace wrapper; remote 27B uses
`scripts/opencode-27b.sh` with `ULMUS_SSH_TARGET` supplied by its private wrapper.

The selected profile is `flash-iq3s-256k-vision-tune-huihuiv220261108` (qualified 2026-11-08).
It keeps one target loaded and starts GPU vision for uncached images. The native reader
stops after five seconds idle; restarting it adds about 2.2 seconds on the next new image.
Cached images bypass the reader. The target uses baked Huihui v2 weight edits; reasoning defaults
and client capacities are preserved. The original `owner20261108` profile remains the rollback.
The launcher starts `qwen3.8-flash-next.service` and waits for systemd readiness.
It verifies the selected profile, creates
a loopback-only SSH tunnel, selects the new model and closes its tunnel
when OpenCode exits. It leaves the loaded model running for later use.
There is no GPU occupancy gate or cross-service stopping. It does not install automatic startup,
change a firewall or power on/off the host. Ulmus must already be awake.

`scripts/opencode.sh --run ...` supports the normal noninteractive OpenCode
arguments. Ordinary OpenCode can select the entry while the SSH tunnel is open.

The client advertises the runtime's capacity with an extra reserve;
combined maximum-context images and the exact native boundary remain
unqualified. The local [client check](../results/public/opencode-client-check.json)
records actual wire settings and bounded image/read-tool outcomes.
