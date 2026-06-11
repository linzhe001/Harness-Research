# Workflow Handbook HTML Rendering Plan

Status: draft implementation plan

## 1. 目标

把 `workflow_handbook/` 从两个长 Markdown 阅读文件，升级成一个
source-backed handbook wiki，同时保持当前的 source-of-truth 边界：

- `workflow_handbook/Workflow_Operator_Handbook.md` 仍是 AI 和维护者可读的
  完整叙事入口。
- `workflow_handbook/Workflow_Stage_Cards.md` 仍是从
  `schemas/skill_contracts.json` 生成的日常 Stage / Skill 速查入口。
- `workflow_handbook/pages/**`、`workflow_handbook/stages/**`、
  `workflow_handbook/skills/**` 用于后续拆分和生成页面。
- `docs/_site/workflow_handbook/**` 是人类可读 HTML view，不是新的
  source of truth。
- `docs/_views/workflow_handbook_reference_index.json` 是 framework
  reference hover preview index，不是项目 Conclusion Evidence。

目标不是引入一个外部文档框架，而是把成熟文档系统的结构抽象成
Harness 自己的 schema、renderer 和 validation flow。

## 2. 参考模型

这个计划组合五类成熟文档实践：

| 参考 | 在 Harness 中的用途 | 参考链接 |
| --- | --- | --- |
| Diataxis | 定义页面类型：concept、how-to、reference、explanation，避免一个页面同时承担太多任务。 | `https://diataxis.fr/start-here/` |
| The Good Docs Project | 借鉴 how-to、concept、reference、API reference 的章节模板。 | `https://www.thegooddocsproject.dev/template/how-to`, `https://www.thegooddocsproject.dev/template/api-reference` |
| Docusaurus | 借鉴 frontmatter、sidebar、page id、sidebar position、generated index 的元数据模型。 | `https://docusaurus.io/docs/sidebar`, `https://docusaurus.io/docs/api/plugins/%40docusaurus/plugin-content-docs` |
| Material for MkDocs | 借鉴 tooltip、annotation、glossary、instant preview 的 hover preview 交互。 | `https://squidfunk.github.io/mkdocs-material/reference/tooltips/`, `https://squidfunk.github.io/mkdocs-material/reference/annotations/` |
| Antora | 借鉴 content source 和 navigation registration 分离的组织方式。 | `https://docs.antora.org/antora/latest/navigation/` |

Harness-specific mapping:

- Diataxis 决定 `kind`。
- The Good Docs Project 决定每类页面应该有哪些章节。
- Docusaurus 决定 frontmatter 和 navigation metadata。
- Material for MkDocs 决定 hover preview 的行为模型。
- Antora 决定 source content 和 navigation config 分离。

## 3. 不变边界

### 3.1 Source Of Truth

这些文件是 handbook 的 source inputs：

```text
workflow_handbook/**/*.md
schemas/skill_contracts.json
.agents/skills/*/SKILL.md
.claude/skills/*/SKILL.md
.agents/references/*.md
.claude/shared/*.md
tooling/codex_hooks/README.md
tooling/evidence/*.py
schemas/*.schema.json
tooling/.tests/*.py
```

这些文件是 generated views：

```text
docs/_site/workflow_handbook/**
docs/_site/workflow_handbook/manifest.json
docs/_views/workflow_handbook_reference_index.json
```

规则：

- Markdown source 保留给 AI、维护者和 diff review。
- HTML view 保留给人类阅读和浏览。
- HTML 不替代 Markdown、Skill Contract、Gate Evidence、Approval Evidence 或
  Evidence Chain。
- 不把 generated HTML 写入 `workflow_handbook/**`。

### 3.2 Conclusion Evidence 和 Framework Reference 的区别

项目 Conclusion Evidence 链路：

```text
project source artifacts
  -> compile_doc.py
  -> .evidence/chains/**
  -> .evidence/index.json
  -> build_evidence_preview_index.py
  -> docs/_views/evidence_preview_index.json
  -> docs/_site/**
```

Workflow handbook reference 链路：

```text
framework source files
  -> build_workflow_handbook_reference_index.py
  -> docs/_views/workflow_handbook_reference_index.json
  -> build_docs_site.py --source-root workflow_handbook
  -> docs/_site/workflow_handbook/**
```

这两条链路不能混用：

- `.evidence/**` 只用于项目 Claim、Current Facts、Protocol、Contract 和 release
  claim 的 Evidence Chain。
- `workflow_handbook_reference_index.json` 只用于解释 framework 本身的
  Stage、Skill、Artifact、Term、Source 和 Page。
- framework hover preview 不是 Conclusion Evidence，不是 Gate Evidence，
  也不是 Human Approval。

### 3.3 Existing Renderer Boundary

`tooling/evidence/build_docs_site.py` 当前已经支持：

```text
--source-root
--output-root
--preview-index
```

但它还缺少：

```text
--nav-config
--site-title
[[...]] framework reference parsing
workflow_handbook_reference_index.json hover card support
handbook-specific page metadata in manifest
```

所以初期可以 dry-run 或基础渲染，但最终 handbook HTML 必须等这些能力补齐后
才算完成。

## 4. 目标目录结构

最终 source tree：

