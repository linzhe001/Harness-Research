<p align="center">
  <img src="media/harness_simple_banner.jpeg" alt="Harness Research banner inspired by The Defect from Slay the Spire 2". width="100%" />
</p>

<p align="center">
  The visual identity of <strong>Harness Research</strong> is inspired by The Defect from <em>Slay the Spire 2</em>.
</p>


<h1><img src="media/harness_icon.png" alt="Harness Research icon inspired by The Defect from Slay the Spire 2." width="56" /> Harness Research</h1>

A domain-neutral, evidence-grounded research workflow framework for AI/ML projects, designed to work with **Claude Code** and **Codex** as AI research assistants.


## What This Is

This repo contains the **framework only** — skills, rules, templates, workflow definitions, document schemas, and the auto-iterate controller. It does **not** contain any research code. Each research project has its own separate git repo; this framework is layered on top via a dual-repo setup (harness `.harness` + research `.git` sharing one worktree).

## Dynamic Context Model

Harness does not ship fixed research-track profiles such as CV, LLM, or RL. It
keeps the core process domain-neutral and lets each project derive its own
research protocol from current evidence:

```text
operator context -> research evidence -> dynamic protocol -> approved contract
  -> evidence-compiled docs -> reproducible iteration -> promoted lessons
```

The framework owns the rules, templates, schemas, and skills that control this
flow. The research project owns the actual context files:

- `OPERATOR_CONTEXT.md` for stable operator preferences, not project facts
- `docs/20_facts/**` for current factual summaries derived from project artifacts
- `docs/30_evidence/**` for papers, repos, datasets, benchmarks, metrics, and open questions
- `docs/35_protocol/**` for the current evidence-derived protocol draft
- `docs/10_contract/**` for human-approved project, evaluation, baseline, and claim boundaries
- `.evidence/chains/**` for auditable evidence chains behind current docs
- `.evidence/index.json` for the latest docchain pointer per compiled doc
- `docs/50_memory/**` and `MEMORY.md` for promoted lessons and decisions

Older flat docs such as `docs/Feasibility_Report.md`,
`docs/Technical_Spec.md`, and `docs/Baseline_Report.md` are compatibility
inputs. Treat their current factual content as fact-layer material to migrate
into `docs/20_facts/**`; archive superseded snapshots under `docs/90_legacy/`.
New projects should create the numbered docs directories from `templates/docs/`.

Useful framework tools:

```bash
python tooling/evidence/init_context.py --workspace-root . --set-state
python tooling/evidence/compile_protocol.py --workspace-root .
python tooling/evidence/check_dynamic_context.py --workspace-root . --stage wf10 --review-packet
python tooling/evidence/check_context_gates.py --workspace-root . --stage wf10-auto
python tooling/evidence/check_protocol_drift.py --workspace-root . --stage wf10
python tooling/evidence/build_review_packet.py --workspace-root . --stage wf10
python tooling/evidence/approve_contract.py --workspace-root . --contract evaluation_contract --approved-by "<human reviewer>" --approval-source ".evidence/review_packets/wf10/<build_id>/review_packet.md"
python tooling/evidence/compile_doc.py --workspace-root . --doc docs/10_contract/Project_Contract.md --source PROJECT_STATE.json docs/30_evidence/Evidence_Index.md
python tooling/evidence/validate_docchain.py .evidence/chains/<doc_id>/<build_id>
python tooling/evidence/check_docchain_gates.py --workspace-root .
python tooling/evidence/check_workflow_state.py --workspace-root .
python tooling/evidence/migrate_legacy_docs.py --workspace-root .
```

