---
name: run
description: "Visible Harness run entry. Use for WF10 experiment iteration: model exploration, hyperparameter changes, ablations, visualization, and quantitative runs."
---

# Run

Use `$run` as the human-facing alias for WF10 iteration work. This is not a
separate Skill Contract.

Read and follow:
- `../../../.agents/skills/iterate/SKILL.md`
- `../../../.agents/skills/auto-iterate-goal/SKILL.md` when starting auto-iterate
- `../../../AGENTS.md`
- `../../../CLAUDE.md`

Route the actual work through `$iterate next` by default. `$iterate next` reads
the active iteration's `action_state.next_action` and then runs exactly one
action from the WF10 action library: `plan`, `code`, `run_screening`,
`run_full`, `eval`, `debug`, `compare`, `ablate`, `register`, `promote`,
`discard`, or `stop`. Direct subcommands remain available when the operator
names one explicitly.

Run-time code construction has three weights:
- `config_only`: create or edit only run-local configs and record no code
  manifest unless useful.
- `run_local_code`: create bounded run-local scripts under `runs/wf10/<iter>/`
  and record `runs/wf10/<iter>/code_manifest.json`.
- `stable_candidate` or `delegated_build`: use heavier build/code-debug
  discipline, record the manifest, and require a promotion plan before merging
  back into stable `src/`, `scripts/`, `configs/`, tests, or `project_map.json`.

Meaningful train/eval work is commit-driven:
- before `run_screening` or `run_full`, create or verify `pre_train_commit`
  covering stable code, eval logic used by the command, durable configs, and
  run-local code/configs under `runs/wf10/<iter>/`
- before `eval`, create or verify `pre_eval_commit`, or record
  `pre_eval_commit_NOT_CHANGED`
- record those hashes in the run manifest or Gate ledger so the run can be
  reproduced or reverted
- do not ask for human approval during WF10 iteration when the action stays
  inside the active Automation Policy; use Gate ledgers and Claim Delta
  Evidence for traceability

When a run-local script or candidate implementation becomes reusable, use
`$iterate promote` or route through `$change classify` before merging it into
stable code. Promotion must read the run code manifest, write a promotion plan,
run acceptance commands or report `NOT_RUN`, and update stable maps when public
interfaces or responsibilities change.

When `auto_paper_output/*/run_request_register.{json,md}` has pending requests,
fold the highest-priority unclosed request into the next `$iterate plan` unless
the operator asks to ignore paper-driven experiments. After `$iterate eval` or
`$analyze` updates completed run evidence, refresh the default light layer
`.evidence/light/index.json` with
`tooling/evidence/build_light_evidence_index.py`. Refresh the paper-facing
`docs/30_evidence/Experiment_Evidence_Index.{json,md}` with
`tooling/evidence/build_experiment_evidence_index.py` only when claim or
writing evidence needs the detailed layer, or report `NOT_RUN`.

When eval creates follow-up questions, assurance gaps, or paper-driven missing
evidence, append or refresh `docs/40_iterations/Experiment_Queue.md`. When a
finding should remain searchable outside a single iteration report, append or
refresh `docs/45_discoveries/Research_Wiki.md`. These files are source
artifacts for later light evidence indexing, not approval records.
