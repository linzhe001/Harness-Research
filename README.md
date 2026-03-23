# Harness Research Loop

A structured 10-stage research workflow framework for CV/ML projects, designed to work with **Claude Code** and **Codex** as AI research assistants.

## What This Is

This repo contains the **framework only** — skills, rules, templates, and workflow definitions. It does **not** contain any research code. Each research project has its own separate git repo; this framework is layered on top via a dual-repo setup.

### Framework Contents

| Path | Purpose |
|------|---------|
| `.claude/skills/` | Claude Code skill definitions (18 skills) |
| `.claude/rules/` | Auto-triggered rules (pre-training, project-map, deps-update) |
| `.claude/shared/` | Shared references (code style) |
| `.claude/Workflow_Guide.md` | Full workflow documentation for Claude Code |
| `.agents/skills/` | Codex agent skill definitions (18 skills) |
| `.agents/references/` | Shared behavior constraints for Codex |
| `CLAUDE.md.template` | Project CLAUDE.md template with `{{placeholders}}` |
| `AGENTS.md.template` | Project AGENTS.md template with `{{placeholders}}` |
| `settings.local.json.template` | Claude Code permissions template |
| `tooling/auto_iterate/scripts/` | V7 auto-iterate controller, runtime adapter, CLI, and package code |
| `tooling/auto_iterate/scripts/auto_iterate/` | Controller package (state, lock, events, goal, etc.) |
| `tooling/auto_iterate/config/auto_iterate_*.example.yaml` | Controller and account configuration examples |
| `tests/fixtures/auto_iterate/` | Contract test fixtures |
| `tests/test_auto_iterate_*.py` | Controller test suite |
| `tooling/auto_iterate/docs/auto_iterate_goal_template.md` | Goal file template for auto-iterate |
| `tooling/auto_iterate/docs/remote_control_guide.md` | Operator runbook for remote control |
| `auto_iterate_v7_plan/` | V7 plan/spec documents for the controller rollout |

### Workflow Stages

```
WF1(survey) → WF2(arch) → WF3(check) → WF4(data) → WF5(baseline)
→ WF6(plan) → WF7(code) → WF7.5(validate) → WF8(iterate) → WF9(final-exp) → WF10(release)
```

---

## AI Agent Setup

For same-worktree bootstrap and dual-repo instructions, see
[AI_AGENT_SETUP.md](AI_AGENT_SETUP.md).

That guide covers:

- how `.harness` / `hgit` coexists with the research repo's normal `.git`
- how to bootstrap project-owned files from harness templates
- how auto-iterate is split between harness-managed tooling and research-managed project/runtime files
- how to keep harness files out of `git status` without fighting the harness-owned root `.gitignore`

---

## Daily Usage

```bash
# Research code changes → normal git
git add src/models/my_model.py
git commit -m "train(research): add depth-guided loss"
git push

# Harness framework updates → hgit
hgit pull origin main                    # pull framework updates
hgit add .claude/skills/iterate/SKILL.md # or push local improvements
hgit commit -m "feat: add ablation sub-command"
hgit push origin main
```

## Updating Framework in Existing Projects

```bash
cd /path/to/existing-project
hgit pull origin main
# Framework files (.claude/skills/*, .agents/*) are updated automatically
# CLAUDE.md (research-specific) is untouched — harness repo does not track it
```

If `CLAUDE.md.template` has new sections you want to adopt:

```bash
diff CLAUDE.md.template CLAUDE.md
# Manually merge relevant new sections into your project's CLAUDE.md
```

---

## File Ownership Summary

| File | Tracked by | Purpose |
|------|-----------|---------|
| `.claude/skills/**` | harness (`hgit`) | Skill definitions |
| `.claude/rules/**` | harness (`hgit`) | Auto-triggered rules |
| `.claude/shared/**` | harness (`hgit`) | Shared references |
| `.claude/Workflow_Guide.md` | harness (`hgit`) | Workflow documentation |
| `.agents/skills/**` | harness (`hgit`) | Codex agent definitions |
| `.agents/references/**` | harness (`hgit`) | Shared constraints |
| `*.template` | harness (`hgit`) | Project templates |
| `tooling/auto_iterate/**` | harness (`hgit`) | Controller, runtime adapter, docs, examples |
| `auto_iterate_v7_plan/**` | harness (`hgit`) | Controller rollout plan/spec |
| `README.md` | harness (`hgit`) | Harness overview and links |
| `.gitignore` | harness (`hgit`) | Harness-side ignore rules for research files |
| `.git/info/exclude` | research-local (`git`) | Research-side ignore rules for harness files |
| `CLAUDE.md` | research (`git`) | Project-specific config |
| `AGENTS.md` | research (`git`) | Project-specific config |
| `src/`, `scripts/`, `configs/` | research (`git`) | Research code |
| `docs/auto_iterate_goal.md` | research (`git`) | Project goal source consumed by auto-iterate |
| `configs/auto_iterate_*.yaml` | research (`git`) | Project-specific auto-iterate config copied from examples |
| `PROJECT_STATE.json` | research (`git`) | Workflow stage state |
| `iteration_log.json` | research (`git`) | Experiment history |
| `project_map.json` | research (`git`) | Code architecture map |
| `.auto_iterate/` | ignored runtime state | Controller state, lock, events, runtime logs |
