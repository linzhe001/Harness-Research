---
name: auto-paper-patch
description: Run the auto-paper patch phase. Use to produce bounded LaTeX or bibliography diffs from latex_patch_plan.md, record patch_ledger.md with guard results, and prepare apply-ready manuscript patches.
argument-hint: "[unit id or artifact dir]"
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
---

# Auto Paper Patch

<instructions>
1. Read `latex_patch_plan.md`, `writing_rationale_matrix.md`, claim register,
   citation bank, and current draft files before editing.
2. Produce one section or contiguous unit group at a time.
3. Preserve labels, refs, citation keys, graphics paths, equations,
   environments, macros, and venue wrappers unless explicitly planned.
4. Do not add unbanked citation keys or strengthen unsupported claims.
5. Default to writing `latex_patch.diff` or `patches/<unit_id>.diff` under
   `auto_paper_output/<paper_id>/`; direct `.tex` or `.bib` edits require
   explicit operator authorization and a write scope that permits the target.
6. Write `patch_ledger.md` and run LaTeX guard or compile checks on an applied
   temporary copy when available.
</instructions>
