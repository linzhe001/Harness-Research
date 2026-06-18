# Auto Paper Research

<instructions>
1. Read intake artifacts, `.claude/shared/research-supervision-patterns.md`,
   `.claude/shared/research-supervision/paper-writing-layouts.md`, and
   `.claude/shared/research-supervision/case-patterns.md` before synthesis.
2. Summarize author evidence, known claims, gaps, and missing files with
   provenance. Experiment provenance comes from
   `docs/30_evidence/Experiment_Evidence_Index.*` and its named artifact paths,
   while direct `iteration_log.json` reads are only weak signals that must be
   cross-checked against reports, configs, logs, metrics, or run artifacts.
3. Learn exemplar structure and style without creating author claims. Classify
   paper logic as technical, benchmark/evaluation, or mixed.
4. Map SOTA gaps from local bib/notes and optional user-requested search.
5. For review/blog work, extract citation candidates for named papers, methods,
   datasets, systems, and quantitative literature claims. If candidates come
   from an AI dialogue or unverified PDF notes, mark them as unverified
   candidates instead of omitting them.
6. When PDFs or Markdown notes include figure/table suggestions, extract the
   visual purpose, evidence source, required data, and uncertainty into
   `research_dossier.md` and `figure_requirement_scan.md`.
7. Write `research_dossier.md`, `exemplar_learning_dossier.md`,
   `style_profile.md`, and `sota_gap_map.md`.
8. Report a Gate ledger entry with commands run, artifacts written, unresolved
   source gaps, any `USER_GATE` or `NOT_RUN` reason, and the next owner before
   handoff.
</instructions>
