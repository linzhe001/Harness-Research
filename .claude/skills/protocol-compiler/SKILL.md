---
name: protocol-compiler
description: Compile Dynamic Research Protocol drafts from current evidence tables without using pre-baked research profiles.
---

# Protocol Compiler

## References

Read these first:
- `../../shared/context-layering-policy.md`
- `../../shared/research-invariants.md`
- `../../shared/evidence-chain-rule.md`
- `../../shared/documentation-evidence-rule.md`
- `../../shared/contract-gating-rule.md`
- `../../shared/language-policy.md`

Tooling:
- `../../../tooling/evidence/compile_protocol.py`
- `../../../tooling/evidence/check_protocol_drift.py`
- `../../../tooling/evidence/check_docchain_gates.py`

## When To Use

Use this skill after WF1 evidence gathering, WF2 idea debate, WF3 refine-idea,
WF5 baseline evidence, or any evidence refresh that should update
`docs/35_protocol/**`. Architecture selection in WF6 may also trigger it when
the design changes protocol assumptions.

This skill must not introduce field profiles or generic domain rules. It may
only compile project-local protocol candidates from current evidence tables.

## Required Work

1. Re-read `docs/30_evidence/**`, especially:
   - `Evidence_Index.md`
   - `Paper_Table.md`
   - `Repo_Table.md`
   - `Dataset_Table.md`
   - `Baseline_Table.md`
   - `Metric_Table.md`
   - `Open_Questions.md`
2. Generate a reviewable draft packet:

   ```bash
   python tooling/evidence/compile_protocol.py --workspace-root .
   ```

3. Review the generated packet under `.evidence/protocol_compiler/<build_id>/`.
4. Apply only after review:

   ```bash
   python tooling/evidence/compile_protocol.py --workspace-root . --apply --overwrite
   ```

5. Run:

   ```bash
   python tooling/evidence/check_protocol_drift.py --workspace-root . --stage status
   ```

6. For applied protocol docs, use `/doc-compiler` to create
   evidence_chain/source_manifest/doc_audit if the docs will become current
   decision material.

## Output Rules

- Keep `Status: draft` and `Review required: yes` unless the current
  conversation contains explicit human acceptance.
- Treat all baselines, metrics, datasets, assumptions, and failure modes as
  candidates until human-approved contracts exist.
- Put unsupported, contradictory, or low-confidence items into Open Questions
  or Protocol Assumptions; do not promote them into contracts.
- Never mark a Project Contract, Evaluation Contract, or Claim Boundary as
  approved from protocol compilation alone.
