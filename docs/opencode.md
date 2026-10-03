# OpenCode on Juniperus

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

`docs/opencode-example.json` contains the owned provider. The installer
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

The launcher starts the owner vision profile only when the owned server
is absent and the GPU is idle. It refuses another active profile, creates
a loopback-only SSH tunnel, selects the new model and closes its tunnel
when OpenCode exits. It leaves the loaded model running for later use.
It does not replace another GPU workload, install automatic startup,
change a firewall or power on/off the host. Ulmus must already be awake.

`scripts/opencode.sh --run ...` supports the normal noninteractive OpenCode
arguments. Ordinary OpenCode can select the entry while the SSH tunnel is open.

The client advertises the runtime's capacity with an extra reserve;
combined maximum-context images and the exact native boundary remain
unqualified. The local [client check](../results/public/opencode-client-check.json)
records actual wire settings and bounded image/read-tool outcomes.