```text
workflow_handbook/
  Workflow_Operator_Handbook.md
  Workflow_Stage_Cards.md
  config/
    navigation.json
  pages/
    00_overview.md
    01_workflow_model.md
    02_state_and_artifacts.md
    03_evidence_approval_and_docchain.md
    04_markdown_to_html_preview_chain.md
    05_hooks_permissions_and_contracts.md
    06_coding_discipline_and_codebase_map.md
    07_auto_iterate.md
    08_operator_playbooks.md
    09_maintenance.md
  stages/
    wf0_init.md
    wf1_survey_idea.md
    wf2_idea_debate.md
    wf3_refine_idea.md
    wf4_data_prep.md
    wf5_baseline_repro.md
    wf6_refine_arch.md
    wf7_build_plan.md
    wf8_code_expert.md
    wf9_validate_run.md
    wf10_iterate.md
    wf11_final_exp.md
    wf12_release.md
  skills/
    docs-site.md
    code-debug.md
    code-expert.md
    harness-maintenance.md
    iterate.md
    ...
  plans/
    HTML_Rendering_Handbook_Plan.md
```

Ownership:

| Path | Owner | Rule |
| --- | --- | --- |
| `Workflow_Operator_Handbook.md` | hand-authored or assembled aggregate | Daily full narrative entrypoint. |
| `Workflow_Stage_Cards.md` | `generate_stage_cards.py` | Generated from `schemas/skill_contracts.json`; no manual fact edits. |
| `pages/**` | hand-authored | Concept/how-to/playbook pages. |
| `stages/**` | generator | Generated or assembled from stage metadata and Skill Contracts. |
| `skills/**` | generator | Generated from Skill Contracts and skill frontmatter. |
| `config/navigation.json` | hand-authored initially | Validated navigation source. |
| `plans/**` | hand-authored | Planning only; not a daily operator entrypoint. |
| `docs/_views/**` | tooling | Generated preview/index data. |
| `docs/_site/**` | `$docs-site` tooling | Generated HTML view. |

## 5. Page Kind 模型

每个 split page 必须声明一个 `kind`。`kind` 决定页面结构、验证规则和导航
表现。

| `kind` | 用户问题 | 必须章节 |
| --- | --- | --- |
| `overview` | 这个系统是什么，我从哪里开始？ | Purpose, Mental Model, Start Here, Related Pages |
| `concept` | 为什么这个 workflow 规则存在？ | Purpose, Model, Boundaries, Common Confusions, Related Pages |
| `how_to` | 我如何完成一个具体操作？ | Goal, Prerequisites, Steps, Expected Outputs, Gates, Troubleshooting |
| `reference` | 精确字段、路径、规则是什么？ | Source Of Truth, Fields Or Paths, Validation, Related References |
| `playbook` | 遇到某个真实场景时怎么做？ | Scenario, Decision Inputs, Procedure, Gate Ledger, Recovery |
| `stage` | 一个 WF stage 怎么运行？ | Purpose, Inputs, Outputs, Required Reads, Gates, Exit Condition |
| `skill` | 一个 Skill 的行为边界是什么？ | Purpose, Triggers, Can Write, Must Read, Must Prove, Cannot Do |
| `artifact` | 一个文件或目录由谁拥有？ | Purpose, Owner, Source Or View, Update Trigger, Related References |
| `term` | 一个 workflow term 的准确定义是什么？ | Definition, Use When, Do Not Confuse With, Related Terms |
| `maintenance` | 维护者如何安全修改 framework？ | Scope, Required Reads, Change Steps, Validation, Handoff |
| `plan` | 后续实施如何推进？ | Purpose, Scope, Design, Slices, Validation, Open Decisions |

验证策略：

1. JSON Schema 验证 frontmatter 的字段类型。
2. Python validator 按 `kind` 检查 required headings。
3. Generator 生成的 `stage` / `skill` 页面还要和
   `schemas/skill_contracts.json` 对齐。

## 6. Markdown Frontmatter 规范

所有 split source pages 都应使用 frontmatter。root aggregate 文件可以在
assembler 实现前暂时不强制。

示例：

```yaml
---
schema_version: "0.1"
page_id: "workflow_model"
title: "Workflow Model"
kind: "concept"
audience: ["operator", "agent"]
source_type: "hand_authored"
source_path: "workflow_handbook/pages/01_workflow_model.md"
source_of_truth: true
status: "current"
summary: "Explains the core Harness workflow primitives and stage flow."
nav:
  section: "workflow"
  position: 10
canonical_sources:
  - path: "workflow_handbook/Workflow_Operator_Handbook.md"
    role: "aggregate_source"
  - path: ".agents/references/workflow-guide.md"
    role: "framework_rule"
references:
  - "stage:WF10"
  - "skill:iterate"
  - "term:Gate Evidence"
html:
  render: true
  output_path: "docs/_site/workflow_handbook/pages/01_workflow_model.html"
  preview_index_path: "docs/_views/workflow_handbook_reference_index.json"
---
```

字段语义：

| Field | Meaning |
| --- | --- |
| `schema_version` | Page metadata schema version. |
| `page_id` | Stable page identity used by navigation and `[[page:*]]`. |
| `title` | Human display title. |
| `kind` | Page Kind from section 5. |
| `audience` | Intended readers: `operator`, `agent`, `maintainer`, `reviewer`. |
| `source_type` | `hand_authored`, `generated`, or `assembled`. |
| `source_path` | Markdown source path. |
| `source_of_truth` | Whether this page is itself a source, not generated view. |
| `status` | `draft`, `current`, `generated`, or `superseded`. |
| `summary` | Short preview summary. |
| `nav` | Navigation section and sort position. |
| `canonical_sources` | Source files that justify this page. |
| `references` | Explicit `[[...]]` references used or expected by the page. |
| `html` | Render behavior and output paths. |

