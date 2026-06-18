---
name: auto-paper
description: "Internal Harness instruction source for auto-paper. Route through visible Harness aliases or hook contracts instead of invoking directly."
---

# Auto Paper

Use this as the auto-paper orchestrator, not a polishing tool. It routes
phases, checks artifacts, and keeps paper state separate from auto-iterate
state.

## Boundaries

- Author evidence outranks exemplars: local results, figures, tables, notes,
  approved claim boundaries, and operator facts.
- Do not invent experiments, results, mechanisms, statistics, novelty,
  clinical meaning, data availability, citations, or source support.
- Blogs, reviews, surveys, and tutorials are citation-supported by default
  unless the operator explicitly asks for an uncited opinion memo.
- External papers are examples for structure, style, terminology, and
  positioning, not author claims.
- Patch LaTeX only from written artifacts.
- Read experiment results primarily through
  `docs/30_evidence/Experiment_Evidence_Index.{json,md}` and artifact paths
  named there. Direct `iteration_log.json` reads are weak intent signals; paper
  claims require reports, configs, logs, metrics, or run artifacts.
- Read `docs/context/experiments.md` when present for Research Wiki context,
  stable observations, run requests, assurance gaps, and open questions.
  Legacy `docs/45_discoveries/Research_Wiki.md` is a fallback before
  dynamic-context-v2 migration; neither file is approval.
- Do not write `iteration_log.json` or `.auto_iterate/**`; auto-paper state
  uses `auto_paper_log.json`, `.auto_paper/`, and
  `auto_paper_output/<paper_id>/`.

## Required Config

Before the loop, establish `paper_id`, workflow, venue/target, draft path, TeX
roots, bibliography paths, figures, materials, references, artifact dir,
optional experiment evidence index, output language, citation target count,
figure/table requirement status, compile command, human gate policy, and
forbidden directions in `auto_paper_output/<paper_id>/config.yaml` or an intake
artifact. If missing, route to `$auto-paper-intake` or return `USER_GATE`.

After Grill establishes an Automation Policy, paper phases auto-proceed within
that policy. Use `USER_GATE` only for missing operator intent, explicit approval
tools, or irreversible external submit.

Use the controller for resumable routing when the operator requests an automatic
paper chain:

```bash
tooling/auto_paper/scripts/auto_paper_ctl.sh start \
  --paper-id <paper_id> \
  --artifact-dir auto_paper_output/<paper_id>
```

The controller checks artifacts and writes `.auto_paper/`; it does not invent
manuscript content.

## Phase Route

Run in order unless an audit routes back: `$auto-paper-research`,
`$auto-paper-argument`, `$auto-paper-citation`, `$auto-paper-layout`,
`$auto-paper-patch`, `$auto-paper-harden`.

Optional branches: `$auto-paper-response`, `$auto-paper-data`,
`$auto-paper-figure`. Enter `$auto-paper-figure` when the operator asks for
figure work, TeX or source files mention needed figures/tables, or harden finds
figure/caption risk.

## Artifacts

Durable decisions live under `auto_paper_output/<paper_id>/`.

- Intake: `config.yaml`, `source_index.md`, `tex_inventory.json`,
  `intake_report.md`, `experiment_source_map.md`, optional
  `figure_requirement_scan.md`
- Phase artifacts: research dossier, style/gap maps, confirmed motivation,
  claim register, citation support bank, section blueprints, rationale matrix,
  citation and patch plans, figure contracts, patch ledgers, audits, and final
  gate ledger
- `run_request_register.{json,md}` when missing experiments are needed

Use `references/artifact-contract.md` for identifiers and stale-artifact policy.

## Gate And Routing

Do not patch around missing upstream artifacts. Every audit finding names
`root_cause`, `owning_phase`, `required_artifact`, `fix_action`, and
`downstream_risk`.

Decisions: `NEXT_UNIT`, `REWORK_RESEARCH`, `REWORK_ARGUMENT`,
`REWORK_CITATION`, `REWORK_LAYOUT`, `REWORK_PATCH`, `RUN_REQUEST`,
`USER_GATE`, `COMPLETE`, `ABORT`.

`RUN_REQUEST` means writing found missing experiment evidence for `$run`. Record
the blocking claim, needed evidence, minimum artifacts, suggested prompt, and
acceptance check in `run_request_register.{json,md}`.

When a draft introduces, narrows, or removes a result claim, record Claim Delta
Evidence in the phase artifact or Gate ledger. Unsupported claims become
`RUN_REQUEST`, not a default approval pause.

## References

Load only active-phase references from `references/`: loop, auto-iterate
boundary, artifact contract, writing rationale, motivation thread, citation
support, and LaTeX source control.

Use deterministic helpers when available:

- `.agents/skills/auto-paper/scripts/figure_requirement_scan.py`
- `../../../.agents/references/research-supervision-patterns.md`
- `../../../.agents/references/research-supervision/README.md`

## Output

Final responses report artifact manifest, modified files, guard/compile
results, remaining reviewer risks, and next human gates.
