# Harness Workflow Stage Cards

本文件由 `schemas/skill_contracts.json` 生成, 用作 operator 快速阅读入口。
contract 仍是权限和 gate 的 source of truth。

生成命令:

```bash
python tooling/codex_hooks/generate_stage_cards.py --workspace-root . --output workflow_handbook/Workflow_Stage_Cards.md
```

通用读法:

```text
Stage -> Purpose -> Inputs -> Can write -> Must read -> Must prove -> Cannot do -> Exit condition
```

## orchestrator

Purpose: Codex wrapper for the canonical WF orchestrator. Use when the user wants project initialization, stage status, gate checks, rollback, or decision logging around `PROJECT_STATE.json`.

Inputs / triggers:
- `$orchestrator`
- `/orchestrator`
- `orchestrator`
- `stage transition`
- `advance stage`
- `rollback`
- `workflow status`

Can write:
- `PROJECT_STATE.json`
- `iteration_log.json`
- `project_map.json`

Final outputs:
- `canonical_state: PROJECT_STATE.json`
- `canonical_state: iteration_log.json`
- `canonical_state: project_map.json`

Tool-owned outputs:
- none

Must read:
- `.agents/references/workflow-guide.md`
- `.agents/references/contract-gating-rule.md`
- `.agents/references/evidence-chain-rule.md`
- `.agents/references/language-policy.md`
- `.agents/skills/orchestrator/SKILL.md`
- `.agents/skills/orchestrator/references/stage-gates.md`
- `.agents/skills/orchestrator/references/project-state-schema.json`
- `AGENTS.md`
- `PROJECT_STATE.json`
- `iteration_log.json`
- `project_map.json`
- `docs/10_contract/Project_Contract.md`
- `docs/10_contract/Evaluation_Contract.md`
- `docs/10_contract/Baseline_Contract.md`
- `docs/10_contract/Claim_Boundary.md`

Must prove:
- `explicit_user_approval_for_transition`
- `workflow_state_gate_or_NOT_RUN`
- `gate_ledger`
- `stage_transition`
- `canonical_state_edit`
- `WF10_readiness`
- `WF11_readiness`
- `WF12_readiness`

Cannot do:
- `stage_transition_without_user_approval`
- `direct_edit_auto_iterate`
- `direct_edit_evidence`

Exit condition:
- Required reads are complete before writes; writes stay inside `write_scope.allowed_paths`; Gate ledger reports command, result, reason, and artifacts when gate conditions are touched.

## doc-compiler

Purpose: Compile current project documents from explicit evidence chains. Use when refreshing contract, fact, protocol, or release docs that need auditable evidence.

Inputs / triggers:
- `$doc-compiler`
- `/doc-compiler`
- `doc-compiler`
- `compile doc`
- `docchain`

Can write:
- `docs/10_contract/`
- `docs/20_facts/`
- `docs/35_protocol/`
- `.evidence/chains/`
- `.evidence/index.json`
- `docs/_views/`
- `docs/_site/`

Final outputs:
- `approved_contract: docs/10_contract/`
- `fact_doc: docs/20_facts/`
- `current_doc: docs/35_protocol/`

Tool-owned outputs:
- `tool_trace: .evidence/chains/`
- `tool_trace: .evidence/index.json`
- `generated_view: docs/_views/`
- `generated_view: docs/_site/`

Must read:
- `.agents/references/evidence-chain-rule.md`
- `.agents/references/documentation-evidence-rule.md`
- `.agents/references/documentation-style.md`
- `.agents/references/language-policy.md`
- `.agents/skills/doc-compiler/SKILL.md`
- `AGENTS.md`
- `PROJECT_STATE.json`
- `docs/10_contract/Project_Contract.md`
- `docs/20_facts/Project_Facts.md`
- `docs/35_protocol/Research_Protocol.md`

Must prove:
- `compile_doc_or_NOT_RUN`
- `check_docchain_gates_or_NOT_RUN`
- `gate_ledger`
- `docs_site_render_or_NOT_RUN`
- `current_doc_write`
- `contract_doc_write`
- `protocol_doc_write`
- `docs_site_render`

Cannot do:
- `manual_edit_evidence_chain`
- `current_doc_without_docchain`

Exit condition:
- Required reads are complete before writes; writes stay inside `write_scope.allowed_paths`; Gate ledger reports command, result, reason, and artifacts when gate conditions are touched.

## docs-site

Purpose: Render source Markdown project docs into human-readable HTML under docs/_site, with Evidence Chain hover previews from docs/_views/evidence_preview_index.json. Use after stable Markdown docs are finalized, before human review or handoff, or when explicitly rebuilding the human docs site.

Inputs / triggers:
- `$docs-site`
- `/docs-site`
- `docs-site`
- `docs site`
- `render docs`
- `HTML docs`
- `human docs`
- `rebuild docs site`

Can write:
- `docs/_views/`
- `docs/_site/`

Final outputs:
- none

Tool-owned outputs:
- `generated_view: docs/_site/`
- `tool_trace: docs/_views/evidence_preview_index.json`
- `tool_trace: docs/_site/manifest.json`

Must read:
- `.agents/references/evidence-chain-rule.md`
- `.agents/references/documentation-style.md`
- `.agents/references/language-policy.md`
- `.agents/references/ubiquitous-language.md`
- `.agents/skills/docs-site/SKILL.md`
- `AGENTS.md`
- `.evidence/index.json`
- `docs/10_contract/Project_Contract.md`
- `docs/20_facts/Codebase_Map.md`
- `docs/20_facts/Project_Glossary.md`
- `docs/Technical_Spec.md`
- `docs/Implementation_Roadmap.md`
- `docs/Validate_Run_Report.md`
- `docs/30_evidence/Validation_Table.md`
- `PROJECT_STATE.json`
- `project_map.json`
- `docs/_views/evidence_preview_index.json`
- `docs/_site/manifest.json`

Must prove:
- `build_evidence_preview_index_or_NOT_RUN`
- `build_docs_site_or_NOT_RUN`
- `validate_docs_site_or_NOT_RUN`
- `gate_ledger`
- `docs_site_render`
- `human_doc_html_write`
- `preview_index_write`

Cannot do:
- `manual_edit_evidence_chain`
- `direct_edit_evidence`
- `edit_source_markdown_during_render`
- `html_as_source_of_truth`

Exit condition:
- Required reads are complete before writes; writes stay inside `write_scope.allowed_paths`; Gate ledger reports command, result, reason, and artifacts when gate conditions are touched.

## review-packet

Purpose: Build concise human review packets for dynamic-context contracts, protocol readiness, and release gates.

Inputs / triggers:
- `$review-packet`
- `/review-packet`
- `review packet`
- `approve contract`
- `human approval`

Can write:
- `.evidence/review_packets/`
- `docs/10_contract/`
- `PROJECT_STATE.json`
- `docs/_views/`
- `docs/_site/`

Final outputs:
- `approved_contract: docs/10_contract/`

Tool-owned outputs:
- `tool_trace: .evidence/review_packets/`
- `generated_view: docs/_views/`
- `generated_view: docs/_site/`

