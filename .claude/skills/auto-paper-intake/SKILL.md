# Auto Paper Intake

<instructions>
1. Collect `paper_id`, target venue, draft path, TeX roots, bib paths,
   figures, figure/table requirement status, materials, references, artifact
   directory, scope, compile command, human-gate policy, optional
   `experiment_evidence_index`, citation policy, and forbidden directions.
2. If the artifact directory is empty or missing, initialize it with
   `.agents/skills/auto-paper/scripts/init_artifacts.py --paper-id <paper_id> --artifact-dir <artifact_dir> --workflow <workflow>`.
3. Use file discovery and deterministic inventory scripts when available. Index
   experiment evidence only through
   `docs/30_evidence/Experiment_Evidence_Index.*`; do not include
   `iteration_log.json` in `source_index.md` as a normal data source. If it is
   read for planning, mark it as a weak signal and cross-check with run
   artifacts or iteration reports.
   For PDF and Markdown materials, run or emulate
   `.agents/skills/auto-paper/scripts/figure_requirement_scan.py` and write
   `figure_requirement_scan.md` with source locations for figure/table cues.
   Do not leave figure needs buried only in extracted PDF text.
4. Write `config.yaml`, `source_index.md`, `tex_inventory.json`,
   `intake_report.md`, `figure_requirement_scan.md` when source materials were
   scanned for visual needs, and `experiment_source_map.md` when experiment
   evidence is present under `auto_paper_output/<paper_id>/`.
5. Treat future-phase template files as scaffolds until their owning phase runs.
6. Do not write manuscript prose, `.auto_paper/`, `.auto_iterate/`, or
   `iteration_log.json`.
7. Report a Gate ledger entry with commands run, artifacts written, any
   `USER_GATE` or `NOT_RUN` reason, and the next owner before handoff.
</instructions>
