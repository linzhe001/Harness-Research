---
name: docs-site
description: Render source Markdown project docs into human-readable HTML under docs/_site, with Evidence Chain hover previews from docs/_views/evidence_preview_index.json. Use after stable Markdown docs are finalized, before human review or handoff, or when explicitly rebuilding the human docs site.
---

# Docs Site

## References

Read these first:
- `../../../.agents/references/evidence-chain-rule.md`
- `../../../.agents/references/documentation-style.md`
- `../../../.agents/references/language-policy.md`
- `../../../.agents/references/ubiquitous-language.md`
- `../../../schemas/docs_site_manifest.schema.json`
- `../../../schemas/evidence_preview_index.schema.json`
- `../../../docs/` source Markdown when present
- `../../../.evidence/index.json` when present

Tooling:
- `../../../tooling/evidence/build_evidence_preview_index.py`
- `../../../tooling/evidence/build_docs_site.py`
- `../../../tooling/evidence/validate_docchain.py`

## When To Use

Use this skill only at a durable documentation boundary:

- after `$doc-compiler` has refreshed a contract, fact, protocol, or claim-bearing Markdown doc and its docchain gates are complete
- after a stage skill has finished writing stable human docs such as `docs/Technical_Spec.md`, `docs/Implementation_Roadmap.md`, `docs/20_facts/Codebase_Map.md`, `docs/Validate_Run_Report.md`, or a Conclusion Evidence table
- before human review, handoff, or final response when `docs/_site/**` should reflect the current Markdown
- when the operator explicitly asks to rebuild the human docs site

Do not run this skill after every temporary Markdown edit. Run it after the
Markdown source is accepted for the current turn, stage, or review packet. If
the Markdown is still a draft in progress, leave the HTML stale and report
`NOT_RUN` with the reason.

## Required Work

1. Treat Markdown as source of truth. Do not edit source Markdown during this skill.
2. If the Markdown is claim-bearing and the required Evidence Chain was not
   compiled, stop or report `compile_doc_or_NOT_RUN`; do not render unsupported
   claims as if they were ready.
   Evidence marker preview cards are available only for markers recorded in
   `.evidence/index.json`; claim-bearing docs that contain `[F:*]`, `[U:*]`,
   `[D:*]`, `[L:*]`, or `[E:*]` markers should be compiled first when the
   operator expects hover previews or click-through source links.
3. If `.evidence/index.json` exists, run:
   `python tooling/evidence/build_evidence_preview_index.py --workspace-root .`
4. Render the human docs site with:
   `python tooling/evidence/build_docs_site.py --workspace-root .`
   Use `--json` for concise success summaries and `--json-full` only when
   debugging the full manifest.
5. Validate generated JSON artifacts when present:
   - `docs/_views/evidence_preview_index.json` against `schemas/evidence_preview_index.schema.json`
   - `docs/_site/manifest.json` against `schemas/docs_site_manifest.schema.json`
   Then inspect at least one rendered marker for a preview card and a non-empty
   click target when the source marker has Evidence Chain preview data.
6. Report a Gate ledger with the preview-index command, render command,
   validation result, reason, and artifacts.

## Output Rules

- Keep generated view data under `docs/_views/**`.
- Keep generated HTML under `docs/_site/**`.
- Do not write generated HTML into `.evidence/**`.
- Do not hand-copy Markdown into HTML; use the renderer.
- HTML is a human-readable view, not an Approved Contract, source artifact, or
  replacement for the Markdown and Evidence Chain.
