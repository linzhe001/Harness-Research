---
name: auto-paper-patch
description: Run the auto-paper patch phase. Use as the only branch that may edit LaTeX or bibliography files from latex_patch_plan.md and record patch_ledger.md with guard results.
argument-hint: "[unit id or artifact dir]"
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
---

# Auto Paper Patch

<instructions>
1. Read `latex_patch_plan.md`, `writing_rationale_matrix.md`, claim register,
   citation bank, and current draft files before editing.
2. Patch one section or contiguous unit group at a time.
3. Preserve labels, refs, citation keys, graphics paths, equations,
   environments, macros, and venue wrappers unless explicitly planned.
4. Do not add unbanked citation keys or strengthen unsupported claims.
5. Write `patch_ledger.md` and run LaTeX guard or compile checks when
   available.
</instructions>
