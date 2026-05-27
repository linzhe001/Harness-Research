---
name: auto-paper-argument
description: Run the auto-paper argument phase. Use to define central tension, core contribution, allowed novelty, claim boundaries, claim register, claims to avoid, and motivation surface map.
argument-hint: "[artifact dir]"
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
---

# Auto Paper Argument

<instructions>
1. Use research artifacts and operator-approved boundaries as sources.
2. Write `confirmed_motivation.md` with field need, bottleneck, proposed move,
   decisive evidence, implication, boundary, and claims to avoid.
3. Write `claim_register.md` with claim ID, location, text, evidence source,
   citation need, verb strength, scope limit, and reviewer risk.
4. Return `USER_GATE` when central claims or boundaries need operator input.
5. Do not patch LaTeX.
</instructions>
