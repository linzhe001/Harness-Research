# Execution Readiness Packet

Status: draft

## Purpose

Summarize candidate execution inputs gathered during Grill. Keep exact
local/private values in `.workflow_supervisor/readiness.json`; redact sensitive
values here.

## Candidate Inputs

| Input | Redacted Value | Verification Status | Verification Command |
| --- | --- | --- | --- |
| dataset_root | pending | candidate | not run |
| baseline_cache | pending | candidate | not run |
| budget | pending | candidate | not run |

## Verified Facts

- None yet.

## Open Questions

- Which local paths must be verified before `prepare`?
- Which approvals are required before unattended WF10?

## Boundary Notes

This packet is not a Review Packet and not Approval Evidence. Supervisor
readiness preflight must verify candidate inputs before using them.
