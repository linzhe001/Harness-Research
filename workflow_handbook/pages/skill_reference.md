---
schema_version: "0.1"
page_id: "skill_reference"
title: "Skill Reference"
kind: "reference"
audience: ["operator", "agent", "maintainer"]
source_type: "hand_authored"
source_path: "workflow_handbook/pages/skill_reference.md"
source_of_truth: true
status: "current"
summary: "Entry point for detailed Skill Contract pages."
nav:
  section: "reference"
  position: 40
canonical_sources:
  - path: "schemas/skill_contracts.json"
    role: "skill_contract"
references:
  - "skill:orchestrator"
  - "skill:docs-site"
  - "skill:iterate"
  - "term:Skill Contract"
html:
  render: true
  output_path: "docs/_site/workflow_handbook/pages/skill_reference.html"
  preview_index_path: "docs/_views/workflow_handbook_reference_index.json"
---

# Skill Reference

## Source Of Truth

Skill detail pages are generated from `schemas/skill_contracts.json` and `.agents/skills/*/SKILL.md`.

## Fields Or Paths

- `required_read_set`: files a Skill must read before writes.
- `write_scope.allowed_paths`: paths a Skill may write.
- `required_actions`: checks or reports expected before final handoff.
- `forbidden_actions`: operations the Skill must not perform.

## Validation

Run `python tooling/codex_hooks/check_contracts.py --workspace-root .` and focused tests after changing Skill Contracts or generator behavior.

## Related References

- [[skill:orchestrator]]
- [[skill:docs-site]]
- [[skill:iterate]]
- [[term:Skill Contract]]