Must read:
- `.agents/references/contract-gating-rule.md`
- `.agents/references/evidence-chain-rule.md`
- `.agents/references/lesson-quality-rule.md`
- `.agents/references/language-policy.md`
- `.agents/skills/review-packet/SKILL.md`
- `AGENTS.md`
- `PROJECT_STATE.json`
- `docs/10_contract/Project_Contract.md`
- `docs/10_contract/Evaluation_Contract.md`
- `docs/10_contract/Baseline_Contract.md`
- `docs/10_contract/Claim_Boundary.md`

Must prove:
- `check_dynamic_context_or_NOT_RUN`
- `build_review_packet_or_NOT_RUN`
- `approval_tool_only_after_explicit_human_approval`
- `gate_ledger`
- `docs_site_render_or_NOT_RUN`
- `contract_approval`
- `review_packet_build`
- `WF10_readiness`
- `WF11_readiness`
- `WF12_readiness`
- `docs_site_render`

Cannot do:
- `approve_without_explicit_human_approval`
- `packet_as_approval`

Exit condition:
- Required reads are complete before writes; writes stay inside `write_scope.allowed_paths`; Gate ledger reports command, result, reason, and artifacts when gate conditions are touched.

## protocol-compiler

Purpose: Compile Dynamic Research Protocol drafts from current evidence tables without using pre-baked research profiles.

Inputs / triggers:
- `$protocol-compiler`
- `/protocol-compiler`
- `protocol compiler`
- `compile protocol`

Can write:
- `.evidence/protocol_compiler/`
- `docs/35_protocol/`
- `docs/_views/`
- `docs/_site/`

Final outputs:
- `current_doc: docs/35_protocol/`

Tool-owned outputs:
- `tool_trace: .evidence/protocol_compiler/`
- `generated_view: docs/_views/`
- `generated_view: docs/_site/`

Must read:
- `.agents/references/evidence-chain-rule.md`
- `.agents/references/documentation-evidence-rule.md`
- `.agents/references/contract-gating-rule.md`
- `.agents/references/language-policy.md`
- `.agents/skills/protocol-compiler/SKILL.md`
- `AGENTS.md`
- `PROJECT_STATE.json`
- `docs/30_evidence/Evidence_Index.md`
- `docs/30_evidence/Open_Questions.md`
- `docs/35_protocol/Research_Protocol.md`

Must prove:
- `compile_protocol_or_NOT_RUN`
- `protocol_review_or_NOT_RUN`
- `docchain_gate_when_current_docs_change`
- `gate_ledger`
- `docs_site_render_or_NOT_RUN`
- `protocol_apply`
- `protocol_doc_write`
- `contract_readiness`
- `docs_site_render`

Cannot do:
- `protocol_as_approved_contract`
- `manual_edit_evidence_chain`

Exit condition:
- Required reads are complete before writes; writes stay inside `write_scope.allowed_paths`; Gate ledger reports command, result, reason, and artifacts when gate conditions are touched.

## protocol-drift-check

Purpose: Check whether dynamic research protocol drafts are stale before baseline, iteration, final experiment, or release gates.

Inputs / triggers:
- `$protocol-drift-check`
- `/protocol-drift-check`
- `protocol drift`
- `drift check`

Can write:
- `docs/35_protocol/`
- `docs/10_contract/`
- `docs/_views/`
- `docs/_site/`

Final outputs:
- `current_doc: docs/35_protocol/`
- `approved_contract: docs/10_contract/`

Tool-owned outputs:
- `generated_view: docs/_views/`
- `generated_view: docs/_site/`

Must read:
- `.agents/references/evidence-chain-rule.md`
- `.agents/references/contract-gating-rule.md`
- `.agents/references/documentation-evidence-rule.md`
- `.agents/references/language-policy.md`
- `.agents/skills/protocol-drift-check/SKILL.md`
- `AGENTS.md`
- `PROJECT_STATE.json`
- `docs/30_evidence/Open_Questions.md`
- `docs/35_protocol/Research_Protocol.md`
- `docs/35_protocol/Protocol_Changelog.md`

Must prove:
- `check_protocol_drift_or_NOT_RUN`
- `docchain_gate_when_current_docs_change`
- `gate_ledger`
- `docs_site_render_or_NOT_RUN`
- `protocol_readiness`
- `WF10_readiness`
- `WF11_readiness`
- `WF12_readiness`
- `docs_site_render`

Cannot do:
- `ignore_unresolved_protocol_drift`
- `protocol_as_approved_contract`

Exit condition:
- Required reads are complete before writes; writes stay inside `write_scope.allowed_paths`; Gate ledger reports command, result, reason, and artifacts when gate conditions are touched.

## survey-idea

Purpose: Codex wrapper for WF1 idea survey and feasibility analysis. Use when the user wants literature-backed validation of a new research idea and a `docs/Feasibility_Report.md` outcome.

Inputs / triggers:
- `$survey-idea`
- `/survey-idea`
- `survey-idea`
- `idea survey`
- `WF1`

Can write:
- `docs/Feasibility_Report.md`
- `docs/30_evidence/`
- `docs/35_protocol/`
- `PROJECT_STATE.json`
- `docs/_views/`
- `docs/_site/`

Final outputs:
- `current_doc: docs/Feasibility_Report.md`
- `current_doc: docs/30_evidence/`
- `current_doc: docs/35_protocol/`

Tool-owned outputs:
- `generated_view: docs/_views/`
- `generated_view: docs/_site/`

Must read:
- `.agents/references/workflow-guide.md`
- `.agents/references/context-layering-policy.md`
- `.agents/references/research-invariants.md`
- `.agents/references/ubiquitous-language.md`
- `.agents/references/documentation-evidence-rule.md`
- `.agents/references/documentation-style.md`
- `.agents/references/language-policy.md`
- `.agents/skills/survey-idea/SKILL.md`
- `.agents/skills/survey-idea/references/feasibility-report.md`
- `AGENTS.md`
- `PROJECT_STATE.json`
- `docs/20_facts/Project_Glossary.md`
- `docs/30_evidence/Evidence_Index.md`
- `docs/30_evidence/Open_Questions.md`
- `docs/35_protocol/Research_Protocol.md`

Must prove:
- `compile_protocol_or_NOT_RUN`
- `workflow_state_gate_or_NOT_RUN`
- `gate_ledger`
- `docs_site_render_or_NOT_RUN`
- `evidence_table_write`
- `feasibility_report_write`
- `canonical_state_edit`
- `docs_site_render`

Cannot do:
- `protocol_as_approved_contract`
- `direct_edit_evidence`

Exit condition:
- Required reads are complete before writes; writes stay inside `write_scope.allowed_paths`; Gate ledger reports command, result, reason, and artifacts when gate conditions are touched.

## idea-debate

Purpose: Codex wrapper for WF2 idea debate. Use after WF1 feasibility to stress-test candidate research directions before WF3 refine-idea and before any architecture design.

Inputs / triggers:
- `$idea-debate`
- `/idea-debate`
- `idea-debate`
- `idea debate`
- `WF2`

Can write:
- `docs/Idea_Debate.md`
- `docs/35_protocol/`
- `PROJECT_STATE.json`
- `docs/_views/`
- `docs/_site/`

Final outputs:
- `current_doc: docs/Idea_Debate.md`
- `current_doc: docs/35_protocol/`

Tool-owned outputs:
- `generated_view: docs/_views/`
- `generated_view: docs/_site/`

