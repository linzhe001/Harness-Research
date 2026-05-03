---
name: idea-debate
description: WF2 idea debate. Stress-test candidate research directions after WF1 feasibility and before WF3 refine-idea.
argument-hint: "[idea_notes]"
disable-model-invocation: true
allowed-tools: Read, Write, Glob, Grep, WebSearch, WebFetch
---

# WF2: Idea Debate

Use this skill after WF1 survey. New projects should not skip directly from
WF1 to architecture design.

Read first:
- `PROJECT_STATE.json` if it exists
- `docs/Feasibility_Report.md` if it exists
- `docs/30_evidence/Evidence_Index.md` if it exists
- `docs/35_protocol/Research_Protocol.md` if it exists
- `../../shared/context-layering-policy.md`
- `../../shared/research-invariants.md`
- `../../shared/documentation-evidence-rule.md`
- `../../shared/documentation-style.md`
- `../../shared/language-policy.md`

Required work:
1. Extract 2-6 candidate ideas or variants. If only one idea exists, create conservative, balanced, and aggressive variants.
2. For each candidate, document strongest objection, likely failure mode, minimum viable experiment, kill criteria, compute estimate, and fallback/pivot path.
3. When dynamic context is enabled, refresh draft protocol assumptions without approving contracts.
4. Write `docs/Idea_Debate.md`.
5. Update `PROJECT_STATE.json` when stage synchronization is required.

Final decision vocabulary: `SELECT`, `PILOT_FIRST`, `MERGE`, `PIVOT`, or `ABANDON`.

Do not design architecture in this stage. The next stage is WF3 refine-idea.
