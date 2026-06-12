# Protocol Drift Check

## References

Read these first:
- `../../shared/context-layering-policy.md`
- `../../shared/research-invariants.md`
- `../../shared/evidence-chain-rule.md`
- `../../shared/contract-gating-rule.md`
- `../../shared/documentation-evidence-rule.md`
- `../../shared/language-policy.md`

Tooling:
- `../../../tooling/evidence/check_protocol_drift.py`
- `../../../tooling/evidence/check_docchain_gates.py`

## When To Use

Use this skill when a dynamic-context project is about to:

- enter or complete WF5 baseline reproduction
- start unattended WF10 auto-iteration
- advance from WF10 to WF11
- design final experiments
- prepare release claims
- update `docs/10_contract/**` from `docs/35_protocol/**`

Legacy projects without `docs/35_protocol/**` should receive a compatibility
note, not a forced migration.

## Required Work

1. Identify the target stage: `wf5`, `wf10`, `wf11`, `wf12`, or `status`.
2. Run:

   ```bash
   python tooling/evidence/check_protocol_drift.py --workspace-root . --stage <stage>
   ```

3. Read the reported checks. Treat these as explicit drift signals:
   - `Review required: yes` in `docs/35_protocol/Research_Protocol.md`
   - blocking rows in `docs/30_evidence/Open_Questions.md`
   - low-confidence assumptions whose review trigger has arrived
   - negative result IDs missing from `Protocol_Review.md` or `Protocol_Changelog.md`
   - latest `PIVOT` or `ABORT` iteration decisions not referenced by protocol review/changelog
4. If the gate fails, refresh `docs/35_protocol/Research_Protocol.md`,
   `Protocol_Assumptions.md`, `Protocol_Review.md`, and
   `Protocol_Changelog.md` before promoting protocol content into contracts.
5. For updated current docs, use `/doc-compiler` and rerun
   `check_docchain_gates.py`.
6. Report a gate ledger for the drift check and any docchain gate rerun.

## Durable Docs Render

After stable Markdown outputs for this skill are finalized, invoke `/docs-site` or report `docs_site_boundary_report`. Do not render after temporary draft edits; Markdown remains the source of truth.

## Output Rules

- Do not silently mark protocol review as accepted.
- Do not convert protocol drafts into approved contracts without explicit human
  approval.
- If evidence is contradictory or insufficient, keep it in Open Questions.
- Report whether the project is safe to continue, safe only with an explicit
  operator exception, or blocked pending protocol review.

## Durable Docs Render

After stable Markdown is finalized, invoke `/docs-site` or report
`docs_site_boundary_report` / `docs_site_render_or_NOT_RUN`. Do not render for
temporary drafts.
