# Documentation Evidence Rule

## Purpose

Prevent hallucinated project documentation by requiring every generated report or summary to be rebuilt from files read in the current turn.

## Scope

Apply this rule whenever a skill writes or refreshes natural-language artifacts, including:

- `docs/**/*.md`
- `CLAUDE.md`
- `MEMORY.md`
- reports generated from `PROJECT_STATE.json`, `iteration_log.json`, `project_map.json`, logs, code, configs, or experiment outputs

Pair this rule with `documentation-style.md`: this file controls evidence and hallucination prevention; the style rule controls readability, brevity, ASCII flow diagrams, and `docs/legacy/` archiving.

## Required Behavior

Before writing documentation:

1. Re-read the relevant source artifacts from disk in the current turn.
2. Prefer primary evidence in this order:
   - source code and configs
   - `PROJECT_STATE.json`, `iteration_log.json`, `project_map.json`
   - existing docs and reports
   - command output, logs, metrics files, checkpoints, or trace files
3. Do not rely on memory, prior conversation summaries, or inferred project facts as evidence.
4. If evidence is missing or contradictory, write it under `Open Questions` instead of presenting it as fact.

## Required Report Sections

Every generated report should include these sections immediately after `context_summary` when the template allows:

```markdown
## Evidence Sources

| Source | Why It Was Read | Key Facts Used |
|--------|-----------------|----------------|
| `{path_or_command}` | ... | ... |

## Verified Facts

- ...

## Inferences

- ...

## Open Questions

- ...
```

If a legacy template has a fixed structure, preserve the legacy structure and add an `Evidence Sources` section near the top.

## Forbidden Behavior

- Do not write "known" architecture, metric, environment, dataset, or experiment facts unless they were verified from disk or command output in the current turn.
- Do not convert a reviewer response or previous assistant summary into a project fact unless the underlying file, code, log, or metric artifact is also read.
- Do not hide uncertainty. Mark unverifiable or stale facts explicitly.
