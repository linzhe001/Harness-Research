# Dependency Update Rule

## Type

- `advisory`
- `skill_scoped` for `$env-setup` and `$init-project`

## Purpose

Keep environment documentation synchronized with the dependency specification files that define the actual runtime environment.

## Scope

This rule applies when any of these files changes:

- `requirements*.txt`
- `environment*.yml`
- `pyproject.toml`
- `setup.py`
- `setup.cfg`

## Trigger

Apply this rule after dependency-related edits or when the user asks to refresh environment documentation.

This is a workflow reminder rule, not an automatic repository hook.

## Required Actions

1. Re-detect the active environment details.
2. Refresh the `## Environment` section of `CLAUDE.md`.
3. Preserve `### Dataset Paths` inside that section unless dataset addresses are being intentionally refreshed.
4. Keep the rest of `CLAUDE.md` unchanged.
5. If the project-level always-on guidance mentions environment activation or key dependency assumptions, update that guidance too.
6. Prefer `$env-setup refresh` as the canonical workflow action.

## Forbidden Actions

- Do not rewrite unrelated sections of `CLAUDE.md` during an environment refresh.
- Do not leave dependency-file changes undocumented when the recorded environment description has become stale.

## Verification

This rule is satisfied when:

- `CLAUDE.md` reflects the current environment accurately
- the `## Environment` section matches the active conda or Python environment, key dependencies, and tracking tools
- unrelated `CLAUDE.md` sections remain intact

## Escalation

- Dependency changes do not always need to block code work immediately.
- But if environment drift could confuse future runs or collaborators, the refresh should be treated as required follow-up before considering the task cleanly finished.
