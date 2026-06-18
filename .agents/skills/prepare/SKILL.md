---
name: prepare
description: "Visible Harness prepare entry. Use after Grill readiness is approved to acquire datasets, clone baselines, run baseline smoke checks, and complete prepare through workflow-supervisor."
---

# Prepare

Use `$prepare` as the human-facing alias for the Execution Supervisor
`prepare` action. This is not a separate Skill Contract.

Read and follow:
- `../../../.agents/skills/workflow-supervisor/SKILL.md`
- `../../../.agents/references/workflow-supervisor-runtime.md`
- `../../../AGENTS.md`
- `../../../CLAUDE.md`

Default command:

```bash
python tooling/workflow_supervisor/scripts/workflow_ctl.py start --segment prepare --complete --json
```

Use Grill-produced approved readiness from `.workflow_supervisor/readiness.json`
when it exists. Pause only for missing inputs, policy blockers, worker
failures, or gate failures.

Before the default command, inspect Grill artifacts and readiness for a
`Model Weight Ledger`, `model_weight_*` policy rows, `hf_model_access_policy`,
and `target_paths` entries such as `model_cache` or `model_<id>`. Pull or
verify only candidate/approved weights with explicit source, access policy, and
target: exact local path, Hugging Face model id/repo via `huggingface-cli
download` or `git clone` when available, or official checkpoint/release URL.
Use `models/<id>` only when no target is specified and the policy allows it.
Do not guess, download deferred/rejected/approval-required weights, or bypass
gated access. Report weight acquisition Gate ledger entries and artifacts
alongside the prepare command result.
