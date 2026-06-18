# Contracts

Context doc: contracts
Context model: dynamic-context-v2
Status: draft
Evidence chain: N/A
Evidence audit: N/A
Audit result: N/A

Project Contract status: draft
Project Contract human approved: no
Project Contract approved at:
Project Contract approved by:
Project Contract approval source:

Evaluation Contract status: draft
Evaluation Contract human approved: no
Evaluation Contract approved at:
Evaluation Contract approved by:
Evaluation Contract approval source:
Evaluation Contract draft accepted for current run: no

Baseline Contract status: draft
Baseline Contract human approved: no
Baseline Contract approved at:
Baseline Contract approved by:
Baseline Contract approval source:

Claim Boundary status: draft
Claim Boundary human approved: no
Claim Boundary approved at:
Claim Boundary approved by:
Claim Boundary approval source:

## Project Contract

### Current Answer

State the execution boundary, forbidden directions, external access limits, and
stop conditions.

### Automation Policy

| Flow | Auto Proceed | Human Approval Required | Notes |
|---|---:|---:|---|
| grill_exit | no | yes | Grill approval/delegation boundary. |
| prepare | yes | no | Inside accepted Automation Policy. |
| build | yes | no | Requires Gate ledger and commit checkpoints. |
| run | yes | no | Requires Semantic Execution Commit before train/eval. |
| analyze | yes | no | Requires evidence-backed decisions. |
| write | yes | no | Claims require Conclusion Evidence. |
| change | yes | no | Route or escalate when policy is exceeded. |
| external_submit | no | yes | Irreversible external action. |

## Evaluation Contract

### Current Answer

State what counts as improvement and what must not be claimed yet.

### Primary Metric

| Metric | Direction | Target | Evidence | Notes |
|---|---|---|---|---|
| | maximize/minimize | | | |

### Tracked Metrics

| Metric | Direction | Required For | Evidence | Notes |
|---|---|---|---|---|
| | | | | |

## Baseline Contract

| Baseline | Source | Required Status | Metric | Notes |
|---|---|---|---|---|
| | | verified/partial/skipped | | |

## Claim Boundary

- Allowed claims:
- Forbidden claims:
- Required evidence before release:

## Human Review Checklist

- [ ] Project execution boundary is understood.
- [ ] Primary metric identity, direction, and target are approved.
- [ ] Baselines and skip rules are acceptable.
- [ ] Claim boundaries are acceptable.