Must read:
- `.agents/references/workflow-guide.md`
- `.agents/references/context-layering-policy.md`
- `.agents/references/research-invariants.md`
- `.agents/references/ubiquitous-language.md`
- `.agents/references/documentation-evidence-rule.md`
- `.agents/references/documentation-style.md`
- `.agents/references/reviewer-independence.md`
- `.agents/references/review-tracing.md`
- `.agents/references/language-policy.md`
- `.agents/skills/idea-debate/SKILL.md`
- `.agents/skills/idea-debate/references/idea-debate-report.md`
- `AGENTS.md`
- `PROJECT_STATE.json`
- `docs/20_facts/Project_Glossary.md`
- `docs/Feasibility_Report.md`
- `docs/30_evidence/Evidence_Index.md`
- `docs/35_protocol/Research_Protocol.md`

Must prove:
- `compile_protocol_or_NOT_RUN`
- `check_protocol_drift_or_NOT_RUN`
- `workflow_state_gate_or_NOT_RUN`
- `gate_ledger`
- `docs_site_render_or_NOT_RUN`
- `idea_debate_report_write`
- `protocol_doc_write`
- `canonical_state_edit`
- `docs_site_render`

Cannot do:
- `protocol_as_approved_contract`
- `direct_edit_evidence`

Exit condition:
- Required reads are complete before writes; writes stay inside `write_scope.allowed_paths`; Gate ledger reports command, result, reason, and artifacts when gate conditions are touched.

## refine-idea

Purpose: Codex wrapper for WF3 idea refinement. Use after WF1 survey and WF2 idea debate to turn the selected direction into a feasible research idea, task framing, success criteria, baseline requirements, and protocol assumptions without designing the architecture.

Inputs / triggers:
- `$refine-idea`
- `/refine-idea`
- `refine-idea`
- `refine idea`
- `WF3`

Can write:
- `docs/Refined_Idea.md`
- `docs/35_protocol/`
- `PROJECT_STATE.json`
- `docs/_views/`
- `docs/_site/`

Final outputs:
- `current_doc: docs/Refined_Idea.md`
- `current_doc: docs/35_protocol/`

Tool-owned outputs:
- `generated_view: docs/_views/`
- `generated_view: docs/_site/`

Must read:
- `.agents/references/workflow-guide.md`
- `.agents/references/context-layering-policy.md`
- `.agents/references/research-invariants.md`
- `.agents/references/ubiquitous-language.md`
- `.agents/references/documentation-evidence-rule.md`
- `.agents/references/documentation-style.md`
- `.agents/references/language-policy.md`
- `.agents/skills/refine-idea/SKILL.md`
- `.agents/skills/refine-idea/references/refined-idea.md`
- `AGENTS.md`
- `PROJECT_STATE.json`
- `docs/20_facts/Project_Glossary.md`
- `OPERATOR_CONTEXT.md`
- `docs/Feasibility_Report.md`
- `docs/Idea_Debate.md`
- `docs/30_evidence/Evidence_Index.md`
- `docs/35_protocol/Research_Protocol.md`

Must prove:
- `compile_protocol_or_NOT_RUN`
- `check_protocol_drift_or_NOT_RUN`
- `workflow_state_gate_or_NOT_RUN`
- `gate_ledger`
- `docs_site_render_or_NOT_RUN`
- `refined_idea_write`
- `protocol_assumption_write`
- `canonical_state_edit`
- `docs_site_render`

Cannot do:
- `protocol_as_approved_contract`
- `architecture_decision_in_build_plan`

Exit condition:
- Required reads are complete before writes; writes stay inside `write_scope.allowed_paths`; Gate ledger reports command, result, reason, and artifacts when gate conditions are touched.

## data-prep

Purpose: Codex wrapper for WF4 data engineering. Use when the user wants dataset analysis, subset strategy selection, and `docs/Dataset_Stats.md` produced according to the original workflow.

Inputs / triggers:
- `$data-prep`
- `/data-prep`
- `data-prep`
- `dataset prep`
- `WF4`

Can write:
- `docs/Dataset_Stats.md`
- `docs/20_facts/`
- `docs/30_evidence/Dataset_Table.md`
- `PROJECT_STATE.json`
- `CLAUDE.md`
- `AGENTS.md`
- `configs/`
- `src/`
- `docs/_views/`
- `docs/_site/`

Final outputs:
- `current_doc: docs/Dataset_Stats.md`
- `conclusion_evidence: docs/30_evidence/Dataset_Table.md`
- `fact_doc: docs/20_facts/`

Tool-owned outputs:
- `generated_view: docs/_views/`
- `generated_view: docs/_site/`

Must read:
- `.agents/references/workflow-guide.md`
- `.agents/references/ubiquitous-language.md`
- `.agents/references/documentation-evidence-rule.md`
- `.agents/references/documentation-style.md`
- `.agents/references/language-policy.md`
- `.agents/skills/data-prep/SKILL.md`
- `.agents/skills/data-prep/references/dataset-stats.md`
- `AGENTS.md`
- `PROJECT_STATE.json`
- `CLAUDE.md`
- `docs/20_facts/Project_Glossary.md`
- `docs/Refined_Idea.md`
- `docs/20_facts/Execution_Contract.md`
- `docs/30_evidence/Dataset_Table.md`

Must prove:
- `compile_doc_or_NOT_RUN`
- `workflow_state_gate_or_NOT_RUN`
- `gate_ledger`
- `docs_site_render_or_NOT_RUN`
- `dataset_stats_write`
- `evidence_table_write`
- `dataset_config_write`
- `canonical_state_edit`
- `CLAUDE_dataset_sync`
- `docs_site_render`

Cannot do:
- `direct_edit_evidence`
- `direct_edit_auto_iterate`

Exit condition:
- Required reads are complete before writes; writes stay inside `write_scope.allowed_paths`; Gate ledger reports command, result, reason, and artifacts when gate conditions are touched.

## baseline-repro

Purpose: Codex wrapper for WF5 baseline reproduction. Use when the user wants baseline adaptation, reproduction tracking, and `docs/Baseline_Report.md` following the original workflow contract.

Inputs / triggers:
- `$baseline-repro`
- `/baseline-repro`
- `baseline-repro`
- `baseline repro`
- `WF5`

Can write:
- `docs/Baseline_Report.md`
- `docs/30_evidence/Baseline_Table.md`
- `docs/10_contract/`
- `docs/20_facts/Codebase_Map.md`
- `PROJECT_STATE.json`
- `project_map.json`
- `CLAUDE.md`
- `baselines/`
- `configs/`
- `scripts/`
- `src/`
- `docs/_views/`
- `docs/_site/`

Final outputs:
- `current_doc: docs/Baseline_Report.md`
- `conclusion_evidence: docs/30_evidence/Baseline_Table.md`
- `approved_contract: docs/10_contract/`

Tool-owned outputs:
- `generated_view: docs/_views/`
- `generated_view: docs/_site/`

