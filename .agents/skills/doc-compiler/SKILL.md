---
name: doc-compiler
description: Compile current project documents from explicit evidence chains. Use when refreshing contract, fact, protocol, or release docs that need auditable evidence.
---

# Doc Compiler

## References

Read these first:
- `../../../.agents/references/context-layering-policy.md`
- `../../../.agents/references/research-invariants.md`
- `../../../.agents/references/evidence-chain-rule.md`
- `../../../.agents/references/documentation-evidence-rule.md`
- `../../../.agents/references/documentation-style.md`
- `../../../.agents/references/language-policy.md`
- `../../../schemas/evidence_chain.schema.json`
- `../../../schemas/source_manifest.schema.json`
- `../../../schemas/doc_audit.schema.json`
Tooling:
- `../../../tooling/evidence/compile_doc.py`
- `../../../tooling/evidence/validate_docchain.py`
- `../../../tooling/evidence/check_docchain_gates.py`

## When To Use

Use this skill to create or refresh current docs under:

- `docs/10_contract/`
- `docs/20_facts/`
- `docs/35_protocol/`
- release docs or claim-bearing docs

Legacy stage reports may still use their local templates, but should migrate to
this compiler when their claims become contract or release material.

## Required Work

1. Resolve the target document path and compute a stable `doc_id` by replacing
   path separators with `__` and dropping the `.md` suffix.
2. Freeze source git context before generated header/docchain writes: commit,
   branch, dirty status, and patch path when dirty.
3. Build a read plan and re-read the current source artifacts from disk.
4. Compile or refresh concise Markdown using fact markers such as `[F:id]` and
   `[U:id]`; the tool should update `Evidence chain`, `Evidence audit`, and
   `Audit result` headers for the current build.
5. Extract atomic facts, unresolved questions, and decisions from the updated
   Markdown.
6. Write `.evidence/chains/{doc_id}/{build_id}/evidence_chain.json`.
7. Write the matching `source_manifest.json` with the updated Markdown hash.
8. Write `doc_audit.json` and update `.evidence/index.json`.
9. For contract docs, review and upgrade fact confidence and support relations;
   v0 `context_only` support is not enough for readiness.
10. Only treat the current Markdown as ready when audit and docchain gates pass.
   If audit fails, keep a
   draft and report unsupported claims.

When shell access is available, use `python tooling/evidence/compile_doc.py`
for the v0 chain generation and `python tooling/evidence/validate_docchain.py`
for validation. The v0 compiler records explicit sources and markers, updates
evidence headers, and refreshes `.evidence/index.json`; it does not prove
semantic support automatically.
Use `python tooling/evidence/check_docchain_gates.py --workspace-root .` before
declaring current contract/fact/protocol docs ready.
Report the compile, validation, and docchain-gate commands in a gate ledger.

## Docs Site Handoff

After the current Markdown is finalized for this turn or stage and docchain
gates have passed, invoke `$docs-site` to refresh `docs/_views/**` and
`docs/_site/**`, or report `docs_site_render_or_NOT_RUN` with the reason. This
is a durable-boundary handoff, not a per-keystroke or temporary-draft action.

## Output Rules

- Markdown is for human review; JSON is for audit.
- Do not include raw logs or long excerpts in Markdown.
- Put unsupported or contradictory claims under Open Questions.
- Contract docs need explicit supporting evidence, not only `context_only`
  source records from the v0 compiler.
- Contract docs must remain `Status: draft` unless the user explicitly approves
  them in the current conversation.
- Treat template wording as structure-only; localize narrative text according to
  `../../../.agents/references/language-policy.md`.

## Execution Rule

Do not replace this with generic documentation writing. The evidence chain,
source manifest, and audit file are required outputs for compiled current docs.
If any required evidence command is not run, report `NOT_RUN` and keep the
document in draft/review status.
