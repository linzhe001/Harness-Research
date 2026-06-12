---
schema_version: "0.1"
page_id: "site_modes"
title: "Site Modes"
kind: "concept"
audience: ["operator", "agent", "maintainer"]
source_type: "hand_authored"
source_path: "workflow_handbook/pages/site_modes.md"
source_of_truth: true
status: "current"
summary: "Separates the static GitHub Pages handbook view from any future local live service with terminal or rebuild APIs."
nav:
  section: "operate"
  position: 35
canonical_sources:
  - path: "workflow_handbook/Workflow_Operator_Handbook.md"
    role: "aggregate_source"
  - path: "workflow_handbook/pages/04_markdown_to_html_preview_chain.md"
    role: "aggregate_source"
  - path: "tooling/evidence/build_docs_site.py"
    role: "tooling"
references:
  - "artifact:docs/_site/workflow_handbook"
  - "artifact:docs/_views/workflow_handbook_reference_index.json"
  - "source:tooling/evidence/build_docs_site.py"
  - "term:Gate Evidence"
  - "term:Human Approval"
html:
  render: true
  output_path: "docs/_site/workflow_handbook/pages/site_modes.html"
  preview_index_path: "docs/_views/workflow_handbook_reference_index.json"
---

# Site Modes

## Purpose

本页把 handbook HTML 的展示模式和可执行终端模式分开。当前仓库实现的是静态
HTML handbook renderer：`workflow_handbook/**` Markdown 通过
[[source:tooling/evidence/build_docs_site.py]] 渲染到
[[artifact:docs/_site/workflow_handbook]]，hover card 来自
[[artifact:docs/_views/workflow_handbook_reference_index.json]]。

## Model

```text
Archive / GitHub Pages mode
  workflow_handbook/**/*.md
    -> reference preview index
    -> docs/_site/workflow_handbook/**
    -> static file or GitHub Pages
    -> read-only handbook

Local live mode
  same generated static HTML
    -> localhost service, if implemented
    -> optional rebuild API / terminal API / WebSocket
    -> local-only workflow cockpit
```

Archive mode must work without a backend. Links and hover previews are built
from local JSON emitted at render time; the browser should not need runtime
fetches to read handbook references.

Local live mode is a separate boundary. If Harness later adds a terminal drawer
or live rebuild controls, that service must run on localhost or another
authenticated operator-controlled host. It is not a GitHub Pages feature and it
must not make generated HTML itself capable of writing files, starting shells,
or approving workflow decisions.

## Boundaries

- GitHub Pages is suitable for the read-only handbook, workflow map, generated
  reference pages, and static hover previews.
- GitHub Pages must not be treated as a PTY host, tmux manager, local filesystem
  writer, secret resolver, or agent profile switcher.
- A local live service may serve the same static files, but terminal/session
  control belongs behind explicit localhost security, origin checks, and
  operator-controlled secrets.
- Hover previews are reading aids. They are not [[term:Gate Evidence]],
  [[term:Human Approval]], or source-of-truth Markdown.
- Generated files under `docs/_site/**` and `docs/_views/**` remain
  tooling-owned outputs.

## Common Confusions

- A page being visible on GitHub Pages does not mean a workflow Stage completed.
- A hover card showing a Skill, Stage, Term, or Artifact does not prove that a
  gate ran.
- A future terminal pane should attach to a local service, not to a public
  static page by default.
- Buying a domain is optional for static publication; it does not replace the
  need for a backend if terminal control is required.

## Related Pages

- [[page:markdown_to_html_preview_chain|Markdown To HTML Preview Chain]]
- [[page:hooks_permissions_model|Hooks And Permissions Model]]
- [[page:evidence_approval_model|Evidence And Approval Model]]