Must read:
- `.agents/references/workflow-guide.md`
- `.agents/references/context-layering-policy.md`
- `.agents/references/contract-gating-rule.md`
- `.agents/references/pre-training-rule.md`
- `.agents/references/ubiquitous-language.md`
- `.agents/references/documentation-evidence-rule.md`
- `.agents/references/documentation-style.md`
- `.agents/references/language-policy.md`
- `.agents/skills/baseline-repro/SKILL.md`
- `.agents/skills/baseline-repro/references/baseline-report.md`
- `AGENTS.md`
- `PROJECT_STATE.json`
- `CLAUDE.md`
- `docs/20_facts/Project_Glossary.md`
- `docs/20_facts/Codebase_Map.md`
- `project_map.json`
- `docs/Refined_Idea.md`
- `docs/Dataset_Stats.md`
- `docs/30_evidence/Baseline_Table.md`
- `docs/10_contract/Evaluation_Contract.md`
- `docs/10_contract/Baseline_Contract.md`
- `docs/35_protocol/Research_Protocol.md`

Must prove:
- `check_protocol_drift_or_NOT_RUN`
- `check_dynamic_context_or_NOT_RUN`
- `workflow_state_gate_or_NOT_RUN`
- `codebase_map_sync_when_baseline_layout_changes`
- `semantic_commit_or_NOT_RUN`
- `gate_ledger`
- `docs_site_render_or_NOT_RUN`
- `baseline_report_write`
- `evidence_table_write`
- `codebase_map_write`
- `baseline_contract_readiness`
- `evaluation_contract_readiness`
- `canonical_state_edit`
- `stable_code_change`
- `docs_site_render`

Cannot do:
- `training_without_semantic_commit`
- `approve_without_explicit_human_approval`
- `protocol_as_approved_contract`

Exit condition:
- Required reads are complete before writes; writes stay inside `write_scope.allowed_paths`; Gate ledger reports command, result, reason, and artifacts when gate conditions are touched.

## refine-arch

Purpose: Codex wrapper for WF6 architecture design. Use after WF4 data preparation and WF5 baseline reproduction to convert the refined idea, dataset facts, baseline evidence, and evaluation contract into a technical spec and MVP architecture.

Inputs / triggers:
- `$refine-arch`
- `/refine-arch`
- `refine-arch`
- `refine arch`
- `architecture design`
- `WF6`

Can write:
- `docs/Technical_Spec.md`
- `docs/20_facts/Project_Glossary.md`
- `docs/35_protocol/`
- `PROJECT_STATE.json`
- `docs/_views/`
- `docs/_site/`

Final outputs:
- `current_doc: docs/Technical_Spec.md`
- `current_doc: docs/35_protocol/`
- `fact_doc: docs/20_facts/Project_Glossary.md`

Tool-owned outputs:
- `generated_view: docs/_views/`
- `generated_view: docs/_site/`

Must read:
- `.agents/references/workflow-guide.md`
- `.agents/references/context-layering-policy.md`
- `.agents/references/research-invariants.md`
- `.agents/references/code-style.md`
- `.agents/references/ubiquitous-language.md`
- `.agents/references/documentation-evidence-rule.md`
- `.agents/references/documentation-style.md`
- `.agents/references/language-policy.md`
- `.agents/skills/refine-arch/SKILL.md`
- `.agents/skills/refine-arch/references/technical-spec.md`
- `AGENTS.md`
- `PROJECT_STATE.json`
- `docs/20_facts/Project_Glossary.md`
- `docs/Refined_Idea.md`
- `docs/Dataset_Stats.md`
- `docs/Baseline_Report.md`
- `docs/10_contract/Evaluation_Contract.md`
- `docs/10_contract/Baseline_Contract.md`
- `docs/10_contract/Claim_Boundary.md`
- `docs/30_evidence/Evidence_Index.md`
- `docs/35_protocol/Research_Protocol.md`

Must prove:
- `check_protocol_drift_or_NOT_RUN`
- `workflow_state_gate_or_NOT_RUN`
- `gate_ledger`
- `docs_site_render_or_NOT_RUN`
- `technical_spec_write`
- `contract_conflict`
- `project_glossary_write`
- `canonical_state_edit`
- `docs_site_render`

Cannot do:
- `protocol_as_approved_contract`
- `project_map_stale`

Exit condition:
- Required reads are complete before writes; writes stay inside `write_scope.allowed_paths`; Gate ledger reports command, result, reason, and artifacts when gate conditions are touched.

## deep-check

Purpose: Codex design-review gate for WF6 architecture decisions. Use when the user wants a skeptical Go/No-Go review of the technical spec before implementation planning or heavy implementation starts.

Inputs / triggers:
- `$deep-check`
- `/deep-check`
- `deep-check`
- `deep check`
- `sanity check`
- `design review`

Can write:
- `docs/Sanity_Check_Log.md`
- `docs/35_protocol/`
- `docs/10_contract/`
- `docs/_views/`
- `docs/_site/`

Final outputs:
- `current_doc: docs/Sanity_Check_Log.md`
- `current_doc: docs/35_protocol/`
- `approved_contract: docs/10_contract/`

Tool-owned outputs:
- `generated_view: docs/_views/`
- `generated_view: docs/_site/`

Must read:
- `.agents/references/workflow-guide.md`
- `.agents/references/context-layering-policy.md`
- `.agents/references/research-invariants.md`
- `.agents/references/contract-gating-rule.md`
- `.agents/references/documentation-evidence-rule.md`
- `.agents/references/documentation-style.md`
- `.agents/references/reviewer-independence.md`
- `.agents/references/review-tracing.md`
- `.agents/references/language-policy.md`
- `.agents/skills/deep-check/SKILL.md`
- `.agents/skills/deep-check/references/sanity-check.md`
- `AGENTS.md`
- `PROJECT_STATE.json`
- `docs/Technical_Spec.md`
- `docs/10_contract/Project_Contract.md`
- `docs/10_contract/Evaluation_Contract.md`
- `docs/10_contract/Baseline_Contract.md`
- `docs/10_contract/Claim_Boundary.md`
- `docs/35_protocol/Research_Protocol.md`

Must prove:
- `codex_review_or_NOT_RUN`
- `external_model_review_or_NOT_RUN`
- `check_protocol_drift_or_NOT_RUN`
- `gate_ledger`
- `docs_site_render_or_NOT_RUN`
- `sanity_check_write`
- `review_trace_write`
- `contract_conflict`
- `docs_site_render`

Cannot do:
- `protocol_as_approved_contract`
- `approve_without_explicit_human_approval`

Exit condition:
- Required reads are complete before writes; writes stay inside `write_scope.allowed_paths`; Gate ledger reports command, result, reason, and artifacts when gate conditions are touched.

## evaluate

Purpose: Codex wrapper for experiment analysis and decision-making. Use when the user wants metrics interpreted, a stage or iteration report written, and a NEXT_ROUND, DEBUG, CONTINUE, PIVOT, or ABORT recommendation.

Inputs / triggers:
- `$evaluate`
- `/evaluate`
- `evaluate`
- `eval results`
- `iteration eval`

Can write:
- `iteration_log.json`
- `docs/40_iterations/`
- `docs/iterations/`
- `docs/50_memory/`
- `MEMORY.md`
- `docs/Stage_Report.md`
- `docs/_views/`
- `docs/_site/`

Final outputs:
- `current_doc: docs/40_iterations/`
- `current_doc: docs/50_memory/`
- `current_doc: docs/Stage_Report.md`