## 7. Cross-Link 和 Hover Preview 语法

Markdown 内使用稳定 wiki-style references：

```text
[[stage:WF10]]
[[skill:docs-site]]
[[artifact:docs/_site]]
[[artifact:.evidence/index.json]]
[[term:Evidence Chain]]
[[source:schemas/skill_contracts.json#docs-site]]
[[page:workflow_model]]
```

允许 display label：

```text
[[skill:docs-site|HTML rendering skill]]
```

Reference prefixes：

| Prefix | Target | HTML behavior |
| --- | --- | --- |
| `stage:` | Generated Stage page | Link to `workflow_handbook/stages/*.html`; hover stage summary. |
| `skill:` | Generated Skill page | Link to `workflow_handbook/skills/*.html`; hover Skill Contract summary. |
| `artifact:` | Artifact reference entry | Link to artifact page or glossary entry; hover owner/source/view status. |
| `term:` | Ubiquitous Language term | Link to term entry; hover definition and confusion boundary. |
| `source:` | Framework source file or anchor | Link to source reference page or repository path; hover excerpt. |
| `page:` | Handbook page id | Link to page; hover page summary. |

Hover preview card should include:

```text
title
kind
summary/body
truth_status
owner
source_paths
related_refs
```

Preview content must be short and directly grounded in framework source files.
Long excerpts should be truncated and marked with `truncated: true`.

## 8. Schema 文件

后续实现应新增三个 schema：

```text
schemas/workflow_handbook_page.schema.json
schemas/workflow_handbook_nav.schema.json
schemas/workflow_handbook_reference_index.schema.json
```

`schemas/docs_site_manifest.schema.json` 可以继续作为通用 site manifest
schema。handbook-specific metadata 先由 `workflow_handbook_page.schema.json`
和 `workflow_handbook_nav.schema.json` 验证。

### 8.1 `schemas/workflow_handbook_page.schema.json`

Purpose: validate parsed page frontmatter plus basic metadata.

Draft:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Workflow Handbook Page",
  "type": "object",
  "required": [
    "schema_version",
    "page_id",
    "title",
    "kind",
    "audience",
    "source_type",
    "source_path",
    "source_of_truth",
    "status",
    "summary",
    "nav",
    "canonical_sources",
    "references",
    "html"
  ],
  "properties": {
    "schema_version": {
      "type": "string",
      "enum": ["0.1"]
    },
    "page_id": {
      "type": "string",
      "pattern": "^[a-z0-9][a-z0-9_.-]*$"
    },
    "title": {
      "type": "string",
      "minLength": 1
    },
    "kind": {
      "type": "string",
      "enum": [
        "overview",
        "concept",
        "how_to",
        "reference",
        "playbook",
        "stage",
        "skill",
        "artifact",
        "term",
        "maintenance",
        "plan"
      ]
    },
    "audience": {
      "type": "array",
      "minItems": 1,
      "uniqueItems": true,
      "items": {
        "type": "string",
        "enum": ["operator", "agent", "maintainer", "reviewer"]
      }
    },
    "source_type": {
      "type": "string",
      "enum": ["hand_authored", "generated", "assembled"]
    },
    "source_path": {
      "type": "string",
      "pattern": "^workflow_handbook/.+\\.md$"
    },
    "source_of_truth": {
      "type": "boolean"
    },
    "status": {
      "type": "string",
      "enum": ["draft", "current", "generated", "superseded"]
    },
    "summary": {
      "type": "string",
      "minLength": 1
    },
    "nav": {
      "type": "object",
      "required": ["section", "position"],
      "properties": {
        "section": {
          "type": "string",
          "pattern": "^[a-z0-9][a-z0-9_-]*$"
        },
        "position": {
          "type": "integer",
          "minimum": 0
        }
      },
      "additionalProperties": false
    },
    "canonical_sources": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["path", "role"],
        "properties": {
          "path": {
            "type": "string",
            "minLength": 1
          },
          "role": {
            "type": "string",
            "enum": [
              "aggregate_source",
              "framework_rule",
              "skill_contract",
              "skill_source",
              "hook_source",
              "schema",
              "test",
              "tooling",
              "external_reference"
            ]
          },
          "anchor": {
            "type": ["string", "null"]
          }
        },
        "additionalProperties": false
      }
    },
    "references": {
      "type": "array",
      "uniqueItems": true,
      "items": {
        "$ref": "#/definitions/reference_id"
      }
    },
    "required_headings": {
      "type": "array",
      "items": {
        "type": "string",
        "minLength": 1
      }
    },
    "discovered_headings": {
      "type": "array",
      "items": {
        "type": "string",
        "minLength": 1
      }
    },
    "html": {
      "type": "object",
      "required": ["render", "output_path", "preview_index_path"],
      "properties": {
        "render": {
          "type": "boolean"
        },
        "output_path": {
          "type": ["string", "null"],
          "pattern": "^docs/_site/workflow_handbook/.+\\.html$"
        },
        "preview_index_path": {
          "type": ["string", "null"],
          "enum": [
            "docs/_views/workflow_handbook_reference_index.json",
            null
          ]
        }
      },
      "additionalProperties": false
    }
  },
  "definitions": {
    "reference_id": {
      "type": "string",
      "pattern": "^(stage|skill|artifact|term|source|page):[A-Za-z0-9_./:# -]+$"
    }
  },
  "additionalProperties": false
}
```

Semantic checks outside JSON Schema:

- `required_headings` must match the Page Kind table.
- `source_type: generated` pages must be reproducible by the generator.
- `source_of_truth: false` is allowed only for assembled or generated summaries.
- every `references[]` entry must exist in
  `workflow_handbook_reference_index.json` after the index builder runs.

### 8.2 `schemas/workflow_handbook_nav.schema.json`

Purpose: validate `workflow_handbook/config/navigation.json`.

Draft:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Workflow Handbook Navigation",
  "type": "object",
  "required": [
    "schema_version",
    "site_title",
    "source_root",
    "output_root",
    "preview_index_path",
    "sections"
  ],
  "properties": {
    "schema_version": {
      "type": "string",
      "enum": ["0.1"]
    },
    "site_title": {
      "type": "string",
      "minLength": 1
    },
    "source_root": {
      "type": "string",
      "enum": ["workflow_handbook"]
    },
    "output_root": {
      "type": "string",
      "enum": ["docs/_site/workflow_handbook"]
    },
    "preview_index_path": {
      "type": "string",
      "enum": ["docs/_views/workflow_handbook_reference_index.json"]
    },
    "sections": {
      "type": "array",
      "minItems": 1,
      "items": {
        "$ref": "#/definitions/nav_section"
      }
    }
  },
  "definitions": {
    "nav_section": {
      "type": "object",
      "required": ["id", "title", "kind", "position", "items"],
      "properties": {
        "id": {
          "type": "string",
          "pattern": "^[a-z0-9][a-z0-9_-]*$"
        },
        "title": {
          "type": "string",
          "minLength": 1
        },
        "kind": {
          "type": "string",
          "enum": [
            "overview",
            "workflow",
            "evidence",
            "reference",
            "playbook",
            "maintenance",
            "plans"
          ]
        },
        "position": {
          "type": "integer",
          "minimum": 0
        },
        "items": {
          "type": "array",
          "items": {
            "$ref": "#/definitions/nav_item"
          }
        }
      },
      "additionalProperties": false
    },
    "nav_item": {
      "type": "object",
      "required": ["page_id", "label", "source_path"],
      "properties": {
        "page_id": {
          "type": "string",
          "pattern": "^[a-z0-9][a-z0-9_.-]*$"
        },
        "label": {
          "type": "string",
          "minLength": 1
        },
        "source_path": {
          "type": "string",
          "pattern": "^workflow_handbook/.+\\.md$"
        },
        "generated": {
          "type": "boolean"
        },
        "children": {
          "type": "array",
          "items": {
            "$ref": "#/definitions/nav_item"
          }
        }
      },
      "additionalProperties": false
    }
  },
  "additionalProperties": false
}
```

