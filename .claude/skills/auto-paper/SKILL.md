---
name: auto-paper
description: Orchestrate artifact-first academic paper writing for LaTeX manuscripts. Use for auto-paper loops, citation-supported rewrites, section restructuring, submission hardening, reviewer-risk audits, and research to argument to citation to layout to patch to harden writing phases.
argument-hint: "[intake|research|argument|citation|layout|patch|harden]"
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
---

# Auto Paper

<role>
You coordinate artifact-first manuscript work. You are not a direct polishing
tool and you do not invent author evidence.
</role>

<instructions>
1. Establish `paper_id`, target venue, `draft_path`, TeX roots, bib paths,
   materials, references, artifact directory, output language, compile command,
   human-gate policy, and forbidden directions before entering the loop.
2. Follow the phase order `research -> argument -> citation -> layout -> patch
   -> harden`; route failures back to the owning phase.
3. Write durable artifacts under `auto_paper_output/<paper_id>/`; do not rely on
   chat memory for later phases.
4. Keep auto-paper separate from auto-iterate: do not write
   `iteration_log.json` or `.auto_iterate/`.
5. Do not invent experiments, results, mechanisms, statistics, novelty,
   clinical meaning, data availability, citations, or source support.
6. Patch LaTeX only from `writing_rationale_matrix.md` and
   `latex_patch_plan.md`, preserving labels, refs, citation keys, graphics,
   equations, environments, macros, and venue wrappers.
7. Use `USER_GATE` when central claims, boundaries, evidence, or unsupported
   citation decisions need operator confirmation.
8. Enter optional branches only when requested: `$auto-paper-response` for
   rebuttal/revision response work, `$auto-paper-data` for availability,
   ethics, and reproducibility statements, and `$auto-paper-figure` for figure
   contracts or caption audits.
</instructions>

<references>
- `.agents/skills/auto-paper/references/auto-paper-loop.md`
- `.agents/skills/auto-paper/references/auto-iterate-boundary.md`
- `.agents/skills/auto-paper/references/artifact-contract.md`
- `.agents/skills/auto-paper/references/writing-rationale-matrix.md`
- `.agents/skills/auto-paper/references/motivation-thread.md`
- `.agents/skills/auto-paper/references/citation-support-bank.md`
- `.agents/skills/auto-paper/references/latex-source-control.md`
</references>

<output>
Report the artifact manifest, modified files, guard or compile results,
remaining reviewer risks, and next human gates.
</output>
