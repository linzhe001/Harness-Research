---
name: refine-arch
description: Codex wrapper for WF6 architecture design. Use after WF4 data preparation and WF5 baseline reproduction to convert the refined idea, dataset facts, baseline evidence, and evaluation contract into a technical spec and MVP architecture.
---

# Refine Arch

## References

Read these first:
- `../../../.agents/references/workflow-guide.md`
- `../../../.agents/references/context-layering-policy.md`
- `../../../.agents/references/research-invariants.md`
- `../../../.agents/references/code-style.md`
- `../../../.agents/references/ubiquitous-language.md`
- `../../../.agents/references/language-policy.md`
- `../../../.agents/references/documentation-evidence-rule.md`
- `../../../.agents/references/documentation-style.md`
- `./references/technical-spec.md`
- `../../../PROJECT_STATE.json`
- `../../../docs/Refined_Idea.md` if it exists
- `../../../docs/Dataset_Stats.md` if it exists
- `../../../docs/Baseline_Report.md` if it exists
- `../../../docs/10_contract/Evaluation_Contract.md` if it exists
- `../../../docs/10_contract/Baseline_Contract.md` if it exists
- `../../../docs/10_contract/Claim_Boundary.md` if it exists
- `../../../docs/30_evidence/Evidence_Index.md` if it exists
- `../../../docs/35_protocol/Research_Protocol.md` if it exists
- `../../../docs/20_facts/Project_Glossary.md` if it exists

## When To Use

Use this skill for WF6 after WF4 data preparation and WF5 baseline reproduction.

Do not use this skill as WF2. Early idea selection belongs to `$idea-debate` and `$refine-idea`.

## Required Work

1. Read WF1-WF5 artifacts: feasibility report, idea debate, refined idea, dataset stats, baseline report, and evaluation protocol or contracts.
2. Inspect the existing codebase structure only after the target task, data constraints, and baseline behavior are clear.
3. Identify extension points, config patterns, registry or inheritance patterns, and integration boundaries.
4. Design the MVP architecture that is justified by literature evidence, dataset facts, baseline gaps, and evaluation constraints.
5. Define the first vertical slice that proves one end-to-end path, including
   entry point, module/domain behavior, artifact/output, acceptance check, and
   out-of-scope work.
6. Define module boundaries before file plans: owns, does not own, public API,
   dependencies, forbidden dependencies, and tests. Prefer deep modules with
   small public APIs.
7. Generate or refresh the initial `docs/20_facts/Project_Glossary.md` seed
   when the project uses dynamic context or when stable codebase vocabulary is
   needed. Use only terms grounded in WF1-WF6 artifacts and architecture
   decisions; mark uncertain names as proposed terms.
8. For each major decision, provide the canonical A/B/C alternatives with pros, cons, evidence, and rollback strategy.
9. Estimate resource requirements for MVP, full training, and ablations.
10. When dynamic context is enabled, run protocol drift or request contract review if the proposed architecture changes evaluation assumptions, claim boundaries, or project scope.
11. Write `docs/Technical_Spec.md` using the canonical template and update `PROJECT_STATE.json` when appropriate.

## Output Rules

- Use `./references/technical-spec.md`.
- Include the required sections: architecture overview, module modification plan, MVP definition, alternative plans, integration points, resource estimation, and risk mitigation.
- Include `application_codebase_language_seed` to show the glossary terms WF6
  generated or proposed for WF7.
- Include evidence sources and separate verified facts from inferences.
- Keep protocol content project-local and evidence-backed; do not introduce pre-baked research-track rules.
- Do not write the implementation roadmap or `project_map.json`; those belong to WF7 `$build-plan`.
- Report a Gate ledger when the technical spec, protocol drafts, contract conflict notes, or canonical state are written. If protocol drift or workflow-state checks are not run, mark them `NOT_RUN` with the reason.
- Treat template wording as structure-only; localize headings and narrative text according to `../../../.agents/references/language-policy.md` unless a field is explicitly English-only.

## Codex Adaptation

- Treat natural-language requests as the canonical `$refine-arch` flow.
- Ask the user directly only if baseline evidence, evaluation constraints, or target scope are missing.
- Preserve the original output path and state-update behavior.

## Execution Rule

Use the local instructions, template, and language policy as the source of truth for the spec sections.
