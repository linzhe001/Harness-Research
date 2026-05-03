---
name: refine-idea
description: WF3 idea refinement. Turn WF1 survey and WF2 idea debate into a feasible, testable research idea without designing architecture.
argument-hint: "[selected_direction]"
disable-model-invocation: true
allowed-tools: Read, Write, Glob, Grep, Bash
---

# WF3: Refine Idea

Use this skill after WF1 survey and WF2 idea debate.

Read first:
- `PROJECT_STATE.json` if it exists
- `OPERATOR_CONTEXT.md` if it exists
- `docs/Feasibility_Report.md` if it exists
- `docs/Idea_Debate.md` if it exists
- `docs/30_evidence/Evidence_Index.md` if it exists
- `docs/35_protocol/Research_Protocol.md` if it exists
- `templates/refined-idea.md`
- `../../shared/context-layering-policy.md`
- `../../shared/research-invariants.md`
- `../../shared/documentation-evidence-rule.md`
- `../../shared/documentation-style.md`
- `../../shared/language-policy.md`

Required work:
1. Identify the selected idea or variant and record why alternatives were rejected or deferred.
2. Define problem statement, target task, data assumptions, candidate baselines, target metrics, success criteria, minimum viable experiment, kill criteria, and pivot triggers.
3. Record open questions that must be resolved by WF4 data-prep or WF5 baseline-repro.
4. When dynamic context is enabled, refresh draft protocol assumptions or run `/protocol-compiler` if evidence tables changed.
5. Write `docs/Refined_Idea.md`.
6. Update `PROJECT_STATE.json` when stage synchronization is required.

Do not write architecture, module plans, file trees, or implementation roadmaps. Architecture design belongs to WF6 after data and baseline evidence exist.
