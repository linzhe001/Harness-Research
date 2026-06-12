# WF9: Training Pipeline Validation

Use this gate between WF8 implementation and WF10 iteration. It checks semantic
equivalence against baselines and verifies that training, checkpointing, eval,
tracking, and git snapshot paths work before expensive loops begin.

## Read First

- Config path from arguments or `CLAUDE.md`.
- `CLAUDE.md` `## Entry Scripts` for Train/Eval commands.
- `project_map.json` for stable `src/` and `baselines/` nodes.
- `docs/Technical_Spec.md`, `docs/Implementation_Roadmap.md`,
  `docs/20_facts/Project_Glossary.md`, and `docs/20_facts/Codebase_Map.md`
  when present.
- Shared rules: `language-policy.md`, `ubiquitous-language.md`,
  `documentation-evidence-rule.md`, and `documentation-style.md`.

## Validation Flow

1. Locate review materials:
   - WF7 implementation files for data, model, loss, metrics, preprocessing,
     train script, and eval script.
   - Verified or partial baseline entry points and corresponding imported
     modules.
   - Design intent from technical spec and roadmap.
2. Always attempt Codex MCP review when available. Pair new and baseline code
   by dimension: data pipeline, model/rendering, loss, evaluation metrics, and
   training loop. If Codex is unavailable, perform a simplified self-review of
   metric computation and data normalization and record
   `codex_review: "unavailable"`.
3. Classify review findings as `critical`, `warning`, or `info`. Critical
   findings produce final verdict `REVIEW`, not automatic `FAIL`; the operator
   decides whether to proceed.
4. Review slice completion against `docs/Implementation_Roadmap.md`: slice
   trace, planned files, public interfaces, test/smoke commands, glossary
   vocabulary, dependency/API changes, and complexity budget.
5. Run 100-step training, usually:

   ```bash
   python {TRAIN_SCRIPT} --config {config_path} --max_steps 100 --exp_name smoke_test
   ```

   Record startup, completion, loss trend, NaN/Inf, OOM/crash, stderr summary,
   and GPU memory when available.
6. Verify checkpoint save/load with required fields such as model, optimizer,
   step, and git commit.
7. Run eval on the smoke checkpoint, usually:

   ```bash
   python {EVAL_SCRIPT} --checkpoint {smoke_test_checkpoint} --split val
   ```

   Record completion, protocol metrics, and generated outputs.
8. Verify wandb only when enabled. Verify git snapshot in smoke logs.
9. Create or refresh `docs/30_evidence/Validation_Table.md` and
   `docs/Validate_Run_Report.md` with reviewed slices, commands, raw log paths,
   review traces, failures, open validation questions, and final verdict.
10. Clean smoke-test temporary files so the experiment directory is not
    polluted.

## Verdicts

- `PASS`: smoke chain passed and no critical review findings.
- `REVIEW`: smoke chain passed but critical review findings require explicit
  operator decision.
- `FAIL`: any smoke-chain item failed.

If PASS, or REVIEW with explicit operator confirmation, update
`PROJECT_STATE.json` to mark WF9 completed and append validation history. If
FAIL, or REVIEW without confirmation, list failures and route to `/code-debug`.

## Hard Constraints

- Never skip review, training, checkpoint, eval, enabled tracking, or git
  snapshot checks.
- Do not invent metrics, logs, paths, or review results.
- Always report concrete error messages for failed steps.
- Keep checklist names, status labels, commands, and identifiers stable; follow
  language policy for surrounding prose.

## Durable Docs Render

After validation Markdown is finalized, invoke `/docs-site` or report
`docs_site_boundary_report` / `docs_site_render_or_NOT_RUN`. Do not render for
temporary drafts.
