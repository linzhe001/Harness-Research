# Artifact Contract

## Rule

Any durable writing decision must be written to an artifact. Later phases read
artifacts, not chat memory.

## Required Artifacts

| phase | required artifacts |
| --- | --- |
| intake | `config.yaml`, `source_index.md`, `tex_inventory.json`, `intake_report.md`, optional `experiment_source_map.md`, optional `figure_requirement_scan.md` |
| research | `research_dossier.md`, `exemplar_learning_dossier.md`, `style_profile.md`, `sota_gap_map.md` |
| argument | `confirmed_motivation.md`, `claim_register.md`, `claims_to_avoid.md`, `motivation_surface_map.md` |
| citation | `citation_support_bank.md`, `claim_citation_map.md` |
| layout | `original_logic_map.md`, `section_blueprints.md`, `writing_rationale_matrix.md`, `citation_plan.md`, `latex_patch_plan.md` |
| figure | `figure_requirement_scan.md`, `figure_asset_map.md`, `figure_contract.md`, `caption_claim_map.md`, `figure_backend_report.md` |
| patch | `latex_patch.diff` or `patches/<unit_id>.diff`, `patch_ledger.md`, guard or compile reports |
| harden | `audit_report.md`, `compile_report.md`, `citation_audit_report.md`, `revision_audit_report.md`, `logic_transfer_audit.md`, `final_gate_ledger.md`, optional `run_request_register.{json,md}` |

## Initialization

Use the bundled templates to create a run scaffold before intake writes the
first concrete artifact:

```bash
.agents/skills/auto-paper/scripts/init_artifacts.py \
  --paper-id <paper_id> \
  --artifact-dir auto_paper_output/<paper_id> \
  --workflow <workflow>
```

Template files are placeholders. A phase postcondition is satisfied only after
that phase replaces placeholder values with source-backed artifact content.

Experiment evidence enters auto-paper through
`docs/30_evidence/Experiment_Evidence_Index.{json,md}`. Intake may mirror the
paper-relevant rows into `experiment_source_map.md`. Direct
`iteration_log.json` reads are allowed only as weak signals; every paper-facing
purpose or result summary must be cross-checked against reports, configs, logs,
metrics, or run artifacts.

For source materials that are PDFs or Markdown notes, intake should also scan
for figure/table cues. `figure_requirement_scan.md` records candidate visual
needs even when no asset exists yet. If a later phase accepts any candidate as
needed, the figure branch must create `figure_contract.md` and
`caption_claim_map.md` before patch/harden declares readiness.

## Identifiers

- `source_id`: `src_tex_001`, `src_bib_001`, `src_fig_001`,
  `src_note_001`, `src_pdf_001`
- `claim_id`: `claim_001`
- `citation_id`: `cite_001`
- `unit_id`: `unit_001`
- `finding_id`: `finding_001`
- `run_request_id`: `run_req_001`
- `figure_id`: `fig_001`

Artifact rows should reference identifiers instead of copying large source
snippets.

## Staleness

Mark downstream artifacts stale when any of these change:

- `draft_path`
- TeX root/input graph
- bibliography path or citation keys
- reference set
- target venue or target paper type
- operator-approved claim boundary

If stale state reaches `patch`, return `REWORK_LAYOUT` or `USER_GATE` instead
of editing LaTeX.
