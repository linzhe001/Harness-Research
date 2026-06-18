---
name: auto-paper
description: "Internal Harness instruction source for auto-paper. Route through visible Harness aliases or hook contracts instead of invoking directly."
---

# Auto Paper

Use this Skill as the auto-paper orchestrator, not a direct polishing tool. It
routes phases, checks artifacts, and keeps paper-writing state separate from
auto-iterate experiment state.

## Boundaries

- Author evidence outranks exemplars: local results, figures, tables, notes,
  approved claim boundaries, and operator facts.
- Do not invent experiments, results, mechanisms, statistics, novelty,
  clinical meaning, data availability, citations, or source support.
- Blog, review, survey, and tutorial outputs are not citation-free by default.
  If they contain literature claims, technology-history claims, clinical
  claims, benchmark claims, or named prior work, build citation artifacts and
  insert citation markers or a verified-reference plan. Only skip citations
  when the operator explicitly requests an uncited opinion memo.
- External papers are examples for structure, style, terminology, and
  positioning, not author claims.
- Patch LaTeX only from written artifacts.
- Read experiment results primarily through
  `docs/30_evidence/Experiment_Evidence_Index.{json,md}` and the artifact
  paths named there. Direct `iteration_log.json` reads are allowed as weak
  signals for experiment intent, but paper claims require cross-checks against
  reports, configs, logs, metrics, or run artifacts.
- Do not write `iteration_log.json` or `.auto_iterate/**`; auto-paper state
  uses `auto_paper_log.json`, `.auto_paper/`, and
  `auto_paper_output/<paper_id>/`.

## Required Config

Before the loop, establish `paper_id`, workflow, venue/target, draft path, TeX
roots, bibliography paths, figures, materials, references, artifact dir,
optional `experiment_evidence_index`, output language, citation target count,
figure/table requirement status, compile command, human gate policy, and
forbidden directions in
`auto_paper_output/<paper_id>/config.yaml` or intake artifact. If missing,
route to `$auto-paper-intake` or return `USER_GATE`.

Use the controller for file-state inspection and resumable routing when the
operator requests an automatic paper chain:

```bash
tooling/auto_paper/scripts/auto_paper_ctl.sh start \
  --paper-id <paper_id> \
  --artifact-dir auto_paper_output/<paper_id>
```

The controller checks artifacts and writes `.auto_paper/` runtime state. It
does not invent manuscript content.

## Phase Route

Run in order unless an audit routes back:

1. `$auto-paper-research`
2. `$auto-paper-argument`
3. `$auto-paper-citation`
4. `$auto-paper-layout`
5. `$auto-paper-patch`
6. `$auto-paper-harden`

Optional branches: `$auto-paper-response`, `$auto-paper-data`,
`$auto-paper-figure`. Enter `$auto-paper-figure` when the operator asks for
figure work, when existing TeX references figures, when source PDFs/Markdown
mention needed figures/tables, or when harden finds figure/caption risk.

## Artifacts

Durable decisions live under `auto_paper_output/<paper_id>/`.

- Intake: `config.yaml`, `source_index.md`, `tex_inventory.json`,
  `intake_report.md`, `experiment_source_map.md`,
  optional `figure_requirement_scan.md`
- Research: `research_dossier.md`, `exemplar_learning_dossier.md`,
  `style_profile.md`, `sota_gap_map.md`
- Argument: `confirmed_motivation.md`, `claim_register.md`,
  `claims_to_avoid.md`, `motivation_surface_map.md`
- Citation: `citation_support_bank.md`, `claim_citation_map.md`
- Layout: `original_logic_map.md`, `section_blueprints.md`,
  `writing_rationale_matrix.md`, `citation_plan.md`, `latex_patch_plan.md`
- Figure branch: `figure_asset_map.md`, `figure_contract.md`,
  `caption_claim_map.md`, `figure_backend_report.md`
- Patch/Harden: diffs, `patch_ledger.md`, guard/compile reports,
  `audit_report.md`, `citation_audit_report.md`, `logic_transfer_audit.md`,
  `final_gate_ledger.md`, `run_request_register.{json,md}` when new
  experiments are needed

Use `references/artifact-contract.md` for identifiers and stale-artifact
policy.

## Gate And Routing

Do not patch around missing upstream artifacts. Every audit finding names
`root_cause`, `owning_phase`, `required_artifact`, `fix_action`, and
`downstream_risk`.

Decisions: `NEXT_UNIT`, `REWORK_RESEARCH`, `REWORK_ARGUMENT`,
`REWORK_CITATION`, `REWORK_LAYOUT`, `REWORK_PATCH`, `RUN_REQUEST`,
`USER_GATE`, `COMPLETE`, `ABORT`.

`RUN_REQUEST` means the writing chain found a missing experiment or result
artifact that `$run` should plan next. Record the request in
`run_request_register.{json,md}` with the blocking claim, needed evidence,
minimum artifacts, suggested run prompt, and acceptance check.

## References

Load only active-phase references from `references/`: loop, auto-iterate
boundary, artifact contract, writing rationale, motivation thread, citation
support, and LaTeX source control as needed.

Use deterministic helpers when available:

- `.agents/skills/auto-paper/scripts/figure_requirement_scan.py` for
  PDF/Markdown/notes figure and table cue discovery
- `../../../.agents/references/research-supervision-patterns.md` for paper
  logic, figure, and pre-submission review patterns
- `../../../.agents/references/research-supervision/README.md` for active
  paper-writing, benchmark, plotting, case-pattern, and hardening assets
## Output

Final responses report artifact manifest, modified files, guard/compile
results, remaining reviewer risks, and next human gates.
