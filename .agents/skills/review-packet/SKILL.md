---
name: review-packet
description: Build concise human review packets for dynamic-context contracts, protocol readiness, and release gates.
---

# Review Packet

## References

Read these first:
- `../../../.agents/references/context-layering-policy.md`
- `../../../.agents/references/contract-gating-rule.md`
- `../../../.agents/references/evidence-chain-rule.md`
- `../../../.agents/references/lesson-quality-rule.md`
- `../../../.agents/references/language-policy.md`

Tooling:
- `../../../tooling/evidence/check_dynamic_context.py`
- `../../../tooling/evidence/build_review_packet.py`
- `../../../tooling/evidence/approve_contract.py`
- `../../../tooling/evidence/check_context_gates.py`
- `../../../tooling/evidence/check_protocol_drift.py`
- `../../../tooling/evidence/check_docchain_gates.py`

## When To Use

Use this skill when the operator needs to approve, revise, or reject a dynamic
context gate without reading every source document:

- WF5 Evaluation Contract readiness
- WF10 auto-iteration readiness
- WF11 final experiment readiness
- WF12 release claim readiness
- status review after a major evidence/protocol update

## Required Work

1. Choose the target stage: `status`, `wf5`, `wf10`, `wf11`, or `wf12`.
2. Run:

   ```bash
   python tooling/evidence/check_dynamic_context.py --workspace-root . --stage <stage> --review-packet
   ```

3. If you only need to rebuild a packet from already-known gate results, run
   `python tooling/evidence/build_review_packet.py --workspace-root . --stage <stage>`.
4. Report the generated packet path under `.evidence/review_packets/`.
5. Summarize only:
   - requested decision
   - gate pass/fail summary
   - blocking items
   - open questions
   - exact human action needed
6. If and only if the current conversation contains explicit human approval for
   a specific contract, record approval with:

   ```bash
   python tooling/evidence/approve_contract.py --workspace-root . \
     --contract <contract_key> \
     --approved-by "<human reviewer>" \
     --approval-source "<review_packet_path_or_conversation_reference>"
   ```

   Then re-run `check_dynamic_context.py --stage <stage> --review-packet` and
   report the new gate result.

## Output Rules

- Do not mark any contract as approved from the packet alone.
- Approval requires explicit human approval in the current conversation.
- If the packet reports blockers, propose the smallest next fix: evidence,
  protocol review, docchain compilation, or contract revision.
