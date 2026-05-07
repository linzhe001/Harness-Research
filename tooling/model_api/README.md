# External Model API

`external_chat.py` calls OpenAI-compatible chat-completions providers for
review and cross-check workflows. It does not replace Codex auto-iterate
runtime execution; it produces reviewer text artifacts from a prompt.

By default, the CLI looks for provider YAML in this order:

1. `tooling/model_api/providers.local.yaml`
2. `tooling/model_api/providers.example.yaml`

If PyYAML is unavailable and no explicit `--config` is supplied, YAML defaults
are skipped so builtin environment-variable providers can still work. Passing a
YAML file through `--config` still requires PyYAML.

For a local file-based setup, copy the example and fill the local copy:

```bash
cp tooling/model_api/providers.example.yaml tooling/model_api/providers.local.yaml
```

In `tooling/model_api/providers.local.yaml`:

```yaml
providers:
  deepseek:
    api_key: "<your-deepseek-api-key>"
    model: deepseek-v4-pro
```

`providers.local.yaml` is local-only and must not be committed. `--config`
overrides the default lookup. Environment variables still work as an
alternative through `DEEPSEEK_API_KEY` and `DEEPSEEK_MODEL`.

The response metadata artifact includes a `cache` summary when the provider
returns `prompt_cache_hit_tokens` and `prompt_cache_miss_tokens`. Cache can
reduce repeat-prefix cost, but the review workflow should not rely on a warm-up
request. By default, send a targeted review packet instead of a full repository
bundle.

DeepSeek cannot read local repository files from a single `external_chat.py`
call. The caller must package every file the model may inspect, or implement a
separate tool-call loop. `build_review_prompt.py` defaults to `--scope changed`,
which sends:

- reviewer instructions
- task text
- `git status --short`
- `git diff` from `--snapshot-ref`
- changed tracked working-tree file content
- operator-selected `--context-file` entries
- untracked file names, without content unless explicitly requested

Use `--context-file` for small, relevant dependencies such as contracts, schemas,
or helper modules. Use `--include-path` and `--exclude-path` to split large
diffs into smaller subsystem review packets. Use `--scope full` only when the
operator explicitly accepts the higher prompt cost.

For provider-backed reviews inside Codex, use the Harness wrapper instead of
calling networked reviewer scripts directly:

```bash
python tooling/model_api/harness_external_review.py agentic \
  --provider deepseek \
  --workspace-root . \
  --task-file .agents/state/review_traces/code-review/task.md \
  --output .agents/state/review_traces/code-review/deepseek_agentic.response.md \
  --trace-json .agents/state/review_traces/code-review/deepseek_agentic.trace.json \
  --meta-json .agents/state/review_traces/code-review/deepseek_agentic.meta.json
```

The wrapper only runs during an active `$code-review heavy` Harness session.
The workspace-local Codex rule installed by `tooling/codex_hooks/install_hooks.py`
allows network escalation for the wrapper prefix, while the Harness PreToolUse
hook blocks direct calls to `agentic_review.py` and `external_chat.py`. Configure
custom endpoints in `tooling/model_api/providers.local.yaml`; the wrapper
rejects `--base-url` and `--config` overrides so the approved command prefix
does not become a generic network tunnel.

For high-rigor reviews where DeepSeek should decide which files to inspect, the
wrapper calls `agentic_review.py`. It keeps the prompt small and exposes a local
read-only tool loop:

- `workflow_hints`
- `git_status`
- `list_files`
- `search_text`
- `read_file`
- `git_diff`
- `git_show`

The local tool runner enforces workspace path checks, ignored-file denial,
untracked-file denial, per-tool byte limits, total tool-output limits, and
secret redaction before tool output is sent back to the model. Search uses
tracked `git grep` results so untracked local files are not searched by default.
If an untracked file is genuinely part of the review scope, pass
`--allow-untracked-file <path>` for each exact file that the model may inspect.
Do not allowlist local credential exports or operator config files.

