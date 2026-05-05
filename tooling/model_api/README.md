# External Model API

`external_chat.py` calls OpenAI-compatible chat-completions providers for
review and cross-check workflows. It does not replace Codex auto-iterate
runtime execution; it produces reviewer text artifacts from a prompt.

Secrets are supplied only through environment variables:

```bash
export DEEPSEEK_API_KEY=...
export DEEPSEEK_MODEL=deepseek-v4-pro
```

Example:

```bash
python tooling/model_api/external_chat.py \
  --provider deepseek \
  --prompt-file .agents/state/review_traces/code-review/prompt.md \
  --output .agents/state/review_traces/code-review/deepseek_review.response.md \
  --request-json .agents/state/review_traces/code-review/deepseek_review.request.json \
  --meta-json .agents/state/review_traces/code-review/deepseek_review.meta.json
```

For another OpenAI-compatible provider, either set `OPENAI_BASE_URL`,
`OPENAI_API_KEY`, and `OPENAI_MODEL`, or copy `providers.example.yaml` and add a
named provider with `base_url`, `api_key_env`, and `model`.
