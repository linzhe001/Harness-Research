---
name: auto-paper-citation
description: Run the auto-paper citation phase. Use to segment claims, build a citation support bank, grade support strength, map claims to citations, and route unsupported claims.
argument-hint: "[artifact dir]"
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
---

# Auto Paper Citation

<instructions>
1. Read `claim_register.md`, bibliography files, research artifacts, and local
   references.
2. Grade support as `strong`, `partial`, `background`, `limiting`,
   `metadata_only`, or `unsupported`.
3. Treat `metadata_only` as bibliographic metadata, not claim support.
4. Write `citation_support_bank.md`, `claim_citation_map.md`, and optional
   `citation_audit_report.md`.
5. Route weak core-claim support back to citation or argument before patching.
</instructions>
