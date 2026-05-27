---
name: auto-paper-intake
description: Prepare an auto-paper run for a LaTeX manuscript. Use when the user provides a paper directory, draft path, materials, references, target venue, or asks to start auto-paper intake before research, argument, citation, layout, patch, or harden phases.
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
- `materials_dir`
- `reference_paths`
- `artifact_dir`
- `objective`
- `scope`
- `output_language`
- `compile_command`
- `human_gate_policy`
- `forbidden_directions`

If a field cannot be inferred from files or user brief, write `unknown` and add
a `USER_GATE` question to `intake_report.md`.

## Discovery

If the artifact directory is empty or missing, initialize the run scaffold
first:

- `.agents/skills/auto-paper/scripts/init_artifacts.py --paper-id <paper_id> --artifact-dir <artifact_dir> --workflow <workflow>`

Templates are placeholders. Replace `unknown` values during intake and keep
future-phase templates as scaffolds until their owning phase runs.

Use `rg --files` to find `.tex`, `.bib`, figures, notes, PDFs, CSV/JSON result
files, and local reports. Prefer deterministic scripts when available:

- `.agents/skills/auto-paper/scripts/init_artifacts.py`
- `.agents/skills/auto-paper/scripts/reference_inventory.py`
- `.agents/skills/auto-paper/scripts/tex_inventory.py`
- `.agents/skills/auto-paper/scripts/latex_guard.py`

If `compile_command` is present, run a non-mutating baseline compile or static
guard. If absent, record `compile_command: unknown`.

## Outputs

Write under `auto_paper_output/<paper_id>/`:

- `config.yaml`
- `source_index.md`
- `tex_inventory.json`
- `intake_report.md`

Do not write `.auto_paper/` or `.auto_iterate/` manually.
