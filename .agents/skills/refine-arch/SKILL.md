---
name: refine-arch
description: Codex wrapper for WF2 architecture design. Use when the user wants to convert an approved idea into a technical spec, MVP plan, and alternative architecture paths.
---

# Refine Arch

## References

Read these first:
- `../../../.agents/references/workflow-guide.md`
- `../../../.agents/references/code-style.md`
- `./references/technical-spec.md`
- `../../../PROJECT_STATE.json`

## When To Use

Use this skill for WF2 when the user wants to translate an approved idea into a technical spec.

## Required Work

1. Read the feasibility report and inspect the existing codebase structure.
2. Identify extension points, config patterns, registry or inheritance patterns, and integration boundaries.
3. Design the MVP.
4. For each major decision, provide the canonical A/B/C alternatives with pros, cons, and rollback strategy.
5. Estimate resource requirements for MVP, full training, and ablations.
6. Write `docs/Technical_Spec.md` using the canonical template and update `PROJECT_STATE.json` when appropriate.

## Output Rules

- Use `./references/technical-spec.md`.
- Include the required sections: architecture overview, module modification plan, MVP definition, alternative plans, integration points, resource estimation, and risk mitigation.

## Codex Adaptation

- Treat natural-language requests as the canonical `$refine-arch` flow.
- Ask the user directly only if baseline codebase or target constraints are missing.
- Preserve the original output path and state-update behavior.

## Execution Rule

Use the local instructions and template as the source of truth for the spec sections.
