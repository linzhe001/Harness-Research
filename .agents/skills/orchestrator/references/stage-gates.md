# Stage Gate Checks

Use these checks when validating `PROJECT_STATE.json` progress.

## State File Placement

- `PROJECT_STATE.json` must live at the repository root.
- `iteration_log.json` must live at the repository root.
- `project_map.json` must live at the repository root.
- `.agents/` may keep local references and volatile context only; it must not become the canonical home for project state.
- Run `python tooling/evidence/check_workflow_state.py --workspace-root .` when schema or cross-file consistency is in question.

## Evidence Tooling Invocation

These Python tools are part of the stage process, not optional decoration:

- Dynamic-context init must use `python tooling/evidence/init_context.py --workspace-root . --set-state` when shell access is available.
- Evidence table or open-question changes must trigger `python tooling/evidence/compile_protocol.py --workspace-root .`; apply generated drafts to `docs/35_protocol/**` only after review.
- Contract, fact, protocol, or release Markdown changes must trigger `python tooling/evidence/compile_doc.py --workspace-root . --doc <doc> --source <sources...>`.
- WF5/WF10/WF11/WF12 readiness must run `python tooling/evidence/check_dynamic_context.py --workspace-root . --stage <stage> --review-packet`.
- Explicit human contract approval must be recorded with `python tooling/evidence/approve_contract.py ...`, followed by another dynamic-context gate run.
- Stage transitions after state edits must run `python tooling/evidence/check_workflow_state.py --workspace-root .`.

If a tool cannot run, report the missing tool execution as an unverified gate.
Do not claim that the stage passed a machine gate based only on prose.

Evidence outputs are consumed by later gates and reviews:

- `.evidence/index.json` identifies the latest docchain for a current doc.
- `source_manifest.json` and Markdown hashes let docchain gates detect stale
  contracts/protocols/facts.
- review packets provide stable approval-source paths for human decisions.
- approval metadata in `PROJECT_STATE.json` is required by WF10/WF11/WF12 gates.

## Required Paths By Stage

Dynamic context mode is enabled when `PROJECT_STATE.json.context_model_version`
is `dynamic-protocol-v1` or any numbered dynamic-context directory exists
(`docs/10_contract`, `docs/20_facts`, `docs/30_evidence`, `docs/35_protocol`).
In that mode, the numbered docs below are required or warning-level gates as
noted. Older flat docs are compatibility inputs and should be migrated into the
fact layer rather than treated as a separate target for new projects.

`PROJECT_STATE.json.workflow_mode` should be explicit:

- `dynamic_context` for new projects using numbered context docs
- `standard` for new projects that intentionally do not use numbered context docs
- `compatibility` only for older imported projects that predate mandatory WF2/dynamic gates

WF2 is mandatory for both `dynamic_context` and `standard` projects. Only
`compatibility` can bypass the new-project WF2 hard gate.

- `survey_idea`
  - `docs/Feasibility_Report.md`
  - dynamic mode: `docs/30_evidence/Evidence_Index.md`
  - dynamic mode: `docs/30_evidence/Open_Questions.md`
  - dynamic mode: optional protocol compiler draft under `.evidence/protocol_compiler/**`
- `idea_debate` (WF2; required for new projects; skipping it is a hard failure)
  - `docs/Idea_Debate.md`
  - dynamic mode: may refresh `docs/35_protocol/Research_Protocol.md`
  - dynamic mode: protocol compiler draft should be reviewed before applying to `docs/35_protocol/**`
- `refine_idea` (WF3)
  - `docs/Refined_Idea.md`
  - dynamic mode: `docs/35_protocol/Research_Protocol.md`
  - dynamic mode: `docs/35_protocol/Protocol_Assumptions.md`
  - dynamic mode: protocol drift check should not report blocking open questions or due low-confidence assumptions for WF3
  - dynamic mode: generated protocol content must remain draft until contract approval
