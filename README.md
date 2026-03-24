<p align="center">
  <img src="media/harness_simple_banner.jpeg" alt="Harness Research banner inspired by The Defect from Slay the Spire 2, blending the visual ideas of Coolheaded and Iterate." width="100%" />
</p>

<p align="center">
  The visual identity of <strong>Harness Research</strong> is inspired by The Defect from <em>Slay the Spire 2</em>, combining the card motifs of Coolheaded and Iterate.
</p>


<h1><img src="media/harness_icon.png" alt="Harness Research icon inspired by The Defect from Slay the Spire 2." width="56" /> Harness Research</h1>

A structured 10-stage research workflow framework for CV/ML projects, designed to work with **Claude Code** and **Codex** as AI research assistants.


## What This Is

This repo contains the **framework only** — skills, rules, templates, workflow definitions, and the auto-iterate controller. It does **not** contain any research code. Each research project has its own separate git repo; this framework is layered on top via a dual-repo setup (harness `.harness` + research `.git` sharing one worktree).

## Workflow Overview

```
WF1(survey) → WF2(arch) → WF3(check) → WF4(data) → WF5(baseline)
→ WF6(plan) → WF7(code) → WF7.5(validate) → WF8(iterate) → WF9(final-exp) → WF10(release)
```

The core iteration loop (WF8) follows four stages per round:

```
plan (hypothesis) → code (implement) → run (train + metrics) → eval (decision)
```

Eval produces one of five decisions: **NEXT_ROUND**, **DEBUG**, **CONTINUE** (advance to WF9), **PIVOT** (roll back to WF2), or **ABORT**.

## Claude Code vs Codex: Division of Labor

Both agents share the same iteration schema (`iteration_log.json`), the same skill interfaces (`plan`/`code`/`run`/`eval`), and the same state ownership model. They differ in execution mode and skill authoring style:

| | Claude Code (`.claude/`) | Codex (`.agents/`) |
|---|---|---|
| **Execution mode** | Interactive — user drives each `/iterate` subcommand | Batch — controller auto-schedules `$iterate` phases |
| **Auto-iterate** | Manual loop only (V1) | Full controller support via `tooling/auto_iterate/` |
| **Skill style** | Thick instructions — self-contained step-by-step in each SKILL.md | Thin wrappers — SKILL.md references shared constraints in `references/` |
| **Safety net** | User reviews each step in real time | Controller postcondition validation + budget/patience tracking |
| **Best for** | Exploratory iteration, debugging, one-off experiments | Overnight batch runs, multi-round automated search |

**Shared invariants** (both agents):

- `iteration_log.json` is the single experiment source of truth, owned exclusively by the iterate skill
- `PROJECT_STATE.json` is owned by the orchestrator, read-only from iterate
- All code changes go through `code-debug`, all analysis through `evaluate`
- Identical iteration log schema, decision vocabulary, and context-passing protocol

**Style trade-offs**:

- Thick instructions (Claude Code) give higher determinism and easier debugging, but carry duplication risk when the schema evolves
- Thin wrappers (Codex) are DRY and low-maintenance, but depend on the model correctly interpreting the reference chain

In practice: use **Claude Code** for interactive research sessions, use **Codex** via the auto-iterate controller for unattended multi-round optimization.

## For AI Agents

- **At project setup**: read [AI_AGENT_SETUP.md](AI_AGENT_SETUP.md) for bootstrap instructions, framework contents, file ownership, and dual-repo layout.
- **At framework update**: read [Harness_Update_Guide.md](Harness_Update_Guide.md) for pull/push workflows, conflict recovery, and post-pull template sync.
