---
schema_version: "0.1"
page_id: "markdown_to_html_preview_chain"
title: "Markdown To HTML Preview Chain"
kind: "concept"
audience: ["operator", "agent", "maintainer"]
source_type: "hand_authored"
source_path: "workflow_handbook/pages/04_markdown_to_html_preview_chain.md"
source_of_truth: true
status: "current"
summary: "Explains how handbook Markdown, framework references, and HTML hover previews stay separated from project Conclusion Evidence."
nav:
  section: "evidence"
  position: 40
canonical_sources:
  - path: "workflow_handbook/Workflow_Operator_Handbook.md"
    role: "aggregate_source"
  - path: "tooling/evidence/build_docs_site.py"
    role: "tooling"
references:
  - "artifact:docs/_views/workflow_handbook_reference_index.json"
  - "artifact:docs/_site/workflow_handbook"
  - "artifact:.evidence/index.json"
  - "page:site_modes"
  - "skill:docs-site"
  - "source:tooling/evidence/build_docs_site.py"
  - "term:Conclusion Evidence"
  - "term:Evidence Chain"
  - "term:Gate Evidence"
html:
  render: true
  output_path: "docs/_site/workflow_handbook/pages/04_markdown_to_html_preview_chain.html"
  preview_index_path: "docs/_views/workflow_handbook_reference_index.json"
---

# Markdown To HTML Preview Chain

## Purpose

本页说明 handbook HTML 的生成边界：`workflow_handbook/**` Markdown 是
framework handbook source，[[artifact:docs/_site/workflow_handbook]] 是
generated HTML view，[[artifact:docs/_views/workflow_handbook_reference_index.json]]
是 framework reference preview index。

## Model

```text
workflow_handbook/**/*.md
  -> build_workflow_handbook_reference_index.py
  -> docs/_views/workflow_handbook_reference_index.json
  -> build_docs_site.py --reference-mode workflow-handbook
  -> docs/_site/workflow_handbook/**
```

For CLI validation, `--json` prints a concise success summary. Use
`--json-full` only when a failing or suspicious render needs the full generated
index or manifest in stdout.

项目 [[term:Conclusion Evidence]] 链路仍然走 `.evidence/**` 和
[[artifact:.evidence/index.json]]。Handbook hover cards 只解释 framework
Stage、Skill、Artifact、Term、Source 和 Page。

Handbook hover cards use build-time preview data instead of runtime fetches.
That keeps the generated handbook readable as a local static file or GitHub
Pages site. Any terminal, rebuild API, or agent session control belongs to a
separate local live service boundary.

## Boundaries

- [[skill:docs-site]] 渲染 HTML view，但不把 HTML 变成 source of truth。
- [[source:tooling/evidence/build_docs_site.py]] 负责 renderer 行为。
- `docs/_views/workflow_handbook_reference_index.json` 不是
  [[term:Evidence Chain]]，也不是 human approval artifact。
- `docs/_site/workflow_handbook/**` 不应被手写；它由 renderer 重新生成。
- Static handbook HTML 不应包含 PTY、tmux、agent profile switching、secret
  resolution 或 filesystem write capability。

## Common Confusions

- Framework reference preview 只解释 Harness workflow source，不证明项目 claim。
- [[term:Gate Evidence]] 是命令、测试、review 或 approval check 的执行记录；
  hover preview 本身不是 Gate Evidence。
- [[artifact:.evidence/index.json]] 属于项目 docchain tooling；handbook reference
  index 属于 framework docs browsing。
- GitHub Pages 可以展示 generated handbook view，但不能运行 local terminal
  service。

## Related Pages

- [[page:site_modes|Site Modes]]
- [[skill:docs-site]]
- [[term:Conclusion Evidence]]
- [[term:Evidence Chain]]
- [[term:Gate Evidence]]