Initial navigation example:

```json
{
  "schema_version": "0.1",
  "site_title": "Harness Workflow Handbook",
  "source_root": "workflow_handbook",
  "output_root": "docs/_site/workflow_handbook",
  "preview_index_path": "docs/_views/workflow_handbook_reference_index.json",
  "sections": [
    {
      "id": "start",
      "title": "Start",
      "kind": "overview",
      "position": 0,
      "items": [
        {
          "page_id": "operator_handbook",
          "label": "Operator Handbook",
          "source_path": "workflow_handbook/Workflow_Operator_Handbook.md",
          "generated": false
        },
        {
          "page_id": "stage_cards",
          "label": "Stage Reference",
          "source_path": "workflow_handbook/Workflow_Stage_Cards.md",
          "generated": true
        }
      ]
    }
  ]
}
```

Semantic checks outside JSON Schema:

- every `source_path` must exist;
- every `page_id` must be unique;
- every page with `html.render: true` should appear in navigation or be
  reachable from a navigation item;
- generated pages should not be hand-edited after generator support exists.

### 8.3 `schemas/workflow_handbook_reference_index.schema.json`

Purpose: validate generated framework reference hover preview data.

Draft:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Workflow Handbook Reference Index",
  "type": "object",
  "required": [
    "schema_version",
    "generated_at",
    "source_index_version",
    "source_roots",
    "entries",
    "links_by_doc"
  ],
  "properties": {
    "schema_version": {
      "type": "string",
      "enum": ["0.1"]
    },
    "generated_at": {
      "type": "string",
      "minLength": 1
    },
    "source_index_version": {
      "type": "string",
      "minLength": 1
    },
    "source_roots": {
      "type": "array",
      "items": {
        "type": "string",
        "minLength": 1
      }
    },
    "entries": {
      "type": "object",
      "additionalProperties": {
        "$ref": "#/definitions/reference_entry"
      }
    },
    "links_by_doc": {
      "type": "object",
      "additionalProperties": {
        "type": "array",
        "items": {
          "$ref": "#/definitions/doc_link"
        }
      }
    }
  },
  "definitions": {
    "reference_entry": {
      "type": "object",
      "required": [
        "ref",
        "kind",
        "title",
        "summary",
        "truth_status",
        "owner",
        "source_paths",
        "preview",
        "related_refs"
      ],
      "properties": {
        "ref": {
          "$ref": "#/definitions/reference_id"
        },
        "kind": {
          "type": "string",
          "enum": ["stage", "skill", "artifact", "term", "source", "page"]
        },
        "title": {
          "type": "string",
          "minLength": 1
        },
        "summary": {
          "type": "string",
          "minLength": 1
        },
        "truth_status": {
          "type": "string",
          "enum": [
            "source_of_truth",
            "generated_view",
            "runtime_state",
            "external_reference",
            "planned"
          ]
        },
        "owner": {
          "type": "string",
          "enum": [
            "operator",
            "orchestrator",
            "skill",
            "hook_runtime",
            "docs-site",
            "evidence_tooling",
            "auto_iterate_controller",
            "maintainer",
            "external"
          ]
        },
        "source_paths": {
          "type": "array",
          "minItems": 1,
          "items": {
            "$ref": "#/definitions/source_locator"
          }
        },
        "preview": {
          "$ref": "#/definitions/preview_card"
        },
        "related_refs": {
          "type": "array",
          "items": {
            "$ref": "#/definitions/reference_id"
          }
        },
        "last_validated_by": {
          "type": ["string", "null"]
        }
      },
      "additionalProperties": false
    },
    "source_locator": {
      "type": "object",
      "required": ["path", "role"],
      "properties": {
        "path": {
          "type": "string",
          "minLength": 1
        },
        "anchor": {
          "type": ["string", "null"]
        },
        "line": {
          "type": ["integer", "null"],
          "minimum": 1
        },
        "role": {
          "type": "string",
          "enum": [
            "skill_contract",
            "skill_source",
            "shared_rule",
            "schema",
            "tooling",
            "test",
            "handbook_page",
            "external_reference"
          ]
        }
      },
      "additionalProperties": false
    },
    "preview_card": {
      "type": "object",
      "required": ["title", "body", "format", "truncated"],
      "properties": {
        "title": {
          "type": "string",
          "minLength": 1
        },
        "body": {
          "type": "string",
          "minLength": 1
        },
        "format": {
          "type": "string",
          "enum": ["plain", "markdown"]
        },
        "source_excerpt": {
          "type": ["string", "null"]
        },
        "excerpt_hash": {
          "type": ["string", "null"]
        },
        "truncated": {
          "type": "boolean"
        }
      },
      "additionalProperties": false
    },
    "doc_link": {
      "type": "object",
      "required": ["ref", "source_path", "marker", "status"],
      "properties": {
        "ref": {
          "$ref": "#/definitions/reference_id"
        },
        "source_path": {
          "type": "string",
          "pattern": "^workflow_handbook/.+\\.md$"
        },
        "marker": {
          "type": "string",
          "pattern": "^\\[\\[[^\\]]+\\]\\]$"
        },
        "line": {
          "type": ["integer", "null"],
          "minimum": 1
        },
        "status": {
          "type": "string",
          "enum": ["resolved", "missing", "ambiguous"]
        },
        "target_html": {
          "type": ["string", "null"]
        }
      },
      "additionalProperties": false
    },
    "reference_id": {
      "type": "string",
      "pattern": "^(stage|skill|artifact|term|source|page):[A-Za-z0-9_./:# -]+$"
    }
  },
  "additionalProperties": false
}
```

Example generated entry:

```json
{
  "schema_version": "0.1",
  "generated_at": "2026-05-21T00:00:00Z",
  "source_index_version": "skill_contracts:0.1",
  "source_roots": [
    "schemas/skill_contracts.json",
    ".agents/skills",
    ".agents/references",
    "workflow_handbook"
  ],
  "entries": {
    "skill:docs-site": {
      "ref": "skill:docs-site",
      "kind": "skill",
      "title": "docs-site",
      "summary": "Render finalized Markdown docs into human-readable HTML views.",
      "truth_status": "source_of_truth",
      "owner": "docs-site",
      "source_paths": [
        {
          "path": "schemas/skill_contracts.json",
          "anchor": "docs-site",
          "line": null,
          "role": "skill_contract"
        },
        {
          "path": ".agents/skills/docs-site/SKILL.md",
          "anchor": null,
          "line": null,
          "role": "skill_source"
        }
      ],
      "preview": {
        "title": "docs-site",
        "body": "Writes docs/_views/** and docs/_site/** after durable Markdown is finalized; Markdown and Evidence Chains remain the source of truth.",
        "format": "plain",
        "source_excerpt": null,
        "excerpt_hash": null,
        "truncated": false
      },
      "related_refs": [
        "artifact:docs/_views",
        "artifact:docs/_site",
        "term:Evidence Chain"
      ],
      "last_validated_by": "build_workflow_handbook_reference_index.py"
    }
  },
  "links_by_doc": {
    "workflow_handbook/pages/04_markdown_to_html_preview_chain.md": [
      {
        "ref": "skill:docs-site",
        "source_path": "workflow_handbook/pages/04_markdown_to_html_preview_chain.md",
        "marker": "[[skill:docs-site]]",
        "line": 42,
        "status": "resolved",
        "target_html": "docs/_site/workflow_handbook/skills/docs-site.html"
      }
    ]
  }
}
```

## 9. Tooling 设计

### 9.1 `validate_workflow_handbook.py`

New file:

```text
tooling/evidence/validate_workflow_handbook.py
```

Responsibilities:

1. Discover Markdown files under `workflow_handbook/`.
2. Enforce root file rule:

```text
workflow_handbook/Workflow_Operator_Handbook.md
workflow_handbook/Workflow_Stage_Cards.md
```

Only these two Markdown files may live directly under `workflow_handbook/`.
Other docs must live under `pages/**`, `stages/**`, `skills/**`, or `plans/**`.

3. Parse frontmatter for split pages.
4. Validate frontmatter against `workflow_handbook_page.schema.json`.
5. Apply Page Kind required heading checks.
6. Validate `workflow_handbook/config/navigation.json` against
   `workflow_handbook_nav.schema.json` when it exists.
7. Verify navigation entries point to existing files.
8. Extract `[[...]]` markers and check prefix validity.
9. Validate `docs/_views/workflow_handbook_reference_index.json` against
   `workflow_handbook_reference_index.schema.json` when it exists.
10. Report explicit errors for missing, ambiguous, or unsupported references.

Command:

```bash
python tooling/evidence/validate_workflow_handbook.py --workspace-root .
```

Expected behavior:

- fail fast on invalid schema JSON;
- fail fast on malformed frontmatter;
- fail if navigation points to missing pages;
- fail if generated pages drift from Skill Contracts after generator support is
  implemented;
- allow `plans/**` to be drafts, but still require valid links if they use
  `[[...]]` references.

### 9.2 `build_workflow_handbook_reference_index.py`

New file:

```text
tooling/evidence/build_workflow_handbook_reference_index.py
```

Inputs:

```text
schemas/skill_contracts.json
.agents/skills/*/SKILL.md
.claude/skills/*/SKILL.md
.agents/references/*.md
.claude/shared/*.md
tooling/codex_hooks/README.md
tooling/evidence/*.py
schemas/*.schema.json
tooling/.tests/*.py
workflow_handbook/**/*.md
```

Output:

```text
docs/_views/workflow_handbook_reference_index.json
```

Build steps:

1. Load `schemas/skill_contracts.json`.
2. Generate `skill:*` entries:
   - `summary` from skill frontmatter description when present;
   - `source_paths` from contract and `.agents/skills/<skill>/SKILL.md`;
   - `preview.body` from purpose, declared paths, required actions, forbidden
     actions, and generated-view boundaries.
3. Generate `stage:*` entries:
   - canonical WF stage id;
   - primary skill;
   - expected outputs;
   - Gate requirements;
   - next stage or rollback behavior.
4. Generate `artifact:*` entries:
   - from Skill Contract `artifact_outputs`;
   - from known state ownership tables in the handbook;
   - mark `truth_status` as `source_of_truth`, `generated_view`, or
     `runtime_state`.
5. Generate `term:*` entries:
   - from `.agents/references/ubiquitous-language.md`;
   - optionally compare with `.claude/shared/ubiquitous-language.md` if present.
6. Generate `source:*` entries:
   - only for allowlisted framework files;
   - include path, optional anchor, optional line.
7. Generate `page:*` entries:
   - from parsed handbook frontmatter;
   - include title, summary, page kind, output HTML target.
8. Extract every `[[...]]` marker from `workflow_handbook/**/*.md`.
9. Populate `links_by_doc`.
10. Mark unresolved references as `missing`; do not silently drop them.
11. Validate output against
    `schemas/workflow_handbook_reference_index.schema.json`.

Command:

```bash
python tooling/evidence/build_workflow_handbook_reference_index.py \
  --workspace-root .
