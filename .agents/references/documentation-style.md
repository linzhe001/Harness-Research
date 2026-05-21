# Documentation Style and Storage Rule

## Purpose

Keep project documentation concise, readable, current, and useful for human handoff.

## Scope

Apply this rule whenever a skill writes or refreshes natural-language artifacts, including:

- `docs/**/*.md`
- `CLAUDE.md`
- `AGENTS.md`
- `MEMORY.md`
- submission README files and report-style summaries

Use this together with `documentation-evidence-rule.md`: evidence rules decide what may be claimed; this file decides how to present and store it.

## Human Readability

- Write for a human operator who needs the current state quickly.
- Put the conclusion, decision, or current status before supporting detail.
- Keep sections short. Prefer bullets for facts and short paragraphs for rationale.
- Avoid template padding. If a section has no useful evidence, write `N/A` or move the uncertainty to `Open Questions`.
- Do not dump raw logs, long metric tables, or repeated background into docs. Link to paths instead.
- Keep jargon only when it is the project's actual technical vocabulary.
- Prefer one clear table over several overlapping tables.
- Record durable lessons and decisions; avoid restating every intermediate thought.

## ASCII Flow Diagrams

When describing a workflow, data path, state transition, or control loop, prefer a compact ASCII diagram before prose.

Use plain ASCII characters so the diagram renders well in terminals and Markdown previews:

```text
raw data -> preprocess -> train -> eval -> report
                         |
                         v
                    checkpoint
```

Guidelines:

- Keep diagrams small enough to scan.
- Use diagrams to show ordering, ownership, or branching.
- Follow the diagram with only the necessary explanation.
- Do not use decorative box art when a simple arrow diagram is enough.

## Information Budget

Each document should contain only effective information that helps a later human understand or operate the current project:

- current decision
- current architecture or workflow
- active paths, commands, metrics, and constraints
- verified facts and evidence paths
- open questions and next actions
- durable lessons worth remembering

Move historical context, superseded drafts, and old versions out of the root `docs/` view.

## `docs/90_legacy/` Storage Rule

`docs/` is the current documentation surface. Keep root-level `docs/*.md` limited to necessary Markdown files that best reflect the current codebase state.

Before refreshing an existing current doc:

1. Read the existing file.
2. Create `docs/90_legacy/<YYYY-MM-DD>/` if needed.
3. Move the old file into `docs/90_legacy/<YYYY-MM-DD>/<original-stem>__<HHMMSS>.md`.
4. Write the refreshed current file at the original path.

Rules:

- Do not archive files already under `docs/90_legacy/`.
- Preserve subdirectory context when useful, for example archive `docs/40_iterations/iter3.md` as `docs/90_legacy/<YYYY-MM-DD>/40_iterations__iter3__<HHMMSS>.md`.
- Do not keep duplicate, stale, or superseded Markdown files in root `docs/`.
- Keep current index-style files concise; link to legacy files instead of copying old content back into current docs.
- `docs/90_legacy/` is historical audit material, not canonical current state.
- If an older project already has `docs/legacy/**`, run
  `python tooling/evidence/migrate_legacy_docs.py --workspace-root .`
  first, review the dry-run plan, then rerun with `--apply`.
