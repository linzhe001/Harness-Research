# Artifact Contract

## Rule

Any durable writing decision must be written to an artifact. Later phases read
artifacts, not chat memory.

## Required Artifacts

| phase | required artifacts |
| --- | --- |
| intake | `config.yaml`, `source_index.md`, `tex_inventory.json`, `intake_report.md` |
| research | `research_dossier.md`, `exemplar_learning_dossier.md`, `style_profile.md`, `sota_gap_map.md` |
| argument | `confirmed_motivation.md`, `claim_register.md`, `claims_to_avoid.md`, `motivation_surface_map.md` |
| citation | `citation_support_bank.md`, `claim_citation_map.md` |
| layout | `original_logic_map.md`, `section_blueprints.md`, `writing_rationale_matrix.md`, `citation_plan.md`, `latex_patch_plan.md` |
| patch | `patch_ledger.md`, guard or compile reports |
| harden | `audit_report.md`, `compile_report.md`, `citation_audit_report.md`, `revision_audit_report.md`, `logic_transfer_audit.md`, `final_gate_ledger.md` |

## Identifiers

- `source_id`: `src_tex_001`, `src_bib_001`, `src_fig_001`,
  `src_note_001`, `src_pdf_001`
- `claim_id`: `claim_001`
- `citation_id`: `cite_001`
- `unit_id`: `unit_001`
- `finding_id`: `finding_001`

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
