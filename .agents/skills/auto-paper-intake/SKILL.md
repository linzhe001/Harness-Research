---
name: auto-paper-intake
description: "Internal Harness instruction source for auto-paper-intake. Route through visible Harness aliases or hook contracts instead of invoking directly."
---

# Auto Paper Intake

## Purpose

Create the run configuration and source inventory. Do not write manuscript
prose or make claim decisions in intake.

## Inputs

Collect or infer:

- `paper_id`
- `target_venue`
- `target_name`
- `draft_path`
- `tex_roots`
- `bib_paths`
- `figure_paths`
- `figure_requirement_status`
- `materials_dir`
- `reference_paths`
- `experiment_evidence_index` when
  `docs/30_evidence/Experiment_Evidence_Index.{json,md}` exists
- `artifact_dir`
- `objective`
- `scope`
- `output_language`
- `compile_command`
- `human_gate_policy`
- `forbidden_directions`

If a field cannot be inferred from files or user brief, write `unknown` and add
a `USER_GATE` question to `intake_report.md`.

For `blog`, `review`, `survey`, or `tutorial` targets, set citation policy
explicitly. Use `citation_target_count: unknown` or a positive target unless
the operator explicitly asks for an uncited opinion memo.

## Discovery

If the artifact directory is empty or missing, initialize the run scaffold
first:

- `.agents/skills/auto-paper/scripts/init_artifacts.py --paper-id <paper_id> --artifact-dir <artifact_dir> --workflow <workflow>`

Templates are placeholders. Replace `unknown` values during intake and keep
future-phase templates as scaffolds until their owning phase runs.

Use `rg --files` to find `.tex`, `.bib`, figures, notes, PDFs, Markdown files,
CSV/JSON result files, and local reports. Index experiment evidence only through
`docs/30_evidence/Experiment_Evidence_Index.*`; do not include
`iteration_log.json` in `source_index.md` as a normal data source. If it is read
for planning, mark it as a weak signal and cross-check with run artifacts or
iteration reports. Prefer deterministic scripts when
available:

- `.agents/skills/auto-paper/scripts/init_artifacts.py`
- `.agents/skills/auto-paper/scripts/reference_inventory.py`
- `.agents/skills/auto-paper/scripts/tex_inventory.py`
- `.agents/skills/auto-paper/scripts/figure_requirement_scan.py`
- `.agents/skills/auto-paper/scripts/latex_guard.py`

For PDF and Markdown materials, run or emulate `figure_requirement_scan.py` to
search for figure/table cues. Record all matches in `figure_requirement_scan.md`
with source locations. If the scan finds candidate figures or tables, set the
next owner to `$auto-paper-figure` or `layout` and do not leave the need only in
the raw PDF text.

If `compile_command` is present, run a non-mutating baseline compile or static
guard. If absent, record `compile_command: unknown`.

## Outputs

Write under `auto_paper_output/<paper_id>/`:

- `config.yaml`
- `source_index.md`
- `tex_inventory.json`
- `intake_report.md`
- `experiment_source_map.md` when an experiment evidence index is present
- `figure_requirement_scan.md` when PDFs, Markdown notes, or source materials
  were scanned for figure/table needs

Do not write `.auto_paper/` or `.auto_iterate/` manually.

## Gate Ledger

Report a Gate ledger entry with commands run, artifacts written, any
`USER_GATE` or `NOT_RUN` reason, and the next owner before handoff.
