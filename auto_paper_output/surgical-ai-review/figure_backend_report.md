# Figure Backend Report

- Figure generation backend: built-in imagegen previews attempted, then deterministic SVG drafts written for durable project assets.
- Durable output format: SVG, 1600x900 viewBox, editable text and shapes.
- Reason for SVG fallback: local built-in imagegen output files were not discoverable under `$CODEX_HOME`; diagrams require reliable readable text.
- Empirical data gap: Figure 2 Panels A/C/D require dataset metadata extraction; Figure 1 numeric placement requires cost/value data.
- Safe fallback used in manuscript: conceptual schematic placeholders and explicit `USER_GATE` notes.

## Draft Assets

| figure_id | path | validation |
| --- | --- | --- |
| fig_001 | `auto_paper_output/surgical-ai-review/figures/fig_001_value_cost_landscape.svg` | XML parse OK; conceptual landscape |
| fig_002 | `auto_paper_output/surgical-ai-review/figures/fig_002_dataset_concentration.svg` | XML parse OK; USER_GATE badges on empirical panels |
| fig_003 | `auto_paper_output/surgical-ai-review/figures/fig_003_layered_spatial_world_models.svg` | XML parse OK; layered research landscape |
| fig_004 | `auto_paper_output/surgical-ai-review/figures/fig_004_three_lane_roadmap.svg` | XML parse OK; roadmap with evidence-strength fading |

## Recommended Next Data Inputs

| input_id | needed_for | fields |
| --- | --- | --- |
| dataset_metadata_csv | Figure 2 Panels A/C/D | dataset_name, year, venue, country, institution_count, institution_type, procedure, videos, frames, patients, modality, robotic_or_laparoscopic, annotation_type, public_access, outcome_linked, external_validation |
| value_cost_evidence_table | Figure 1 empirical placement | system_category, procedure, comparator, incremental_cost, total_cost, clinical_endpoint, outcome_direction, evidence_type, source_key |
