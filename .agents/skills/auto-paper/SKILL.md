---
name: auto-paper
description: "Internal Harness instruction source for auto-paper. Route through visible Harness aliases or hook contracts instead of invoking directly."
---

# Auto Paper

Use this Skill as the auto-paper orchestrator, not a direct polishing tool. It
routes phases, checks artifacts, and keeps paper-writing state separate from
auto-iterate experiment state.

## Boundaries

- Author evidence outranks exemplars: local results, figures, tables, notes,
  approved claim boundaries, and operator facts.
- Do not invent experiments, results, mechanisms, statistics, novelty,
  clinical meaning, data availability, citations, or source support.
- External papers are examples for structure, style, terminology, and
  positioning, not author claims.
- Patch LaTeX only from written artifacts.
- Do not write `iteration_log.json` or `.auto_iterate/**`; auto-paper state
  uses `auto_paper_log.json`, `.auto_paper/`, and
  `auto_paper_output/<paper_id>/`.

## Required Config

Before the loop, establish `paper_id`, workflow, venue/target, draft path, TeX
roots, bibliography paths, figures, materials, references, artifact dir,
output language, citation target count, compile command, human gate policy, and
forbidden directions in `auto_paper_output/<paper_id>/config.yaml` or intake
artifact. If missing, route to `$auto-paper-intake` or return `USER_GATE`.

## Phase Route

Run in order unless an audit routes back:

1. `$auto-paper-research`
2. `$auto-paper-argument`
3. `$auto-paper-citation`
4. `$auto-paper-layout`
5. `$auto-paper-patch`
6. `$auto-paper-harden`

Optional branches: `$auto-paper-response`, `$auto-paper-data`,
`$auto-paper-figure`.

## Artifacts

Durable decisions live under `auto_paper_output/<paper_id>/`.

- Intake: `config.yaml`, `source_index.md`, `tex_inventory.json`,
  `intake_report.md`
- Research: `research_dossier.md`, `exemplar_learning_dossier.md`,
  `style_profile.md`, `sota_gap_map.md`
- Argument: `confirmed_motivation.md`, `claim_register.md`,
  `claims_to_avoid.md`, `motivation_surface_map.md`
- Citation: `citation_support_bank.md`, `claim_citation_map.md`
- Layout: `original_logic_map.md`, `section_blueprints.md`,
  `writing_rationale_matrix.md`, `citation_plan.md`, `latex_patch_plan.md`
- Patch/Harden: diffs, `patch_ledger.md`, guard/compile reports,
  `audit_report.md`, `citation_audit_report.md`, `logic_transfer_audit.md`,
  `final_gate_ledger.md`

Use `references/artifact-contract.md` for identifiers and stale-artifact
policy.

## Gate And Routing

Do not patch around missing upstream artifacts. Every audit finding names
`root_cause`, `owning_phase`, `required_artifact`, `fix_action`, and
`downstream_risk`.

Decisions: `NEXT_UNIT`, `REWORK_RESEARCH`, `REWORK_ARGUMENT`,
`REWORK_CITATION`, `REWORK_LAYOUT`, `REWORK_PATCH`, `USER_GATE`, `COMPLETE`,
`ABORT`.

## References

Load only active-phase references from `references/`: loop, auto-iterate
boundary, artifact contract, writing rationale, motivation thread, citation
support, and LaTeX source control as needed.

## Output

Final responses report artifact manifest, modified files, guard/compile
results, remaining reviewer risks, and next human gates.
