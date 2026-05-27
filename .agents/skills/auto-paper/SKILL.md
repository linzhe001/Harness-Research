---
name: auto-paper
description: Orchestrate artifact-first academic paper writing for LaTeX manuscripts. Use when Codex is asked to run an auto-paper loop, rewrite or restructure a paper section, produce citation-supported manuscript edits, harden a submission, audit reviewer risk, or coordinate research to argument to citation to layout to patch to harden writing phases.
---

# Auto Paper

## Purpose

Use this skill as the auto-paper orchestrator, not as a direct polishing tool.
It selects the route, invokes branch skills, checks artifact completeness, and
keeps writing state separate from auto-iterate experiment state.

## Boundaries

- Put author evidence first: local results, figures, tables, notes, approved
  claim boundaries, and operator-provided facts outrank external exemplars.
- Do not invent experiments, results, mechanisms, statistics, novelty,
  clinical meaning, data availability, citations, or source support.
- Treat external papers as structure, style, terminology, and positioning
  examples; do not promote exemplar content into author claims.
- Patch LaTeX only from written artifacts, never from chat memory alone.
- Do not write `iteration_log.json` or `.auto_iterate/`; auto-paper state uses
  `auto_paper_log.json`, `.auto_paper/`, and `auto_paper_output/<paper_id>/`.

## Required Configuration

Before entering the loop, establish these fields in
`auto_paper_output/<paper_id>/config.yaml` or an equivalent intake artifact:

- `paper_id`
- `workflow`
- `target_venue`
- `target_name`
- `draft_path`
- `tex_roots`
- `bib_paths`
- `figure_paths`
- `materials_dir`
- `reference_paths`
- `artifact_dir`
- `output_language`
- `citation_target_count`
- `compile_command`
- `human_gate_policy`
- `forbidden_directions`

If a required field is missing, route to `$auto-paper-intake` or return
`USER_GATE` with the smallest set of questions needed to continue.

## Route

Run phases in this order unless an audit finding routes back to an owning
phase:

1. `research` -> `$auto-paper-research`
2. `argument` -> `$auto-paper-argument`
3. `citation` -> `$auto-paper-citation`
4. `layout` -> `$auto-paper-layout`
5. `patch` -> `$auto-paper-patch`
6. `harden` -> `$auto-paper-harden`

Optional branches are only entered when requested:
`$auto-paper-response` for rebuttal or revision response work,
`$auto-paper-data` for availability/ethics/reproducibility statements, and
`$auto-paper-figure` for figure contracts or caption audits.

## Standard Artifacts

Durable decisions must be written under `auto_paper_output/<paper_id>/`.
Required artifacts by phase:

- Intake: `config.yaml`, `source_index.md`, `tex_inventory.json`,
  `intake_report.md`
- Research: `research_dossier.md`, `exemplar_learning_dossier.md`,
  `style_profile.md`, `sota_gap_map.md`
- Argument: `confirmed_motivation.md`, `claim_register.md`,
  `claims_to_avoid.md`, `motivation_surface_map.md`
- Citation: `citation_support_bank.md`, `claim_citation_map.md`
- Layout: `original_logic_map.md`, `section_blueprints.md`,
  `writing_rationale_matrix.md`, `citation_plan.md`, `latex_patch_plan.md`
- Patch: `latex_patch.diff` or `patches/<unit_id>.diff`, `patch_ledger.md`,
  guard or compile reports for the patched unit
- Harden: `audit_report.md`, `compile_report.md`,
  `citation_audit_report.md`, `revision_audit_report.md`,
  `logic_transfer_audit.md`, `final_gate_ledger.md`

Use `references/artifact-contract.md` for the required identifiers and stale
artifact policy.

## Gate And Routing

Do not patch final paper text to hide a missing upstream artifact. Every audit
finding must name `root_cause`, `owning_phase`, `required_artifact`,
`fix_action`, and `downstream_risk`.

Decision values:

- `NEXT_UNIT`
- `REWORK_RESEARCH`
- `REWORK_ARGUMENT`
- `REWORK_CITATION`
- `REWORK_LAYOUT`
- `REWORK_PATCH`
- `USER_GATE`
- `COMPLETE`
- `ABORT`

Citation support failures route to citation, motivation instability routes to
argument, paragraph-job failures route to layout, LaTeX errors route to patch,
and source coverage gaps route to research.

## References

Load only the references needed for the active phase:

- `references/auto-paper-loop.md` for phase order and decision routing
- `references/auto-iterate-boundary.md` for state ownership boundaries
- `references/artifact-contract.md` for artifact names and identifiers
- `references/writing-rationale-matrix.md` before layout or patch planning
- `references/motivation-thread.md` before argument work
- `references/citation-support-bank.md` before citation audits
- `references/latex-source-control.md` before editing `.tex` or `.bib`

## Output Contract

Final responses must report:

- artifact manifest
- modified files
- guard or compile results
- remaining reviewer risks
- next human gates

Match the operator's language for prose while keeping paths, schema keys,
workflow IDs, citation keys, labels, and commands in English.
