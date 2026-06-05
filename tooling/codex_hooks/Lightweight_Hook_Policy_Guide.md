# Lightweight Hook Policy Guide

本文件保留旧文件名以避免引用断裂，但内容已经替换为新的轻量 hook
模型。Harness Codex hooks 不再把 prompt 识别结果当作 Stage 权限提升；
prompt 只提供 route hint，真正的硬边界只在具体 tool call 上判断。

术语遵循 `.agents/references/ubiquitous-language.md`。特别注意:

```text
Conclusion Evidence -> 支持 claim / fact / idea / protocol choice 的来源链
Gate Evidence       -> 支持 command / review / approval check / gate 的执行结果
```

Hook runtime 是 guardrail，不是 evidence。Hook 提示不能替代 Read Contract、
Gate Evidence、review packet 或 human approval。

## 目标

旧模型的问题是把意图判断、上下文注入和写入权限绑得过紧:

- 意图判断会犯错，误判后容易阻断正常工作。
- 每次注入完整 contract/read-set 会消耗大量 token。
- Stop 阶段阻断容易制造重复提醒，也会在任务已经足够清楚时打断输出。
- 但 `.evidence/**`、`.auto_iterate/**`、`.workflow_supervisor/**`、
  生成视图、外部 review wrapper 和 commit hygiene 仍然需要 guardrail。

新模型的目标:

- UserPromptSubmit 只注入紧凑 route hint 和 workspace capsule。
- 读文件是推荐动作，由模型按任务需要主动读取；hook 只做一次性提醒。
- PreToolUse 默认提示不阻断，只保留少量高确定性的 hard block。
- PostToolUse 静默记录状态，不向模型反复输出。
- Stop 不再默认阻断缺读或缺 Gate ledger，只在已有完整 Gate ledger 时清理
  compatible pending state。

## Runtime Flow

```text
UserPromptSubmit
  -> infer candidate_skill and intent
  -> write .harness_hooks/session.json
  -> emit one route hint per turn
  -> emit workspace capsule once per session

PreToolUse
  -> block narrow boundary violations
  -> otherwise emit one notice per risk fingerprint

PostToolUse
  -> record read ledger, mutating tool paths, and pending metadata silently

Stop
  -> clear compatible pending state when final output includes a full Gate ledger
  -> do not block final output by default
```

## Session Fields

`session.json` keeps compatibility fields because old runtime state and tests may
still contain them:

| Field | New meaning |
| --- | --- |
| `candidate_skill` | Normal route hint inferred from the prompt |
| `intent_class` | Prompt intent metadata such as `code_write` or `code_review_heavy` |
| `enforcement_mode` | Compatibility/status field; new detection normally writes `context_only` or `none` |
| `active_skill` | Legacy compatibility field; do not treat it as route authorization |
| `pending_candidate_activation` | Compatibility flag for continuation prompts |

Continuation prompts such as `继续`, `continue`, and `resume` preserve route
context only when the Codex `session_id` matches. This keeps multi-turn reviews
coherent without leaking stale context across independent sessions.

## Contract Metadata

`schemas/skill_contracts.json` remains useful, but it is no longer a permission
elevation mechanism. Hook runtime uses it for:

- recommended read notices
- route owner notices
- generated Stage reference
- artifact output descriptions
- forbidden action checks that are concrete and high confidence
- external review and tool-owned output boundaries

`write_scope.allowed_paths` is still required by the schema because it documents
which paths belong to a skill or stage. It should be read as ownership metadata,
not as proof that a prompt has unlocked those paths.

## Notices

Notices are advisory and deduplicated through `.harness_hooks/notices.json`.
They should be specific enough to help the model choose the next action, but
short enough not to consume large context.

Current notices include:

- missing recommended reads before durable edits
- mixed owner paths before `git add` or `git commit`
- missing sliced-commit guidance before `git commit`
- route owner hints when a path maps to a Harness skill owner

Notices are emitted once per relevant turn/session fingerprint. If the same
tool call repeats, the hook should avoid repeating the same advisory text.

## Hard Blocks

Hard blocks are reserved for concrete boundary violations:

- direct manual writes to `.evidence/**`
- direct manual writes to `.auto_iterate/**`
- direct manual writes to `.workflow_supervisor/**`
- direct manual writes to generated view paths `docs/_views/**` and
  `docs/_site/**`
- `git add` of known local-only or reference-only paths
- direct calls to external review scripts instead of
  `tooling/model_api/harness_external_review.py`
- provider-backed external review outside `$code-review heavy` route context
- external review outputs outside
  `.agents/state/review_traces/code-review/**`
- source or guardrail writes during `code-review`, except local review traces

Everything else should prefer a notice over a block unless the tool call would
corrupt controlled state or bypass an explicitly owned tool.

## Operator Model

```text
Codex sandbox       = coarse filesystem/network permission
Harness hard block  = controlled state would be corrupted
Harness notice      = context, route, or hygiene may be missing
Human approval      = explicit operator decision or auditable approval artifact
Gate Evidence       = command/review/approval result, not a hook message
```

The human operator remains responsible for claim boundaries, contract
acceptance, high-risk transitions, and release decisions. Hook output is
guidance for the agent, not approval.

## Maintenance Checklist

When changing hook policy:

- [ ] Keep default behavior advisory unless the risk is concrete and
  high-confidence.
- [ ] Add or update focused tests for each notice and hard block.
- [ ] Verify repeated tool calls do not repeat identical notices.
- [ ] Preserve direct manual-write blocks for tool-owned paths.
- [ ] Preserve review-only boundaries for `code-review`.
- [ ] Keep `.agents/` and `.claude/` workflow language aligned.
- [ ] Update README and reviewer prompt snippets so old hook models do not
  re-enter future reviews.
- [ ] Run the hook contract validation commands.

Required checks for hook, contract, or schema changes:

```bash
python tooling/codex_hooks/check_contracts.py --workspace-root .
python tooling/codex_hooks/hook_status.py --workspace-root .
pytest tooling/.tests/test_codex_hooks_contracts.py
python -m py_compile tooling/codex_hooks/harness_contracts.py tooling/codex_hooks/user_prompt_submit.py tooling/codex_hooks/pre_tool_use_policy.py tooling/codex_hooks/post_tool_use_markers.py tooling/codex_hooks/require_gate_ledger.py
ruff check --select=E,F,I tooling/codex_hooks/harness_contracts.py tooling/codex_hooks/user_prompt_submit.py tooling/codex_hooks/pre_tool_use_policy.py tooling/codex_hooks/post_tool_use_markers.py tooling/codex_hooks/require_gate_ledger.py
```
