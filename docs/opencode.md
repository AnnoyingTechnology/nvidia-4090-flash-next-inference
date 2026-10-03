# OpenCode on Juniperus

The selected IQ3_S stack is the best measured Flash-Next path on Ulmus in
this campaign. Unbuilt alternatives remain experiments, not established
improvements. The two client entries follow the existing 27B naming style:

- `ai-ulmus-flash-next/qwen3.8-flash-next`: low by default, 8192 output
  tokens, 245760 input tokens inside a 253952-token client window.
- `ai-ulmus-flash-next/qwen3.8-flash-next-long`: the same model with 32768
  output tokens and 221184 input tokens inside the same client window.

Both expose image attachments and tool calls. Off, low, medium and xhigh
variants are available; Strata maps high/xhigh to the same native xhigh
level. Increasing effort or output room is optional. The longer budget
is useful for experimentation but does not guarantee that a difficult
coding problem finishes: the first capped 8K coding case also capped at 32K.
The current OpenCode global completion ceiling is 32000 tokens; the client
reserves 32768 for the long entry, so its actual request budget can be 32000.
Current quality comparisons use low, with off cells kept separate.

The API model ID remains `Qwen3.8-Flash-Next`; the lowercase OpenCode keys
are client names mapped through the supported `id` field. Reasoning
history is preserved through `reasoning_content`. Sampling options are
sent as native compatible-API fields, not a runtime rewriting patch.

`docs/opencode-example.json` contains only the new provider. The installer
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

Use `ULMUS_OPENCODE_MODEL=ai-ulmus-flash-next/qwen3.8-flash-next-long`
to select the larger reserve. `scripts/opencode.sh --run ...` supports
the normal noninteractive OpenCode arguments. Ordinary OpenCode can also
select either entry while the SSH tunnel is open.

The client advertises the runtime's capacity with an extra reserve;
combined maximum-context images and the exact native boundary remain
unqualified. The local [client check](../results/public/opencode-client-check.json)
records actual wire settings and bounded image/read-tool outcomes.