DeepSeek calls are intended for high-rigor review, not cheap routine checks.
The default agentic behavior is `--thinking-scope all`, so every tool-selection
turn and the final synthesis request use provider `thinking` / `reasoning_effort`
extras, such as `reasoning_effort: max`. This is more expensive, but it matches
the intended use: when DeepSeek is called, let it inspect broadly and think hard.
Use `--thinking-scope final` only when explicitly trading off cost, or
`--thinking-scope none` for the lowest-cost run.

The final synthesis request omits tools and `tool_choice` so the provider must
return review text instead of another local read request. Each response trace
records payload, messages, and tool-schema hashes so unusually low cache hit
rates can be debugged. By default, when the final request reports a prompt cache miss rate
above `--cache-retry-miss-rate` (default `0.8`), the runner waits
`--cache-retry-delay-sec` seconds and retries the unchanged payload once. Use
`--cache-retry-scope all` to allow one unchanged high-miss retry on a
tool-selection round as well. Retryable provider HTTP/network failures are also
retried with `--api-retry-attempts` and `--api-retry-delay-sec`.

If a provider returns tool-call markup as plain text during final synthesis
(for example DSML-style `<...tool_calls>` content), the runner performs one
corrective final-text retry. If the retry still returns markup, the run exits as
`INCOMPLETE` with `trace.status="invalid_final_response"` instead of treating
the markup as a successful review.

Example:

```bash
python tooling/model_api/harness_external_review.py agentic \
  --provider deepseek \
  --workspace-root . \
  --task-file .agents/state/review_traces/code-review/task.md \
  --thinking-scope all \
  --max-iterations 12 \
  --max-tool-calls 40 \
  --force-final-after-tool-calls 40 \
  --allow-untracked-file tooling/model_api/agentic_review.py \
  --max-output-tokens 8192 \
  --cache-retry-miss-rate 0.8 \
  --cache-retry-delay-sec 5 \
  --cache-retry-scope all \
  --api-retry-attempts 3 \
  --api-retry-delay-sec 2 \
  --output .agents/state/review_traces/code-review/deepseek_agentic.response.md \
  --trace-json .agents/state/review_traces/code-review/deepseek_agentic.trace.json \
  --meta-json .agents/state/review_traces/code-review/deepseek_agentic.meta.json
```

Example:

```bash
python tooling/model_api/build_review_prompt.py \
  --workspace-root . \
  --task-file .agents/state/review_traces/code-review/task.md \
  --include-path tooling/model_api \
  --context-file AGENTS.md \
  --context-file CLAUDE.md \
  --context-file tooling/codex_hooks/README.md \
  --output .agents/state/review_traces/code-review/prompt.md
```

If a full-repository review is still needed, make it explicit and reuse one
starting ref through a session:

```bash
SESSION_SNAPSHOT_REF=$(git rev-parse HEAD)

python tooling/model_api/build_review_prompt.py \
  --workspace-root . \
  --scope full \
  --snapshot-ref "$SESSION_SNAPSHOT_REF" \
  --task-file .agents/state/review_traces/code-review/task.md \
  --output .agents/state/review_traces/code-review/prompt.md
```

Untracked file content is omitted from generated prompts by default, including
file names. To include a new untracked review file in a prompt packet, select it
explicitly:

```bash
python tooling/model_api/build_review_prompt.py \
  --workspace-root . \
  --task-file .agents/state/review_traces/code-review/task.md \
  --include-untracked-content \
  --include-untracked-path tooling/model_api/agentic_review.py \
  --output .agents/state/review_traces/code-review/prompt.md
```

Example:

```bash
python tooling/model_api/harness_external_review.py chat \
  --provider deepseek \
  --prompt-file .agents/state/review_traces/code-review/prompt.md \
  --output .agents/state/review_traces/code-review/deepseek_review.response.md \
  --request-json .agents/state/review_traces/code-review/deepseek_review.request.json \
  --meta-json .agents/state/review_traces/code-review/deepseek_review.meta.json
```
