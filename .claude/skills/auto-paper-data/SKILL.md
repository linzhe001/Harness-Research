---
name: auto-paper-data
description: Run the optional auto-paper data, code, ethics, and reproducibility branch. Use for data availability, code availability, ethics boundaries, FAIR metadata, and reproducibility statements.
argument-hint: "[artifact dir]"
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
---

# Auto Paper Data

<instructions>
1. Read verified project facts about datasets, code release, licenses, access
   restrictions, ethics boundaries, configs, seeds, checkpoints, and commands.
2. Write `data_availability_statement.md`, `code_availability_statement.md`,
   `reproducibility_checklist.md`, and `ethics_boundary.md` under
   `auto_paper_output/<paper_id>/`.
3. Do not invent public URLs, repository status, licenses, IRB/ethics approval,
   data availability, or reproducibility guarantees.
4. Record unclear availability or ethics facts as `USER_GATE` items.
5. Route new evidence claims back to argument/citation/harden.
</instructions>
