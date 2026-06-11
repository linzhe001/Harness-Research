# Workflow Supervisor Runtime Reference

## Purpose

Use this compact reference for routine Execution Supervisor operation and
maintenance. It replaces historical supervisor design drafts as the default
agent read target.

Do not read `docs/grill_execution_supervisor*.md`, `workflow_handbook/**`,
`docs/_site/**`, or `docs/_views/**` during routine supervisor work. Read those
only when the task is explicitly to maintain those documents or generated
views.

## Default Context

Routine supervisor work should start from:

- `AGENTS.md`
- `CLAUDE.md`
- `.agents/skills/workflow-supervisor/SKILL.md`
- `tooling/workflow_supervisor/config/default_nodes.json`
- `tooling/workflow_supervisor/config/gate_policy.yaml`
- the narrow source or test files for the requested change

Workers should read source artifacts directly only when the active node needs
them. Avoid re-reading broad workflow guides in every worker.

## Runtime Model

```text
start segment
  -> load node registry
  -> run `run_when=always` nodes in order
  -> validate worker result JSON
  -> validate node postconditions
  -> pause on typed HITL request or unrecovered gate failure
```

`run_when` values:

- `always`: normal ordered node.
- `on_failure`: recovery node. The supervisor may run it after a failed node,
  then retry the failed node once.
- `manual`: reserved for explicit/manual recovery or future tooling.

`build_code_debug` is an `on_failure` recovery node. It is not part of the
normal build path.

## Segment Boundaries

- `prepare --dry-run`: runtime readiness preflight only; no Review Packet gate.
- `prepare --complete`: readiness, acquisition plan, data/baseline acquisition,
  protocol compiler, WF5 Review Packet, then approval pause.
- `build`: `refine-arch -> build-plan -> code-expert -> validate-run`.
  `code-debug` runs only as failure recovery.
- `iterate`: delegates to auto-iterate and mirrors controller status.
- `release`: requires an explicit validate/package/submit action, runs WF11
  final experiment matrix first, then WF12 release gate and approval pause.
- `change`: classifies route only; it does not invoke the target skill.

Starting a new segment must fail closed while any active run or pending request
exists. Use `status`, `recover`, `answer`, `approve`, or `resume` first.

## Worker Prompt Contract

Worker prompts must include:

- automation budget
- allowed write patterns
- node `evidence_tools`
- node postconditions
- exact worker result handoff path

Workers must run listed `evidence_tools` when inputs exist. If a tool cannot
run, the worker result must include a `NOT_RUN` Gate ledger entry with the
reason.

## Docs-Site Boundary

Do not render generated HTML during ordinary supervisor, build, or change
nodes. Report `docs_site_boundary_report` unless the operator explicitly asks
for `$docs-site`, or the run is at a durable human-review, handoff, release, or
HTML submission boundary. Agents should not inspect `docs/_site/**` diffs.
