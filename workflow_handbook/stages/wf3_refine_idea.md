---
schema_version: "0.1"
page_id: "wf3_refine_idea"
title: "WF3 Refine Idea"
kind: "stage"
audience: ["operator", "agent", "maintainer"]
source_type: "generated"
source_path: "workflow_handbook/stages/wf3_refine_idea.md"
source_of_truth: true
status: "generated"
summary: "Turn the selected idea into a tighter research question and execution target."
nav:
  section: "stages"
  position: 30
canonical_sources:
  - path: "schemas/skill_contracts.json"
    role: "skill_contract"
    anchor: "refine-idea"
  - path: ".agents/skills/refine-idea/SKILL.md"
    role: "skill_source"
references: ["stage:WF3", "skill:refine-idea", "source:schemas/skill_contracts.json#refine-idea", "term:Gate Evidence"]
html:
  render: true
  output_path: "docs/_site/workflow_handbook/stages/wf3_refine_idea.html"
  preview_index_path: "docs/_views/workflow_handbook_reference_index.json"
---

# WF3 Refine Idea

## Purpose

Turn the selected idea into a tighter research question and execution target.

## How To Run

`$refine-idea` with the selected direction and unresolved assumptions.

## Completion Effect

`docs/Refined_Idea.md` defines scope, hypothesis, and known unknowns.

## Contract Detail

Codex wrapper for WF3 idea refinement. Use after WF1 survey and WF2 idea debate to turn the selected direction into a feasible research idea, task framing, success criteria, baseline requirements, and protocol assumptions without designing the architecture.

## Inputs

- `$refine-idea`
- `/refine-idea`
- `refine-idea`
- `refine idea`
- `WF3`

## Outputs

- `current_doc: docs/Refined_Idea.md`
- `current_doc: docs/35_protocol/`
- `canonical_state: PROJECT_STATE.json`
- `generated_view: docs/_views/`
- `generated_view: docs/_site/`

## Required Reads

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

## Gates

- `compile_protocol_or_NOT_RUN`
- `check_protocol_drift_or_NOT_RUN`
- `workflow_state_gate_or_NOT_RUN`
- `gate_ledger`
- `docs_site_render_or_NOT_RUN`
- `refined_idea_write`
- `protocol_assumption_write`
- `canonical_state_edit`
- `docs_site_render`

## Exit Condition

The stage has produced its declared outputs or explicit `NOT_RUN` results, and the operator has any required decision or approval context.

## Related Skills

- [[skill:refine-idea]]

## Related References

- [[stage:WF3]]
- [[skill:refine-idea]]
- [[source:schemas/skill_contracts.json#refine-idea]]
- [[term:Gate Evidence]]
