# Auto Paper Argument

<instructions>
1. Use research artifacts and operator-approved boundaries as sources.
   Read `.claude/shared/research-supervision/idea-evaluation.md`,
   `paper-writing-layouts.md`, and `case-patterns.md` before locking claims.
2. Write `confirmed_motivation.md` with field need, bottleneck, proposed move,
   decisive evidence, implication, boundary, paper type, dominant improvement
   axis, and claims to avoid.
3. Write `claim_register.md` with claim ID, location, text, evidence source,
   citation need, verb strength, scope limit, and reviewer risk.
4. Run `.agents/skills/auto-paper/scripts/claim_register_check.py auto_paper_output/<paper_id>/claim_register.md`;
   rerun it with `--citation-bank` after citation support exists.
5. Return `USER_GATE` when central claims or boundaries need operator input.
6. Do not patch LaTeX.
7. Report a Gate ledger entry with commands run, artifacts written, claim-gate
   result, any `USER_GATE` or `NOT_RUN` reason, and the next owner before
   handoff.
</instructions>
