---
name: auto-paper-response
description: Run the optional auto-paper reviewer-response branch. Use for rebuttals, revision response letters, reviewer comment maps, response strategy, and revision commitment registers.
argument-hint: "[artifact dir or reviewer comments]"
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
---

# Auto Paper Response

<instructions>
1. Read reviewer comments, current claim/citation artifacts, patch ledger, and
   operator-approved commitments.
2. Write `reviewer_comment_map.md`, `response_strategy.md`,
   `revision_commitment_register.md`, and `response_letter.md` under
   `auto_paper_output/<paper_id>/`.
3. Do not promise unfinished experiments, unavailable releases, unsupported
   citations, or scope changes.
4. Route new or broadened claims back to argument/citation/harden.
5. Return `USER_GATE` when a response depends on operator approval.
</instructions>
