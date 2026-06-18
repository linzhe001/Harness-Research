---
name: build
description: "Visible Harness build entry. Use after prepare to plan and implement the minimal runnable codebase slice through workflow-supervisor build automation."
---

# Build

Use `$build` as the human-facing alias for the Execution Supervisor `build`
segment. This is not a separate Skill Contract.

Read and follow:
- `../../../.agents/skills/workflow-supervisor/SKILL.md`
- `../../../.agents/references/workflow-supervisor-runtime.md`
- `../../../AGENTS.md`
- `../../../CLAUDE.md`

Preflight:

1. Run `status --json`.
2. If a run or pending request is active, use `recover --repair-stale-running
   --auto-resume-answered --json`, then resume or report the typed pending
   request. Do not start a second build run.
3. If a worker appears stuck, follow `Worker Process Safety` in
   `workflow-supervisor`; do not directly kill Codex worker PIDs from the
   active Codex session/process group.
4. If no run is active, start the build segment.

Default command:

```bash
python tooling/workflow_supervisor/scripts/workflow_ctl.py start \
  --segment build \
  --goal "Implement the minimal runnable target research codebase slice from the approved contracts, current Technical Spec, Implementation Roadmap, project_map.json, prepare outputs, and baseline state. Build must reach a runnable smoke/evaluation/training-ready path, not only a planning or foundation slice." \
  --auto \
  --json
```

Scope:

- Keep the build scoped to the current Grill intent, approved contracts,
  prepare outputs, baseline state, `docs/Technical_Spec.md`,
  `docs/Implementation_Roadmap.md`, `project_map.json`, and the declared
  worker-result contract.
- The normal build path is `refine-arch -> build-plan -> code-expert ->
  validate-run`. `code-debug` is recovery only.
- `build_ready_for_iterate` means the minimal runnable path has validated. It
  must not be reported for a roadmap foundation slice alone unless the operator
  explicitly requested first-slice-only work.
- The worker result must include PASS/FAIL/NOT_RUN Gate ledger entries for
  postcondition command gates such as `roadmap implementation completeness` and
  `validate-run verdict`.
- Build workers must create semantic git commits for durable non-tool-owned
  outputs before a node can complete. For WF8 code nodes, every
  `docs/Implementation_Roadmap.md` `commit_plan` row must be implemented,
  validated, and committed as its own Commit Slice before the next independent
  row begins.
- Supervisor postconditions verify both `sliced_commits_recorded` from the
  run `base_git_commit` and `git_worktree_clean` for non-tool-owned paths.
  Missing or bundled roadmap slice commits keep the build node failed or
  paused; they must not be converted into `build_ready_for_iterate`.
- If the current implementation lacks the smoke runner, config, evaluator,
  training dry-run, or run-artifact bundle required by the roadmap, return
  `failed` or `interrupt_requested`; do not convert that state into success from
  artifact existence alone.
