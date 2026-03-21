---
name: deep-check
description: Codex wrapper for WF3 deep-check. Use when the user wants a skeptical Go/No-Go review of the technical spec before heavy implementation starts.
---

# Deep Check

## References

Read these first:
- `../../../.agents/references/workflow-guide.md`
- `../../../.agents/references/language-policy.md`
- `./references/sanity-check.md`
- `../../../PROJECT_STATE.json`

## When To Use

Use this skill for WF3 when the user wants a skeptical gate review before data engineering or coding.

## Required Work

1. Read `docs/Technical_Spec.md` and extract assumptions, chosen path, and target outcomes.
2. Use web research to look for negative evidence, limitations, and failure reports.
3. Build the canonical risk matrix with probability, impact, and mitigation.
4. Estimate upper, expected, and lower performance bounds.
5. Write `docs/Sanity_Check_Log.md` using the canonical template and one of:
   - `GO`
   - `CONDITIONAL GO`
   - `NO-GO`

## Output Rules

- Keep the `context_summary`.
- Include failure-case search results, theoretical analysis, performance estimation, risk matrix, and recommendation.
- Treat template wording as structure-only; localize headings and narrative text according to `../../../.agents/references/language-policy.md` unless a field is explicitly English-only.

## Codex Adaptation

- Treat natural-language requests as the canonical `$deep-check` invocation.
- Preserve the critical-gate semantics from the canonical workflow.
- Ask the user directly only if the technical spec path or design target is unclear.

## Execution Rule

Follow the local review logic, template, and language policy rather than collapsing this stage into a generic prose review.
