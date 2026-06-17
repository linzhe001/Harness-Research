---
schema_version: "0.1"
page_id: "refine-idea"
title: "refine-idea"
kind: "skill"
audience: ["operator", "agent", "maintainer"]
source_type: "generated"
source_path: "workflow_handbook/skills/refine-idea.md"
source_of_truth: true
status: "generated"
summary: "Internal Harness instruction source for refine-idea. Route through visible Harness aliases or hook contracts instead of invoking directly."
nav:
  section: "skills"
  position: 80
canonical_sources:
  - path: "schemas/skill_contracts.json"
    role: "skill_contract"
    anchor: "refine-idea"
  - path: ".agents/skills/refine-idea/SKILL.md"
    role: "skill_source"
references: ["skill:refine-idea", "source:schemas/skill_contracts.json#refine-idea", "term:Gate Evidence"]
html:
  render: true
  output_path: "docs/_site/workflow_handbook/skills/refine-idea.html"
  preview_index_path: "docs/_views/workflow_handbook_reference_index.json"
---

# refine-idea

## Purpose

Internal Harness instruction source for refine-idea. Route through visible Harness aliases or hook contracts instead of invoking directly.

## Visibility

This page is an internal Skill Contract reference. Contract triggers below may include legacy or internal route names from `schemas/skill_contracts.json`; they are not the `$` autocomplete surface. Daily operator entry is limited to `$grill`, `$prepare`, `$build`, `$run`, `$analyze`, `$write`, `$change`.

## Triggers

- `$refine-idea`
- `/refine-idea`
- `refine-idea`
- `refine idea`
- `WF3`

## Can Write

- `docs/Refined_Idea.md`
- `docs/35_protocol/`
- `PROJECT_STATE.json`

## Final Outputs

- `current_doc: docs/Refined_Idea.md`
- `current_doc: docs/35_protocol/`

## Tool-Owned Outputs

- none

## Must Read

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

## Must Prove

- `compile_protocol_or_NOT_RUN`
- `check_protocol_drift_or_NOT_RUN`
- `workflow_state_gate_or_NOT_RUN`
- `gate_ledger`
- `docs_site_boundary_report`
- `refined_idea_write`
- `protocol_assumption_write`
- `canonical_state_edit`
- `docs_site_boundary_report`

## Constraints

- `protocol_as_approved_contract [hard_invariant/block; exception=never]`
- `architecture_decision_in_build_plan [workflow_default/notice; exception=overlay_allowed]`

## Exit Condition

Recommended reads have been considered; durable writes stay aligned with declared path ownership; Gate ledger reports command, result, reason, and artifacts when gate conditions are touched.

## Related References

- [[skill:refine-idea]]
- [[source:schemas/skill_contracts.json#refine-idea]]
- [[term:Gate Evidence]]
