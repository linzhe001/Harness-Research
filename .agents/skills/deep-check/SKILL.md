---
name: deep-check
description: Codex design-review gate for WF6 architecture decisions. Use when the user wants a skeptical Go/No-Go review of the technical spec before implementation planning or heavy implementation starts.
---

# Deep Check

## References

Read these first:
- `../../../.agents/references/workflow-guide.md`
- `../../../.agents/references/context-layering-policy.md`
- `../../../.agents/references/research-invariants.md`
- `../../../.agents/references/contract-gating-rule.md`
- `../../../.agents/references/language-policy.md`
- `../../../.agents/references/documentation-evidence-rule.md`
- `../../../.agents/references/documentation-style.md`
- `../../../.agents/references/reviewer-independence.md`
- `../../../.agents/references/review-tracing.md`
- `./references/sanity-check.md`
- `../../../PROJECT_STATE.json`
- `../../../docs/Refined_Idea.md` if it exists
- `../../../docs/Dataset_Stats.md` if it exists
- `../../../docs/Baseline_Report.md` if it exists
- `../../../docs/10_contract/Project_Contract.md` if it exists
- `../../../docs/10_contract/Evaluation_Contract.md` if it exists
- `../../../docs/10_contract/Baseline_Contract.md` if it exists
- `../../../docs/10_contract/Claim_Boundary.md` if it exists
- `../../../docs/35_protocol/Research_Protocol.md` if it exists

## When To Use

Use this skill after WF6 `$refine-arch` and before WF7 `$build-plan` when the architecture affects claim boundaries, evaluation assumptions, core interfaces, or high-cost implementation direction.

## Required Work

1. Read `docs/Technical_Spec.md` and extract assumptions, chosen path, target outcomes, contract dependencies, and evidence sources.
2. Use web research to look for negative evidence, limitations, and failure reports.
3. Build the canonical risk matrix with probability, impact, and mitigation.
4. Estimate upper, expected, and lower performance bounds.
5. When dynamic context is enabled, check whether the architecture conflicts with Project, Evaluation, Baseline, or Claim contracts. If it does, record the conflict and route to protocol drift or human review instead of silently changing contracts.
6. Write `docs/Sanity_Check_Log.md` using the canonical template and one of:
   - `GO`
   - `CONDITIONAL GO`
   - `NO-GO`

## Context Budget

- Review 1 design target per invocation; split unrelated architecture choices.
- Run at most 4 negative-search queries and 1 reviewer round unless the
  operator explicitly expands scope.

## Durable Docs Render

After stable Markdown outputs for this skill are finalized, invoke `$docs-site` or report `docs_site_render_or_NOT_RUN`. Do not render after temporary draft edits; Markdown remains the source of truth.

## Output Rules

- Keep the `context_summary`.
- Include evidence sources, failure-case search results, theoretical analysis, performance estimation, risk matrix, reviewer trace status, and recommendation.
- Do not create or approve contracts by default. Contract drafting and approval are governed by the WF5 contract gate and explicit human review.
- Report a Gate ledger for reviewer passes, protocol drift checks, contract-conflict handling, and the sanity-check log write. Mark skipped reviewer or gate steps `NOT_RUN` with the reason.
- Treat template wording as structure-only; localize headings and narrative text according to `../../../.agents/references/language-policy.md` unless a field is explicitly English-only.

## Codex Adaptation

- Treat natural-language requests as the canonical `$deep-check` invocation.
- Preserve the critical-gate semantics from the canonical workflow.
- Ask the user directly only if the technical spec path or design target is unclear.

## Execution Rule

Follow the local review logic, template, and language policy rather than collapsing this stage into a generic prose review.