Tool-owned outputs:
- `generated_view: docs/_views/`
- `generated_view: docs/_site/`

Must read:
- `.agents/references/workflow-guide.md`
- `.agents/references/context-layering-policy.md`
- `.agents/references/lesson-quality-rule.md`
- `.agents/references/documentation-evidence-rule.md`
- `.agents/references/documentation-style.md`
- `.agents/references/reviewer-independence.md`
- `.agents/references/review-tracing.md`
- `.agents/references/language-policy.md`
- `.agents/skills/evaluate/SKILL.md`
- `.agents/skills/evaluate/references/stage-report.md`
- `AGENTS.md`
- `PROJECT_STATE.json`
- `iteration_log.json`
- `docs/10_contract/Evaluation_Contract.md`
- `docs/10_contract/Baseline_Contract.md`
- `docs/50_memory/Lessons.md`
- `MEMORY.md`

Must prove:
- `decision_vocabulary`
- `lesson_quality_check_or_NOT_RUN`
- `workflow_state_gate_or_NOT_RUN`
- `gate_ledger`
- `docs_site_render_or_NOT_RUN`
- `stage_report_write`
- `iteration_report_write`
- `lesson_promotion`
- `iteration_log_write`
- `docs_site_render`

Cannot do:
- `stage_transition_from_iterate`
- `auto_observation_direct_to_MEMORY`
- `protocol_as_approved_contract`

Exit condition:
- Required reads are complete before writes; writes stay inside `write_scope.allowed_paths`; Gate ledger reports command, result, reason, and artifacts when gate conditions are touched.

## init-project

Purpose: WF0/bootstrap wrapper for staged `CLAUDE.md` generation and updates. Use when the user wants the compact project snapshot initialized or refreshed while preserving the original staged template behavior.

Inputs / triggers:
- `$init`
- `$init-project`
- `/init`
- `/init-project`
- `init-project`
- `init project`
- `WF0`
- `bootstrap init`

Can write:
- `CLAUDE.md`
- `AGENTS.md`
- `OPERATOR_CONTEXT.md`
- `PROJECT_STATE.json`
- `docs/`
- `.evidence/`
- `docs/_views/`
- `docs/_site/`

Final outputs:
- `guidance: CLAUDE.md`
- `guidance: AGENTS.md`
- `guidance: OPERATOR_CONTEXT.md`

Tool-owned outputs:
- `tool_trace: .evidence/`
- `generated_view: docs/_views/`
- `generated_view: docs/_site/`

Must read:
- `.agents/references/context-layering-policy.md`
- `.agents/references/ubiquitous-language.md`
- `.agents/references/documentation-evidence-rule.md`
- `.agents/references/documentation-style.md`
- `.agents/references/language-policy.md`
- `.agents/skills/init-project/SKILL.md`
- `.agents/skills/init-project/references/claude-md-template.md`
- `.agents/skills/init-project/references/claude-maintenance.md`
- `AGENTS.md`
- `PROJECT_STATE.json`
- `CLAUDE.md`
- `OPERATOR_CONTEXT.md`
- `docs/Feasibility_Report.md`
- `docs/Dataset_Stats.md`
- `docs/Baseline_Report.md`
- `project_map.json`

Must prove:
- `context_gate_or_NOT_RUN`
- `workflow_state_gate_or_NOT_RUN`
- `gate_ledger`
- `docs_site_render_or_NOT_RUN`
- `dynamic_context_init`
- `CLAUDE_write`
- `operator_context_write`
- `canonical_state_edit`
- `docs_site_render`

Cannot do:
- `direct_edit_evidence`
- `direct_edit_auto_iterate`

Exit condition:
- Required reads are complete before writes; writes stay inside `write_scope.allowed_paths`; Gate ledger reports command, result, reason, and artifacts when gate conditions are touched.

## env-setup

Purpose: Codex wrapper for environment creation and refresh. Use when the user wants the environment detected, created, or synchronized into the legacy `CLAUDE.md` format.

Inputs / triggers:
- `$env-setup`
- `/env-setup`
- `env-setup`
- `environment refresh`
- `deps changed`
- `dependency refresh`

Can write:
- `CLAUDE.md`
- `requirements.txt`
- `requirements-dev.txt`
- `environment.yml`
- `environment.yaml`
- `pyproject.toml`
- `scripts/`
- `configs/`

Final outputs:
- `guidance: CLAUDE.md`
- `operational_scope: requirements.txt`
- `operational_scope: requirements-dev.txt`
- `operational_scope: environment.yml`
- `operational_scope: environment.yaml`
- `operational_scope: pyproject.toml`

Tool-owned outputs:
- none

Must read:
- `.agents/references/deps-update-rule.md`
- `.agents/references/documentation-style.md`
- `.agents/references/language-policy.md`
- `.agents/skills/env-setup/SKILL.md`
- `.agents/skills/env-setup/references/environment-refresh.md`
- `.agents/skills/init-project/references/claude-maintenance.md`
- `AGENTS.md`
- `CLAUDE.md`
- `PROJECT_STATE.json`
- `requirements.txt`
- `requirements-dev.txt`
- `environment.yml`
- `environment.yaml`
- `pyproject.toml`

Must prove:
- `py_compile_or_NOT_RUN`
- `ruff_or_NOT_RUN`
- `gate_ledger`
- `dependency_file_change`
- `environment_section_write`
- `setup_command_run`

Cannot do:
- `training_without_semantic_commit`
- `direct_edit_auto_iterate`

Exit condition:
- Required reads are complete before writes; writes stay inside `write_scope.allowed_paths`; Gate ledger reports command, result, reason, and artifacts when gate conditions are touched.

## build-plan

Purpose: Codex wrapper for WF7 implementation planning. Use after WF6 architecture design when the user wants `docs/Implementation_Roadmap.md`, `project_map.json`, and `docs/20_facts/Codebase_Map.md` built from the technical spec, baseline evidence, templates, and schemas.

Inputs / triggers:
- `$build-plan`
- `/build-plan`
- `build plan`
- `implementation roadmap`
- `WF7`

Can write:
- `project_map.json`
- `PROJECT_STATE.json`
- `docs/20_facts/Project_Glossary.md`
- `docs/20_facts/Codebase_Map.md`
- `docs/Implementation_Roadmap.md`
- `docs/_views/`
- `docs/_site/`

Final outputs:
- `current_doc: docs/Implementation_Roadmap.md`
- `fact_doc: docs/20_facts/Project_Glossary.md`
- `fact_doc: docs/20_facts/Codebase_Map.md`

Tool-owned outputs:
- `generated_view: docs/_views/`
- `generated_view: docs/_site/`

Must read:
- `.agents/references/workflow-guide.md`
- `.agents/references/contract-gating-rule.md`
- `.agents/references/ubiquitous-language.md`
- `.agents/references/documentation-evidence-rule.md`
- `.agents/references/documentation-style.md`
- `.agents/references/project-map-rule.md`
- `.agents/references/sliced-commit-rule.md`
- `.agents/skills/build-plan/SKILL.md`
- `.agents/skills/build-plan/references/implementation-roadmap.md`
- `.agents/skills/build-plan/references/project-map-schema.json`
- `AGENTS.md`
- `PROJECT_STATE.json`
- `project_map.json`
- `docs/20_facts/Project_Glossary.md`
- `docs/20_facts/Codebase_Map.md`
- `docs/Technical_Spec.md`
- `docs/Baseline_Report.md`
- `docs/10_contract/Evaluation_Contract.md`
- `docs/10_contract/Baseline_Contract.md`

