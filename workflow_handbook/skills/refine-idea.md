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
summary: "Codex wrapper for WF3 idea refinement. Use after WF1 survey and WF2 idea debate to turn the selected direction into a feasible research idea, task framing, success criteria, baseline requirements, and protocol assumptions without designing the architecture."
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

Codex wrapper for WF3 idea refinement. Use after WF1 survey and WF2 idea debate to turn the selected direction into a feasible research idea, task framing, success criteria, baseline requirements, and protocol assumptions without designing the architecture.

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
- `docs/_views/`
- `docs/_site/`

## Final Outputs

- `current_doc: docs/Refined_Idea.md`
- `current_doc: docs/35_protocol/`

## Tool-Owned Outputs

- `generated_view: docs/_views/`
- `generated_view: docs/_site/`

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
- `docs_site_render_or_NOT_RUN`
- `refined_idea_write`
- `protocol_assumption_write`
- `canonical_state_edit`
- `docs_site_render`

## Cannot Do

- `protocol_as_approved_contract`
- `architecture_decision_in_build_plan`

## Exit Condition

Recommended reads have been considered; durable writes stay aligned with declared path ownership; Gate ledger reports command, result, reason, and artifacts when gate conditions are touched.

## Related References

- [[skill:refine-idea]]
- [[source:schemas/skill_contracts.json#refine-idea]]
- [[term:Gate Evidence]]
