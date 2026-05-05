---
name: refine-idea
description: Codex wrapper for WF3 idea refinement. Use after WF1 survey and WF2 idea debate to turn the selected direction into a feasible research idea, task framing, success criteria, baseline requirements, and protocol assumptions without designing the architecture.
---

# Refine Idea

## References

Read these first:
- `../../../.agents/references/workflow-guide.md`
- `../../../.agents/references/context-layering-policy.md`
- `../../../.agents/references/research-invariants.md`
- `../../../.agents/references/language-policy.md`
- `../../../.agents/references/documentation-evidence-rule.md`
- `../../../.agents/references/documentation-style.md`
- `./references/refined-idea.md`
- `../../../PROJECT_STATE.json` if it exists
- `../../../OPERATOR_CONTEXT.md` if it exists
- `../../../docs/Feasibility_Report.md` if it exists
- `../../../docs/Idea_Debate.md` if it exists
- `../../../docs/30_evidence/Evidence_Index.md` if it exists
- `../../../docs/35_protocol/Research_Protocol.md` if it exists

## When To Use

Use this skill for WF3 after `$survey-idea` and `$idea-debate`.

The goal is to refine the research idea, not to design the architecture. Architecture decisions belong to WF6 after WF4 data preparation and WF5 baseline reproduction.

## Required Work

1. Re-read the WF1 feasibility report, WF2 idea debate, evidence tables, and any explicit operator constraints.
2. Identify the selected idea or variant and record why alternatives were rejected or deferred.
3. Define the project-local research framing:
   - problem statement
   - target task and data assumptions
   - candidate baselines to reproduce
   - target metrics and success criteria to verify in WF5
   - minimum viable experiment
   - kill criteria and pivot triggers
   - open questions that must be resolved by WF4/WF5
4. When dynamic context is enabled, refresh draft protocol assumptions or run `$protocol-compiler` if evidence tables changed.
5. Write `docs/Refined_Idea.md`.
6. Update `PROJECT_STATE.json` when stage-state synchronization is requested or required by the orchestrator.

## Output Rules

- Do not write architecture, module plans, registry changes, file trees, or implementation roadmaps here.
- Use `./references/refined-idea.md`.
- Architecture constraints may be recorded only as open design inputs for WF6.
- Include evidence sources and separate verified facts, inferences, operator preferences, and open questions.
- Protocol updates are drafts only; do not mark any contract as approved.
- Use the decision vocabulary: `SELECT`, `PILOT_FIRST`, `PIVOT`, or `ABANDON`.
- Report a Gate ledger when refined idea docs, protocol assumptions, or canonical state are written. If protocol compilation, drift checks, or workflow-state checks are not run, mark them `NOT_RUN` with the reason.
- Treat template wording as structure-only; localize headings and narrative text according to `../../../.agents/references/language-policy.md` unless a field is explicitly English-only.

## Execution Rule

Keep this stage narrow: turn survey and debate into a feasible idea and testable research framing. Leave architecture selection until after data and baseline evidence exist.
