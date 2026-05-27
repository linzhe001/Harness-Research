---
name: auto-paper-intake
description: Prepare an auto-paper run for a LaTeX manuscript. Use when the operator provides a paper directory, draft path, materials, references, target venue, or wants intake before the writing loop.
argument-hint: "[paper path or goal]"
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
---

# Auto Paper Intake

<instructions>
1. Collect `paper_id`, target venue, draft path, TeX roots, bib paths,
   figures, materials, references, artifact directory, scope, compile command,
   human-gate policy, and forbidden directions.
2. If the artifact directory is empty or missing, initialize it with
   `.agents/skills/auto-paper/scripts/init_artifacts.py --paper-id <paper_id> --artifact-dir <artifact_dir> --workflow <workflow>`.
3. Use file discovery and deterministic inventory scripts when available.
4. Write `config.yaml`, `source_index.md`, `tex_inventory.json`, and
   `intake_report.md` under `auto_paper_output/<paper_id>/`.
5. Treat future-phase template files as scaffolds until their owning phase runs.
6. Do not write manuscript prose, `.auto_paper/`, `.auto_iterate/`, or
   `iteration_log.json`.
</instructions>