- `data_prep`
  - `docs/Dataset_Stats.md`
  - `PROJECT_STATE.json.dataset_paths`
  - `CLAUDE.md` dataset paths synchronized
  - `AGENTS.md` stable pointer to `CLAUDE.md` checked when `AGENTS.md` exists
- `baseline_repro`
  - `docs/Baseline_Report.md`
  - populated `baseline_metrics` in `PROJECT_STATE.json`
  - evaluation protocol or tracked metric names recorded for later WF10 comparison
  - dynamic mode: `docs/10_contract/Evaluation_Contract.md` exists; if missing, WF5 drafts it from baseline/evaluation evidence and routes it to human approval
  - dynamic mode: `docs/10_contract/Baseline_Contract.md` exists or is drafted from baseline evidence; required/skipped/reference baselines need human-readable review before later stages depend on them
  - dynamic mode: protocol drift check for WF5 should not report due low-confidence assumptions or blocking evidence questions
- `refine_arch` (WF6 architecture-design)
  - `docs/Technical_Spec.md`
  - must read `docs/Refined_Idea.md`, `docs/Dataset_Stats.md`, `docs/Baseline_Report.md`, and evaluation protocol or contracts when present
  - dynamic mode: architecture must not conflict with Project, Evaluation, Baseline, or Claim contracts without explicit review
- `deep_check` (WF6 design-review utility)
  - `docs/Sanity_Check_Log.md`
  - required when architecture changes claim boundaries, evaluation assumptions, core interfaces, or high-cost implementation direction
  - dynamic mode: conflicts trigger protocol drift or human review instead of silent contract edits
- `build_plan`
  - `docs/Implementation_Roadmap.md`
  - `project_map.json`
- `code_expert`
  - prefer `artifacts.code_modules` from `PROJECT_STATE.json`
  - fallback: `src/`, `scripts/train_smoke.py`, `scripts/eval_smoke.py`
- `validate_run`
  - `project_map.json`
  - `docs/Implementation_Roadmap.md`
  - `scripts/train_smoke.py`
  - `scripts/eval_smoke.py`
  - `scripts/train_all_scenes.py` when the project uses it
  - `docs/Validate_Run_Report.md`
  - report must include raw log paths, review trace path or `unavailable`, command evidence, and PASS/REVIEW/FAIL verdict
- `iterate`
  - `iteration_log.json`
  - `PROJECT_STATE.json.current_stage.latest_iteration` synchronized with the latest iteration record
  - `CLAUDE.md` current-stage summary synchronized with iteration progress
  - dynamic auto-iterate mode: `docs/10_contract/Evaluation_Contract.md` is approved or explicitly accepted by the operator for this run
  - dynamic auto-iterate mode: protocol drift check for WF10 should pass, or the operator explicitly accepts the review gap
  - WF10 → WF11 gate: only a `decision=CONTINUE` on the latest completed iteration allows advancing to WF11. `NEXT_ROUND` and `DEBUG` keep the project in WF10. `PIVOT` triggers rollback to WF2 idea-debate/refine-idea. `ABORT` terminates.
  - If auto-iterate is active, `.auto_iterate/state.json` may be read for loop status (read-only; orchestrator must not write to `.auto_iterate/`)
- `final_exp`
  - `docs/Final_Experiment_Matrix.md`
  - dynamic mode: read `docs/10_contract/Project_Contract.md`, `docs/10_contract/Evaluation_Contract.md`, `docs/10_contract/Baseline_Contract.md`, and `docs/10_contract/Claim_Boundary.md`
  - dynamic mode: protocol drift check for WF11 should pass before designing final experiments
- `release`
  - `submission/`
  - `submission/README.md`
  - `submission/manifest.json`
  - dynamic mode: release claims must respect `docs/10_contract/Claim_Boundary.md`
  - dynamic mode: protocol drift check for WF12 should pass before release claims are finalized

## Output Format

When checking a stage, report:

- current workflow id or name
- current status
- `missing_artifacts`
- a `checks` list with per-check:
  - `name`
  - `ok`
  - `required`
  - `present`
  - `missing`
  - optional `detail`