`init_context.py` never overwrites existing docs unless `--overwrite` is passed.
`compile_protocol.py` compiles evidence tables into a reviewable draft packet
under `.evidence/protocol_compiler/`; use `--apply --overwrite` only after
review.
`check_dynamic_context.py` runs the context, protocol-drift, docchain, and
workflow-state gates from one command, with optional review-packet generation.
`check_context_gates.py` keeps legacy projects compatible while enforcing
Evaluation Contract readiness for dynamic-context auto-iteration.
`check_protocol_drift.py` detects explicit protocol-review blockers such as
blocking open questions, due assumptions, negative results, or pivot decisions.
`build_review_packet.py` writes a concise human review packet under
`.evidence/review_packets/` for approval, revision, or rejection decisions.
`approve_contract.py` records explicit human approval in both the contract
Markdown and `PROJECT_STATE.json`; run it only after the current conversation or
review record contains that approval, then rerun the dynamic-context gate.
`compile_doc.py` v0 records explicit sources and markers into docchain JSON; it
also refreshes the Markdown evidence headers and `.evidence/index.json`.
It does not replace agent or human judgment about semantic support.
Rerun it whenever the Markdown, explicit source artifacts, fact markers,
confidence, or support relation changes. Old `.evidence/chains/<doc>/<build>/`
directories are audit history; the current Markdown headers and
`.evidence/index.json` point to the latest build.
`check_docchain_gates.py` scans current contract/fact/protocol docs and fails
when their evidence chain is missing, invalid, stale, or violates clean/patch
git-context requirements.
`check_workflow_state.py` checks `PROJECT_STATE.json`, `iteration_log.json`,
`project_map.json`, `.auto_iterate/state.json`, lesson candidates, and
cross-file consistency when those files exist.
`migrate_legacy_docs.py` is a default dry-run helper for moving old
`docs/legacy/**` files into the canonical `docs/90_legacy/<date>/` archive.

Set `PROJECT_STATE.json.workflow_mode` explicitly for new projects:
`dynamic_context` for numbered context docs, `standard` for new projects without
numbered context docs, and `compatibility` only for older imported projects that
predate mandatory WF2/dynamic gates.

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
4. create `CLAUDE.md`, `AGENTS.md`, `MEMORY.md`, and `docs/auto_iterate_goal.md`
5. optionally create `OPERATOR_CONTEXT.md`, numbered docs directories, and `.evidence/`
6. create remote-control and auto-iterate local configs in the workspace
7. verify `cc-connect`, `cw`, `codex_all`, and `auto_iterate_ctl.sh`

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
- Current project docs should stay concise in `docs/`; superseded Markdown
  snapshots should move under `docs/90_legacy/`.

## Workflow Overview

```
WF1(survey) → WF2(idea-debate) → WF3(refine-idea) → WF4(data) → WF5(baseline)
→ WF6(arch) → WF7(plan) → WF8(code) → WF9(validate) → WF10(iterate) → WF11(final-exp) → WF12(release)
```

The core iteration loop (WF10) follows four stages per round:

```
plan (hypothesis) → code (implement) → run (train + metrics) → eval (decision)
```

Eval produces one of five decisions: **NEXT_ROUND**, **DEBUG**, **CONTINUE** (advance to WF11), **PIVOT** (roll back to WF2 idea debate/refinement), or **ABORT**.

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

## Codex Accounts

WF10 auto-iterate uses Cockpit-managed Codex accounts as the credential source.
The controller still isolates phases by setting one `CODEX_HOME` per account,
but those homes are generated projections under `~/.cache/auto_iterate/codex/`,
not hand-created `.codex-acc*` login directories.

Before long unattended runs, refresh the local account registry:

```bash
tooling/auto_iterate/scripts/project_cockpit_codex_accounts.py \
  --accounts-yaml tooling/auto_iterate/config/accounts.local.yaml
```

Then start the controller with `--accounts tooling/auto_iterate/config/accounts.local.yaml`.

## For AI Agents

- **At project setup**: read [AI_AGENT_SETUP.md](AI_AGENT_SETUP.md) for bootstrap instructions, framework contents, file ownership, and dual-repo layout.
- **At framework update**: read [Harness_Update_Guide.md](Harness_Update_Guide.md) for pull/push workflows, conflict recovery, and post-pull template sync.

Some code is based on [ralph](https://github.com/snarktank/ralph) and [cc-connect](https://github.com/chenhg5/cc-connect).