Must prove:
- `write_implementation_roadmap`
- `update_project_map`
- `workflow_state_gate_or_NOT_RUN`
- `gate_ledger`
- `docs_site_render_or_NOT_RUN`
- `project_map_write`
- `project_glossary_write`
- `codebase_map_write`
- `canonical_state_edit`
- `docs_site_render`

Cannot do:
- `architecture_decision_in_build_plan`
- `project_map_stale`

Exit condition:
- Required reads are complete before writes; writes stay inside `write_scope.allowed_paths`; Gate ledger reports command, result, reason, and artifacts when gate conditions are touched.

## code-expert

Purpose: Codex wrapper for WF8 first-pass code generation. Use when the user wants implementation generated directly from `project_map.json`, `docs/20_facts/Codebase_Map.md`, the roadmap, and the original Claude skill contract.

Inputs / triggers:
- `$code-expert`
- `/code-expert`
- `code-expert`
- `implement`
- `WF8`

Can write:
- `src/`
- `scripts/`
- `configs/`
- `project_map.json`
- `docs/20_facts/Codebase_Map.md`
- `PROJECT_STATE.json`
- `docs/_views/`
- `docs/_site/`
- `.evidence/chains/`
- `.evidence/index.json`

Final outputs:
- `implementation: src/`
- `implementation: scripts/`
- `implementation: configs/`

Tool-owned outputs:
- `generated_view: docs/_views/`
- `generated_view: docs/_site/`
- `tool_trace: .evidence/chains/`
- `tool_trace: .evidence/index.json`

Must read:
- `.agents/references/code-style.md`
- `.agents/references/contract-gating-rule.md`
- `.agents/references/ubiquitous-language.md`
- `.agents/references/language-policy.md`
- `.agents/references/project-map-rule.md`
- `.agents/references/pre-training-rule.md`
- `.agents/references/sliced-commit-rule.md`
- `.agents/skills/code-expert/SKILL.md`
- `.agents/skills/code-expert/references/generation-order.md`
- `AGENTS.md`
- `PROJECT_STATE.json`
- `project_map.json`
- `CLAUDE.md`
- `docs/20_facts/Project_Glossary.md`
- `docs/20_facts/Codebase_Map.md`
- `docs/Implementation_Roadmap.md`
- `docs/10_contract/Evaluation_Contract.md`
- `docs/10_contract/Baseline_Contract.md`

Must prove:
- `read_project_map_before_stable_code`
- `py_compile_or_NOT_RUN`
- `ruff_or_NOT_RUN`
- `semantic_commit_or_NOT_RUN`
- `workflow_state_gate_or_NOT_RUN`
- `gate_ledger`
- `docs_site_render_or_NOT_RUN`
- `compile_doc_or_NOT_RUN`
- `stable_code_change`
- `project_map_write`
- `codebase_map_write`
- `canonical_state_edit`
- `docs_site_render`
- `codebase_map_docchain`

Cannot do:
- `stable_code_without_project_map_read`
- `project_map_stale`
- `training_without_semantic_commit`

Exit condition:
- Required reads are complete before writes; writes stay inside `write_scope.allowed_paths`; Gate ledger reports command, result, reason, and artifacts when gate conditions are touched.

## code-debug

Purpose: Codex wrapper for post-WF8 repository implementation code modification and debugging. Use for planned iteration changes, bug fixes, or tightly scoped performance edits under src, scripts, configs, project_map, or Codebase_Map. Do not use for Codex hooks, skill contracts, skill routing, or permission policy; use harness-maintenance for those.

Inputs / triggers:
- `$code-debug`
- `/code-debug`
- `code-debug`
- `debug`
- `fix`

Can write:
- `src/`
- `scripts/`
- `configs/`
- `project_map.json`
- `docs/20_facts/Codebase_Map.md`
- `docs/_views/`
- `docs/_site/`
- `.evidence/chains/`
- `.evidence/index.json`

Final outputs:
- `implementation: src/`
- `implementation: scripts/`
- `implementation: configs/`

Tool-owned outputs:
- `generated_view: docs/_views/`
- `generated_view: docs/_site/`
- `tool_trace: .evidence/chains/`
- `tool_trace: .evidence/index.json`

Must read:
- `.agents/references/code-style.md`
- `.agents/references/ubiquitous-language.md`
- `.agents/references/language-policy.md`
- `.agents/references/project-map-rule.md`
- `.agents/references/pre-training-rule.md`
- `.agents/references/sliced-commit-rule.md`
- `.agents/skills/code-debug/SKILL.md`
- `.agents/skills/code-debug/references/debug-modes.md`
- `AGENTS.md`
- `project_map.json`
- `CLAUDE.md`
- `docs/20_facts/Project_Glossary.md`
- `docs/20_facts/Codebase_Map.md`
- `docs/Validate_Run_Report.md`
- `iteration_log.json`

Must prove:
- `read_project_map_before_stable_code`
- `py_compile_or_NOT_RUN`
- `ruff_or_NOT_RUN`
- `semantic_commit_or_NOT_RUN`
- `gate_ledger`
- `docs_site_render_or_NOT_RUN`
- `compile_doc_or_NOT_RUN`
- `stable_code_change`
- `project_map_write`
- `codebase_map_write`
- `docs_site_render`
- `codebase_map_docchain`

Cannot do:
- `stable_code_without_project_map_read`
- `project_map_stale`
- `training_without_semantic_commit`

Exit condition:
- Required reads are complete before writes; writes stay inside `write_scope.allowed_paths`; Gate ledger reports command, result, reason, and artifacts when gate conditions are touched.

## harness-maintenance

Purpose: Maintain Harness framework guardrails: Codex hooks, evidence tooling guardrails, skill contracts, skill routing/triggers, permission policy docs, schema/tests, bootstrap templates, and .agents/.claude guidance alignment. Use when modifying tooling/codex_hooks, tooling/evidence guardrails, schemas/skill_contracts.json, schemas/skill_contracts.schema.json, .agents/skills, .agents/references, .claude/Workflow_Guide.md, .claude/skills, .claude/rules, .claude/shared, templates, hook detection, hook trust/status, schema validation, or permission boundaries.

Inputs / triggers:
- `$harness-maintenance`
- `/harness-maintenance`
- `harness-maintenance`
- `harness maintenance`
- `hook maintenance`
- `hook detection`
- `hook trigger`
- `hook routing`

Can write:
- `.agents/skills/`
- `.agents/references/`
- `.claude/Workflow_Guide.md`
- `.claude/skills/`
- `.claude/rules/`
- `.claude/shared/`
- `tooling/codex_hooks/`
- `tooling/evidence/`
- `tooling/model_api/`
- `tooling/.tests/`
- `templates/`
- `schemas/`
- `docs/`
- `workflow_handbook/`
- `.gitignore`
- `AGENTS.md`
- `AGENTS.md.template`
- `CLAUDE.md`
- `CLAUDE.md.template`
- `README.md`
- `AI_AGENT_SETUP.md`

