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

## Practical Bootstrap Order

When you initialize a new project, identify the three roles first:

- **target workspace**: the new repo that will actually run harness
- **framework source**: this repo (`Harness-Research/`), used as the bootstrap source
- **baseline/reference repo**: an optional old project used only for comparison

Only the **target workspace** should receive the harness bootstrap. In the Aegis
bring-up, that meant:

- `Aegis/` was the real workspace root
- `MARS/` was only a baseline reference
- `Harness-Research/` was only the framework source tree

Recommended order:

1. choose the real workspace root
2. move the framework git history to `.harness`
3. initialize or reuse the normal research `.git`
4. create `CLAUDE.md`, `AGENTS.md`, and `docs/auto_iterate_goal.md`
5. create remote-control and auto-iterate local configs in the workspace
6. verify `cc-connect`, `cw`, `codex_all`, and `auto_iterate_ctl.sh`

For the full bootstrap checklist, see [AI_AGENT_SETUP.md](AI_AGENT_SETUP.md).

## Common Bootstrap Gotchas

- A sibling repo such as `MARS/` can be a baseline, but it should not be turned
  into the live harness workspace unless that is the intended project root.
- `Harness-Research/tooling/remote_control/config/` may only contain
  `README.md` and `templates/` in a fresh framework clone. The live files
  `cc_connect.local.toml` and `remote_control.local.yaml` are created later in
  the target workspace.
- A successful `tooling/remote_control/bin/cc-connect -version` is not enough
  to prove the shared-session stack works. Also verify:
  - `tooling/remote_control/bin/cc-connect share list --config tooling/remote_control/config/cc_connect.local.toml`
  - `tooling/remote_control/bin/cw list`
  - `tooling/remote_control/bin/codex_all help`
- In dual-repo mode, the shared root `.gitignore` is read by both git histories.
  If normal `git status` stops showing research files such as `CLAUDE.md`,
  `AGENTS.md`, `docs/`, or `src/`, move those research-side hide rules into
  `.harness/info/exclude` instead of leaving them in the root `.gitignore`.

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

Some code is based on [ralph](https://github.com/snarktank/ralph) and [cc-connect](https://github.com/chenhg5/cc-connect).