```

### 9.3 Stage / Skill Page Generator

Extend:

```text
tooling/codex_hooks/generate_stage_cards.py
```

Add optional arguments:

```text
--pages-output workflow_handbook
--generate-skill-pages
--generate-stage-pages
```

Example:

```bash
python tooling/codex_hooks/generate_stage_cards.py \
  --workspace-root . \
  --output workflow_handbook/Workflow_Stage_Cards.md \
  --pages-output workflow_handbook \
  --generate-skill-pages \
  --generate-stage-pages
```

Generated files:

```text
workflow_handbook/skills/<skill>.md
workflow_handbook/stages/<stage>.md
```

Generated skill page content:

```text
frontmatter
# <skill>
## Purpose
## Triggers
## Can Write
## Final Outputs
## Tool-Owned Outputs
## Must Read
## Must Prove
## Cannot Do
## Exit Condition
## Related References
```

Generated stage page content:

```text
frontmatter
# <stage>
## Purpose
## Inputs
## Outputs
## Required Reads
## Gates
## Exit Condition
## Related Skills
## Related References
```

Rules:

- generator output should be deterministic;
- generated files should include `source_type: "generated"`;
- generated pages should name `schemas/skill_contracts.json` as a canonical
  source;
- tests should fail if generated pages drift from contracts.

### 9.4 `build_docs_site.py` Extension

Extend existing renderer instead of creating a separate site generator.

Add CLI arguments:

```text
--nav-config workflow_handbook/config/navigation.json
--site-title "Harness Workflow Handbook"
--reference-mode project-evidence|workflow-handbook
```

Expected command:

```bash
python tooling/evidence/build_docs_site.py \
  --workspace-root . \
  --source-root workflow_handbook \
  --output-root docs/_site/workflow_handbook \
  --preview-index docs/_views/workflow_handbook_reference_index.json \
  --nav-config workflow_handbook/config/navigation.json \
  --site-title "Harness Workflow Handbook" \
  --reference-mode workflow-handbook