Final outputs:
- `current_doc: tooling/codex_hooks/README.md`
- `current_doc: tooling/codex_hooks/Stage_Permission_Elevation_Guide.md`
- `current_doc: workflow_handbook/`
- `current_doc: README.md`
- `current_doc: AI_AGENT_SETUP.md`
- `guidance: AGENTS.md`
- `guidance: AGENTS.md.template`
- `guidance: CLAUDE.md`
- `guidance: CLAUDE.md.template`
- `guidance: .agents/skills/`
- `guidance: .agents/references/`
- `guidance: .claude/Workflow_Guide.md`
- `guidance: .claude/skills/`
- `guidance: .claude/rules/`
- `guidance: .claude/shared/`
- `guidance: templates/`

Tool-owned outputs:
- none

Must read:
- `.agents/references/code-style.md`
- `.agents/references/language-policy.md`
- `.agents/references/ubiquitous-language.md`
- `tooling/codex_hooks/README.md`
- `schemas/skill_contracts.json`
- `schemas/skill_contracts.schema.json`
- `tooling/.tests/test_codex_hooks_contracts.py`
- `.agents/skills/harness-maintenance/SKILL.md`
- `AGENTS.md`
- `CLAUDE.md`
- `.codex/config.toml`
- `.codex/hooks.json`
- `.codex/rules/harness_external_review.rules`
- `tooling/codex_hooks/Stage_Permission_Elevation_Guide.md`

Must prove:
- `py_compile_or_NOT_RUN`
- `ruff_or_NOT_RUN`
- `gate_ledger`
- `hook_runtime_change`
- `hook_contract_change`
- `skill_contract_change`
- `skill_routing_change`
- `permission_policy_change`

Cannot do:
- `direct_edit_auto_iterate`
- `direct_edit_evidence`
- `manual_edit_auto_iterate`
- `manual_edit_evidence_chain`

Exit condition:
- Required reads are complete before writes; writes stay inside `write_scope.allowed_paths`; Gate ledger reports command, result, reason, and artifacts when gate conditions are touched.

## code-review

Purpose: Review code, docs-supporting code, and git diffs with line-referenced findings, git metadata, Codex review, optional external model cross-check, and a reconciled report.

Inputs / triggers:
- `$code-review`
- `/code-review`
- `code-review`
- `code review`
- `review code`
- `codex review`
- `deepseek review`
- `external model review`

Can write:
- `.agents/state/review_traces/code-review/`

Final outputs:
- `review_trace: .agents/state/review_traces/code-review/`

Tool-owned outputs:
- none

Must read:
- `.agents/references/code-style.md`
- `.agents/references/contract-gating-rule.md`
- `.agents/references/language-policy.md`
- `.agents/references/project-map-rule.md`
- `.agents/references/review-tracing.md`
- `.agents/references/reviewer-independence.md`
- `.agents/skills/code-review/SKILL.md`
- `.agents/skills/code-review/references/review-report.md`
- `AGENTS.md`
- `CLAUDE.md`
- `project_map.json`
- `docs/Implementation_Roadmap.md`
- `docs/Validate_Run_Report.md`
- `iteration_log.json`
- `.agents/state/current_iteration.json`

Must prove:
- `collect_review_scope`
- `git_metadata_snapshot`
- `changed_line_map`
- `codex_review_or_NOT_RUN`
- `external_model_review_or_NOT_RUN`
- `reconcile_review_findings`
- `write_review_report_or_NOT_RUN`
- `gate_ledger`
- `post_code_change_review`
- `code_review_report_write`
- `docs_or_evidence_chain_review`
- `heavy_review`

Cannot do:
- `modify_subject_files_during_code_review`
- `review_without_line_references`
- `unverified_model_finding_as_fact`
- `heavy_review_without_trace`

Exit condition:
- Required reads are complete before writes; writes stay inside `write_scope.allowed_paths`; Gate ledger reports command, result, reason, and artifacts when gate conditions are touched.

## validate-run

Purpose: Codex wrapper for WF9 validation. Use when the user wants the training chain reviewed and smoke-tested before entering WF10.

Inputs / triggers:
- `$validate-run`
- `/validate-run`
- `validate-run`
- `smoke test`
- `WF9`

Can write:
- `docs/Validate_Run_Report.md`
- `docs/30_evidence/Validation_Table.md`
- `PROJECT_STATE.json`
- `docs/_views/`
- `docs/_site/`

Final outputs:
- `current_doc: docs/Validate_Run_Report.md`
- `conclusion_evidence: docs/30_evidence/Validation_Table.md`

Tool-owned outputs:
- `generated_view: docs/_views/`
- `generated_view: docs/_site/`

Must read:
- `.agents/references/workflow-guide.md`
- `.agents/references/contract-gating-rule.md`
- `.agents/references/ubiquitous-language.md`
- `.agents/references/documentation-evidence-rule.md`
- `.agents/references/documentation-style.md`
- `.agents/references/reviewer-independence.md`
- `.agents/references/review-tracing.md`
- `.agents/skills/validate-run/SKILL.md`
- `.agents/skills/validate-run/references/review-checklist.md`
- `.agents/skills/validate-run/references/validate-run-report.md`
- `AGENTS.md`
- `PROJECT_STATE.json`
- `project_map.json`
- `CLAUDE.md`
- `docs/Implementation_Roadmap.md`
- `docs/20_facts/Project_Glossary.md`
- `docs/20_facts/Codebase_Map.md`
- `docs/Technical_Spec.md`
- `docs/Baseline_Report.md`
- `docs/30_evidence/Validation_Table.md`
- `docs/10_contract/Evaluation_Contract.md`
- `docs/10_contract/Baseline_Contract.md`

Must prove:
- `semantic_review`
- `smoke_test_or_NOT_RUN`
- `write_validate_report`
- `workflow_state_gate_or_NOT_RUN`
- `gate_ledger`
- `docs_site_render_or_NOT_RUN`
- `WF10_readiness`
- `validate_report_write`
- `evidence_table_write`
- `docs_site_render`

Cannot do:
- `WF9_PASS_without_semantic_review`
- `WF9_PASS_without_smoke_evidence`

Exit condition:
- Required reads are complete before writes; writes stay inside `write_scope.allowed_paths`; Gate ledger reports command, result, reason, and artifacts when gate conditions are touched.

## iterate

Purpose: Codex wrapper for WF10 structured iteration. Use when the user wants to run `plan`, `code`, `run`, `eval`, `ablate`, `status`, or `log` while preserving the original iteration schema and workflow logic.

Inputs / triggers:
- `$iterate`
- `/iterate`
- `iterate`
- `NEXT_ROUND`
- `DEBUG`
- `CONTINUE`
- `PIVOT`
- `ABORT`

Can write:
- `iteration_log.json`
- `docs/40_iterations/`
- `docs/iterations/`
- `docs/50_memory/`
- `MEMORY.md`
- `docs/_views/`
- `docs/_site/`

Final outputs:
- `current_doc: docs/40_iterations/`
- `current_doc: docs/50_memory/`

Tool-owned outputs:
- `generated_view: docs/_views/`
- `generated_view: docs/_site/`

