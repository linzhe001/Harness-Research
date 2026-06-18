---
name: write
description: "Visible Harness write entry. Use for manuscript writing, citation-supported paper work, final documentation, README hardening, and GitHub Pages preparation."
argument-hint: "[paper or release goal]"
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
---

# Write

Use `/write` as the human-facing alias for paper and release-documentation
work. This is not a separate Skill Contract.

Read and follow:
- `../../../.claude/skills/auto-paper/SKILL.md` for manuscript work
- `../../../.claude/shared/research-supervision/README.md` for internalized paper, figure, benchmark, case-pattern, and review assets
- `../../../.claude/skills/docs-site/SKILL.md` only after durable Markdown docs are finalized
- `../../../CLAUDE.md`
- `../../../AGENTS.md`

For manuscript work, `/write` may read PDFs, Markdown notes, LaTeX sources,
bibliographies, figures, local reports, and `iteration_log.json` when needed.
Treat `iteration_log.json` as a weak planning signal, not Conclusion Evidence.
Experiment evidence should flow through
`docs/30_evidence/Experiment_Evidence_Index.*`, whose entries cross-check
iteration-log signals against reports and run artifacts.
Research Wiki context and run requests should flow through
`docs/context/experiments.md`; legacy `docs/45_discoveries/Research_Wiki.md` is
a pre-migration fallback.

Blogs and review articles are still citation-supported writing unless the
operator explicitly asks for an uncited opinion memo. Do not set
`citation_target_count: 0` for a blog or review by default. If the only source
is an AI dialogue, PDF discussion, or unverified literature note, extract
candidate references and mark them as unverified instead of silently omitting
citations.

For PDFs and Markdown notes, `/write` must also look for figure/table planning
cues such as `Figure`, `Table`, `diagram`, `chart`, `plot`, `图`, `图表`,
`表格`, `架构图`, `路线图`, `热力图`, and `雷达图`. When such cues appear,
write `figure_requirement_scan.md` and either route through
`/auto-paper-figure` or record a concrete `USER_GATE` / `NOT_RUN` reason.

When writing finds missing experiment evidence, write
`auto_paper_output/<paper_id>/run_request_register.{json,md}` and return
`RUN_REQUEST` so `/run` can plan the next WF10 iteration.

Do not upgrade claims beyond approved Claim Boundaries or available Conclusion
Evidence.