```

Renderer requirements:

- current project docs behavior must remain unchanged when `--reference-mode`
  is omitted;
- `project-evidence` mode continues to support `[F:*]`, `[U:*]`, and `[E:*]`;
- `workflow-handbook` mode supports `[[stage:*]]`, `[[skill:*]]`,
  `[[artifact:*]]`, `[[term:*]]`, `[[source:*]]`, and `[[page:*]]`;
- reference preview cards use
  `docs/_views/workflow_handbook_reference_index.json`;
- `navigation.json` controls sidebar grouping and ordering;
- output manifest still validates against `schemas/docs_site_manifest.schema.json`;
- manifest page entries may include additional metadata such as `page_id`,
  `page_kind`, `source_type`, and `references`.

### 9.5 Optional Aggregate Assembler

Optional new file:

```text
tooling/codex_hooks/assemble_operator_handbook.py
```

Purpose:

- assemble `workflow_handbook/pages/**` into
  `workflow_handbook/Workflow_Operator_Handbook.md`;
- keep the aggregate file readable by AI and simple text search;
- preserve any future protected sections such as `## Custom`;
- avoid making humans read generated stage/skill pages when they only need the
  narrative handbook.

This is optional. If the aggregate remains hand-authored, tests should instead
verify that it links to the split pages and still mentions critical workflow
chains.

## 10. Validation Plan

Schema parse checks:

```bash
python -m json.tool schemas/workflow_handbook_page.schema.json
python -m json.tool schemas/workflow_handbook_nav.schema.json
python -m json.tool schemas/workflow_handbook_reference_index.schema.json
```

Handbook validation:

```bash
python tooling/evidence/validate_workflow_handbook.py --workspace-root .
```

Stage reference regeneration check:

```bash
python tooling/codex_hooks/generate_stage_cards.py \
  --workspace-root . \
  --output /tmp/Workflow_Stage_Cards.generated.md
diff -u workflow_handbook/Workflow_Stage_Cards.md \
  /tmp/Workflow_Stage_Cards.generated.md
```

Reference index build:

```bash
python tooling/evidence/build_workflow_handbook_reference_index.py \
  --workspace-root .
```

HTML render:

```bash
python tooling/evidence/build_docs_site.py \
  --workspace-root . \
  --source-root workflow_handbook \
  --output-root docs/_site/workflow_handbook \
  --preview-index docs/_views/workflow_handbook_reference_index.json \
  --nav-config workflow_handbook/config/navigation.json \
  --site-title "Harness Workflow Handbook" \
  --reference-mode workflow-handbook
```

Focused tests:

```bash
pytest tooling/.tests/test_workflow_handbook_site.py
pytest tooling/.tests/test_evidence_docchain.py
pytest tooling/.tests/test_codex_hooks_contracts.py
```

Expected test coverage:

- root `workflow_handbook/*.md` contains only two daily entrypoints;
- `Workflow_Stage_Cards.md` matches generated output;
- schema files parse as JSON;
- every split page frontmatter validates;
- every page has the required headings for its `kind`;
- every navigation entry resolves to an existing source page;
- every `[[...]]` marker is present in `links_by_doc`;
- unresolved references are explicit `missing` entries;
- generated skill and stage pages match `schemas/skill_contracts.json`;
- generated reference index validates;
- generated HTML manifest validates;
- existing project Evidence Chain hover behavior is not broken;
- generated views under `docs/_views/**` and `docs/_site/**` are still
  tool-owned.

## 11. Rollout Slices

### Slice 1: Plan Only

Scope:

- expand this plan with external design references;
- define target structure;
- define schemas;
- define rollout order;
- do not implement tools yet.

Validation:

```bash
git diff --check
```

Report:

- `py_compile_or_NOT_RUN`: no Python changes.
- `ruff_or_NOT_RUN`: no Python changes.
- `docs_site_boundary_report`: renderer does not yet support handbook
  navigation and framework reference previews.

### Slice 2: Schema Files

Scope:

- add `schemas/workflow_handbook_page.schema.json`;
- add `schemas/workflow_handbook_nav.schema.json`;
- add `schemas/workflow_handbook_reference_index.schema.json`;
- add schema parse assertions to tests.

Validation:

```bash
python -m json.tool schemas/workflow_handbook_page.schema.json
python -m json.tool schemas/workflow_handbook_nav.schema.json
python -m json.tool schemas/workflow_handbook_reference_index.schema.json
pytest tooling/.tests/test_evidence_docchain.py
pytest tooling/.tests/test_codex_hooks_contracts.py
```

### Slice 3: Validator

Scope:

- add `tooling/evidence/validate_workflow_handbook.py`;
- add `tooling/.tests/test_workflow_handbook_site.py`;
- validate root entrypoint rule, frontmatter, navigation config, headings, and
  reference marker syntax.

Validation:

```bash
python -m py_compile tooling/evidence/validate_workflow_handbook.py
ruff check --select=E,F,I tooling/evidence/validate_workflow_handbook.py \
  tooling/.tests/test_workflow_handbook_site.py
pytest tooling/.tests/test_workflow_handbook_site.py
```

### Slice 4: Navigation Config And First Pages

Scope:

- add `workflow_handbook/config/navigation.json`;
- add first hand-authored split pages under `workflow_handbook/pages/**`;
- keep root entrypoints unchanged;
- add links from `Workflow_Operator_Handbook.md` to split pages once the pages
  exist.

Validation:

```bash
python tooling/evidence/validate_workflow_handbook.py --workspace-root .
git diff --check
```

### Slice 5: Generated Stage And Skill Pages

Scope:

- extend `generate_stage_cards.py`;
- generate `workflow_handbook/stages/**`;
- generate `workflow_handbook/skills/**`;
- ensure generated pages use valid frontmatter;
- keep `Workflow_Stage_Cards.md` as the compact lookup.

Validation:

```bash
python -m py_compile tooling/codex_hooks/generate_stage_cards.py
ruff check --select=E,F,I tooling/codex_hooks/generate_stage_cards.py \
  tooling/.tests/test_codex_hooks_contracts.py
python tooling/codex_hooks/generate_stage_cards.py \
  --workspace-root . \
  --output /tmp/Workflow_Stage_Cards.generated.md
diff -u workflow_handbook/Workflow_Stage_Cards.md \
  /tmp/Workflow_Stage_Cards.generated.md
pytest tooling/.tests/test_codex_hooks_contracts.py
pytest tooling/.tests/test_workflow_handbook_site.py
```

### Slice 6: Framework Reference Index

Scope:

- add `build_workflow_handbook_reference_index.py`;
- generate `docs/_views/workflow_handbook_reference_index.json`;
- validate schema;
- ensure missing references are explicit.

Validation:

```bash
python -m py_compile tooling/evidence/build_workflow_handbook_reference_index.py
ruff check --select=E,F,I tooling/evidence/build_workflow_handbook_reference_index.py \
  tooling/.tests/test_workflow_handbook_site.py
python tooling/evidence/build_workflow_handbook_reference_index.py \
  --workspace-root .
python tooling/evidence/validate_workflow_handbook.py --workspace-root .
pytest tooling/.tests/test_workflow_handbook_site.py
```

### Slice 7: HTML Renderer Extension

Scope:

- extend `build_docs_site.py` with `--nav-config`, `--site-title`, and
  `--reference-mode`;
- support `[[...]]` reference rendering;
- support workflow handbook preview cards;
- keep project docs rendering unchanged.

Validation:

```bash
python -m py_compile tooling/evidence/build_docs_site.py
ruff check --select=E,F,I tooling/evidence/build_docs_site.py \
  tooling/.tests/test_evidence_docchain.py \
  tooling/.tests/test_workflow_handbook_site.py
python tooling/evidence/build_docs_site.py --workspace-root .
python tooling/evidence/build_docs_site.py \
  --workspace-root . \
  --source-root workflow_handbook \
  --output-root docs/_site/workflow_handbook \
  --preview-index docs/_views/workflow_handbook_reference_index.json \
  --nav-config workflow_handbook/config/navigation.json \
  --site-title "Harness Workflow Handbook" \
  --reference-mode workflow-handbook
pytest tooling/.tests/test_evidence_docchain.py
pytest tooling/.tests/test_workflow_handbook_site.py
```

### Slice 8: Optional Aggregate Assembly

Scope:

- decide whether `Workflow_Operator_Handbook.md` should be assembled from
  `pages/**`;
- if yes, add `assemble_operator_handbook.py`;
- if no, add tests that the hand-authored aggregate covers required sections.

Validation if implemented:

```bash
python -m py_compile tooling/codex_hooks/assemble_operator_handbook.py
ruff check --select=E,F,I tooling/codex_hooks/assemble_operator_handbook.py
python tooling/codex_hooks/assemble_operator_handbook.py --workspace-root .
git diff --check
```

### Slice 9: Marker Policy Alignment

Current state:

- `compile_doc.py` records `[F:*]`, `[U:*]`, `[D:*]`, and `[L:*]`.
- `build_docs_site.py` currently renders hover markers for `[F:*]`, `[U:*]`,
  and `[E:*]`.
- handbook framework references should use `[[...]]`, not `[F:*]`.

Decision:

- either extend project Evidence Chain hover behavior to `[D:*]` and `[L:*]`;
- or document that `[D:*]` and `[L:*]` remain compile-time trace markers
  without hover cards.

This must be implemented separately from handbook reference previews so
project Conclusion Evidence remains distinct from framework reference previews.

## 12. Completion Criteria

The handbook HTML project is complete when:

- schema files exist and are validated by tests;
- `workflow_handbook/config/navigation.json` exists and validates;
- split handbook pages exist and pass `kind` heading checks;
- generated stage and skill pages are deterministic;
- `docs/_views/workflow_handbook_reference_index.json` is generated and
  validates;
- `build_docs_site.py` renders both project docs and workflow handbook docs;
- workflow handbook HTML contains sidebar navigation and hover previews;
- project Evidence Chain hover previews still work;
- `Workflow_Operator_Handbook.md` and `Workflow_Stage_Cards.md` remain the only
  root Markdown entrypoints;
- generated views stay under `docs/_views/**` and `docs/_site/**`;
- Gate Ledger reports the render command, validation result, reason, and
  artifacts whenever the handbook HTML is rebuilt.

## 13. Open Decisions

- Whether generated handbook HTML should be committed or produced on demand.
- Whether generated `workflow_handbook/stages/**` and
  `workflow_handbook/skills/**` should be committed or regenerated on demand.
- Whether `Workflow_Operator_Handbook.md` should become an assembled aggregate.
- Whether framework preview cards should include source excerpts, generated
  summaries, or both.
- Whether local search should be added after the static handbook site is stable.
- Whether `[D:*]` and `[L:*]` should get project Evidence Chain hover previews.
- Whether `workflow_handbook/config/navigation.json` should remain hand-authored
  or eventually be generated from page frontmatter.
