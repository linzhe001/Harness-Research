# Contract Gating Rule

## Purpose

Separate AI-generated research protocol drafts from human-approved execution
contracts.

## Contract Files

New dynamic-context-v2 projects use one canonical file:

- `docs/context/contracts.md`

It records named sections and headers for:

- `Project Contract status`
- `Evaluation Contract status`
- `Baseline Contract status`
- `Claim Boundary status`

Legacy or not-yet-migrated projects may still use:

- `docs/10_contract/Project_Contract.md`
- `docs/10_contract/Evaluation_Contract.md`
- `docs/10_contract/Baseline_Contract.md`
- `docs/10_contract/Claim_Boundary.md`

Each contract must expose one of these statuses near the top or in its named
v2 header:

- `missing`
- `draft`
- `approved`
- `superseded`

## Approval Semantics

- AI may create `draft` or `proposed` contract content.
- AI must not mark a contract as `approved` unless the current conversation
  contains explicit human approval for that contract.
- Research evidence and protocol compiler output are inputs to review only; they
  never become approved contracts by themselves.
- Gate tooling treats `Status: approved` as confirmed only when both approval
  records exist:
  - the contract Markdown has `Human approved: yes` or the matching v2 header
    such as `Evaluation Contract human approved: yes`
  - `PROJECT_STATE.json.contracts.<contract>.status` is `approved` and the
    contract entry includes `approved_at`, `approved_by`, and `approval_source`
- Approved contracts override dynamic protocols and operator preferences.
- If a contract conflicts with current evidence, record the conflict and ask for
  review instead of silently changing the contract.

## Promotion Flow

1. Compile or update draft protocol/contract content from current evidence.
2. Compile the contract docchain with `tooling/evidence/compile_doc.py` and
   explicit source artifacts.
3. Run `tooling/evidence/check_dynamic_context.py --stage <stage> --review-packet`
   and give the review packet to the operator.
4. Only after explicit human approval, update both approval records:
  - contract Markdown: `Status: approved` and `Human approved: yes`, or the
    matching v2 named status and approval headers
   - `PROJECT_STATE.json.contracts.<contract>`: `status: approved`,
     `approved_at`, `approved_by`, and `approval_source`
5. Re-run the dynamic-context gate suite. If it fails, keep the contract in
   draft or fix the recorded issue before treating it as approved.

Use the approval tooling for step 4 instead of hand-editing both files:

```bash
python tooling/evidence/approve_contract.py \
  --workspace-root . \
  --contract evaluation_contract \
  --approved-by "<human reviewer>" \
  --approval-source ".evidence/review_packets/wf10/<build_id>/review_packet.md"
```

Valid `--contract` values are `project_contract`, `evaluation_contract`,
`baseline_contract`, and `claim_boundary`. After the command, re-run
`python tooling/evidence/check_dynamic_context.py --workspace-root . --stage <stage> --review-packet`.

## Gate Ledger

Contract and readiness work must report the actual gate evidence used for the
decision. Use this short format for contract promotion, current contract/fact
doc updates, WF10/WF11/WF12 readiness, and release claims:

```text
Gate ledger
- command: <exact command or "not run">
- result: PASS | FAIL | NOT_RUN
- reason: <why this gate was required or why it could not run>
- artifacts: <contract/doc/state/evidence paths created or updated>
```

Do not treat a skill instruction, review packet, Codex sandbox approval,
execpolicy rule, or hook reminder as proof that a Harness gate passed. A
contract/readiness claim is machine-verified only when the relevant command,
controller check, CI job, or approval tool actually ran; otherwise report
`NOT_RUN`.

## Gates

- WF4-WF9 may proceed with draft contracts when the operator accepts the risk.
- WF10 auto-iteration must have an approved or explicitly operator-accepted
  Evaluation Contract.
- WF11 and WF12 must have approved Project Contract, Evaluation Contract, and
  Claim Boundary before final experiment design or release claims.

## Legacy Compatibility

Older projects may not have `docs/context/contracts.md` or
`docs/10_contract/**`. In legacy mode, warn and fall back to
`PROJECT_STATE.json.evaluation_protocol`,
`docs/Baseline_Report.md`, and existing workflow artifacts.