Must read:
- `.agents/references/workflow-guide.md`
- `.agents/references/contract-gating-rule.md`
- `.agents/references/lesson-quality-rule.md`
- `.agents/references/ubiquitous-language.md`
- `.agents/references/documentation-evidence-rule.md`
- `.agents/references/documentation-style.md`
- `.agents/references/reviewer-independence.md`
- `.agents/references/review-tracing.md`
- `.agents/skills/iterate/SKILL.md`
- `.agents/skills/iterate/references/iteration-log-schema.json`
- `.agents/skills/iterate/references/iteration-context.md`
- `.agents/skills/iterate/references/iteration-constraints.md`
- `AGENTS.md`
- `PROJECT_STATE.json`
- `iteration_log.json`
- `docs/20_facts/Project_Glossary.md`
- `docs/10_contract/Evaluation_Contract.md`
- `docs/10_contract/Baseline_Contract.md`
- `docs/50_memory/Lessons.md`
- `MEMORY.md`

Must prove:
- `iteration_log_update`
- `decision_vocabulary`
- `lesson_quality_check_or_NOT_RUN`
- `gate_ledger`
- `docs_site_render_or_NOT_RUN`
- `iteration_log_write`
- `iteration_report_write`
- `lesson_promotion`
- `WF11_handoff`
- `docs_site_render`

Cannot do:
- `auto_observation_direct_to_MEMORY`
- `manual_edit_auto_iterate`
- `stage_transition_from_iterate`

Exit condition:
- Required reads are complete before writes; writes stay inside `write_scope.allowed_paths`; Gate ledger reports command, result, reason, and artifacts when gate conditions are touched.

## auto-iterate-goal

Purpose: Generate or validate the auto-iterate goal file before launching WF10 auto-iterate

Inputs / triggers:
- `$auto-iterate-goal`
- `/auto-iterate-goal`
- `auto iterate goal`
- `auto-iterate goal`
- `WF10 auto`

Can write:
- `docs/auto_iterate_goal.md`
- `docs/_views/`
- `docs/_site/`

Final outputs:
- `current_doc: docs/auto_iterate_goal.md`

Tool-owned outputs:
- `generated_view: docs/_views/`
- `generated_view: docs/_site/`

Must read:
- `.agents/references/workflow-guide.md`
- `.agents/references/context-layering-policy.md`
- `.agents/references/contract-gating-rule.md`
- `.agents/references/lesson-quality-rule.md`
- `.agents/references/documentation-evidence-rule.md`
- `.agents/references/documentation-style.md`
- `.agents/skills/auto-iterate-goal/SKILL.md`
- `.agents/skills/evaluate/references/stage-report.md`
- `AGENTS.md`
- `PROJECT_STATE.json`
- `iteration_log.json`
- `docs/auto_iterate_goal.md`
- `docs/10_contract/Evaluation_Contract.md`
- `docs/10_contract/Baseline_Contract.md`
- `docs/Validate_Run_Report.md`

Must prove:
- `goal_validate_or_init`
- `context_gate_or_NOT_RUN`
- `gate_ledger`
- `docs_site_render_or_NOT_RUN`
- `WF10_auto_readiness`
- `goal_write`
- `docs_site_render`

Cannot do:
- `start_auto_iterate_without_goal_validation`
- `manual_edit_auto_iterate`

Exit condition:
- Required reads are complete before writes; writes stay inside `write_scope.allowed_paths`; Gate ledger reports command, result, reason, and artifacts when gate conditions are touched.

## final-exp

Purpose: Codex wrapper for WF11 final experiment planning. Use when the user wants ablations, robustness tests, cross-dataset evaluation, and compute budgeting organized according to the original template.

Inputs / triggers:
- `$final-exp`
- `/final-exp`
- `final experiment`
- `WF11`

Can write:
- `docs/Final_Experiment_Matrix.md`
- `PROJECT_STATE.json`
- `docs/_views/`
- `docs/_site/`

Final outputs:
- `current_doc: docs/Final_Experiment_Matrix.md`

Tool-owned outputs:
- `generated_view: docs/_views/`
- `generated_view: docs/_site/`

Must read:
- `.agents/references/workflow-guide.md`
- `.agents/references/context-layering-policy.md`
- `.agents/references/contract-gating-rule.md`
- `.agents/references/documentation-evidence-rule.md`
- `.agents/references/documentation-style.md`
- `.agents/skills/final-exp/SKILL.md`
- `.agents/skills/final-exp/references/experiment-matrix.md`
- `AGENTS.md`
- `PROJECT_STATE.json`
- `iteration_log.json`
- `docs/10_contract/Project_Contract.md`
- `docs/10_contract/Evaluation_Contract.md`
- `docs/10_contract/Baseline_Contract.md`
- `docs/10_contract/Claim_Boundary.md`

Must prove:
- `respect_evaluation_contract`
- `respect_claim_boundary`
- `check_dynamic_context_or_NOT_RUN`
- `gate_ledger`
- `docs_site_render_or_NOT_RUN`
- `WF11_readiness`
- `final_experiment_matrix_write`
- `docs_site_render`

Cannot do:
- `final_exp_outside_claim_boundary`
- `WF11_without_approved_contracts`

Exit condition:
- Required reads are complete before writes; writes stay inside `write_scope.allowed_paths`; Gate ledger reports command, result, reason, and artifacts when gate conditions are touched.

## release

Purpose: Codex wrapper for WF12 release and submission packaging. Use when the user wants validation, packaging, or submission preparation according to the original workflow.

Inputs / triggers:
- `$release`
- `/release`
- `release`
- `submit`
- `package`
- `WF12`

Can write:
- `submission/`
- `docs/`
- `PROJECT_STATE.json`
- `docs/_views/`
- `docs/_site/`

Final outputs:
- `release_package: submission/`
- `current_doc: docs/60_release/`

Tool-owned outputs:
- `generated_view: docs/_views/`
- `generated_view: docs/_site/`

Must read:
- `.agents/references/workflow-guide.md`
- `.agents/references/context-layering-policy.md`
- `.agents/references/contract-gating-rule.md`
- `.agents/references/evidence-chain-rule.md`
- `.agents/references/documentation-evidence-rule.md`
- `.agents/references/documentation-style.md`
- `.agents/skills/release/SKILL.md`
- `.agents/skills/release/references/release-checklist.md`
- `.agents/skills/release/references/release-manifest.md`
- `AGENTS.md`
- `PROJECT_STATE.json`
- `iteration_log.json`
- `CLAUDE.md`
- `docs/10_contract/Project_Contract.md`
- `docs/10_contract/Evaluation_Contract.md`
- `docs/10_contract/Baseline_Contract.md`
- `docs/10_contract/Claim_Boundary.md`

Must prove:
- `check_dynamic_context_wf12_or_NOT_RUN`
- `release_manifest_validation`
- `claim_boundary_check`
- `gate_ledger`
- `docs_site_render_or_NOT_RUN`
- `WF12_readiness`
- `release_claim`
- `submission_package_write`
- `docs_site_render`

Cannot do:
- `release_claim_outside_claim_boundary`
- `submit_without_explicit_user_request`
- `overwrite_package_without_confirmation`

Exit condition:
- Required reads are complete before writes; writes stay inside `write_scope.allowed_paths`; Gate ledger reports command, result, reason, and artifacts when gate conditions are touched.
