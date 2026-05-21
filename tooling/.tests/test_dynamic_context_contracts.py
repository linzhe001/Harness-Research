from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_dynamic_context_templates_exist() -> None:
    required = [
        "OPERATOR_CONTEXT.md.template",
        "templates/docs/00_START_HERE.md",
        "templates/docs/10_contract/Project_Contract.md",
        "templates/docs/10_contract/Evaluation_Contract.md",
        "templates/docs/10_contract/Baseline_Contract.md",
        "templates/docs/10_contract/Claim_Boundary.md",
        "templates/docs/20_facts/Codebase_Map.md",
        "templates/docs/20_facts/Project_Glossary.md",
        "templates/docs/30_evidence/Evidence_Index.md",
        "templates/docs/30_evidence/Validation_Table.md",
        "templates/docs/35_protocol/Research_Protocol.md",
        "templates/docs/40_iterations/latest.md",
        "templates/docs/50_memory/Lessons.md",
        "schemas/evidence_chain.schema.json",
        "schemas/source_manifest.schema.json",
        "schemas/doc_audit.schema.json",
        "schemas/evidence_index.schema.json",
        "schemas/review_packet.schema.json",
        "schemas/approval_record.schema.json",
        "schemas/project_state.schema.json",
        "schemas/iteration_log.schema.json",
        "schemas/project_map.schema.json",
        "schemas/docs_site_manifest.schema.json",
        "schemas/codebase_map_doc.schema.json",
        "schemas/glossary_doc.schema.json",
        "schemas/architecture_doc.schema.json",
        "schemas/api_reference_doc.schema.json",
        "schemas/runbook_doc.schema.json",
        "schemas/implementation_roadmap_doc.schema.json",
        "schemas/decision_log_doc.schema.json",
        "schemas/validation_report_doc.schema.json",
        "schemas/evidence_preview_index.schema.json",
        "tooling/evidence/build_docs_site.py",
        "schemas/skill_contracts.json",
        "schemas/skill_contracts.schema.json",
        ".agents/skills/doc-compiler/SKILL.md",
        ".agents/skills/docs-site/SKILL.md",
        ".claude/skills/doc-compiler/SKILL.md",
        ".claude/skills/docs-site/SKILL.md",
    ]
    missing = [path for path in required if not (REPO_ROOT / path).exists()]
    assert not missing


def test_agents_and_claude_shared_rules_are_mirrored() -> None:
    mirrored = [
        "context-layering-policy.md",
        "research-invariants.md",
        "evidence-chain-rule.md",
        "contract-gating-rule.md",
        "lesson-quality-rule.md",
    ]
    for name in mirrored:
        agents_text = (REPO_ROOT / ".agents" / "references" / name).read_text(
            encoding="utf-8"
        )
        claude_text = (REPO_ROOT / ".claude" / "shared" / name).read_text(
            encoding="utf-8"
        )
        assert agents_text.splitlines()[0] == claude_text.splitlines()[0]
        assert "Purpose" in agents_text
        assert "Purpose" in claude_text


def test_project_state_schema_has_optional_contracts() -> None:
    schema = json.loads(
        (REPO_ROOT / "schemas" / "project_state.schema.json").read_text(
            encoding="utf-8"
        )
    )
    props = schema["properties"]
    assert "context_model_version" in props
    assert "workflow_mode" in props
    assert "contracts" in props
    contract_props = props["contracts"]["properties"]
    assert {
        "project_contract",
        "evaluation_contract",
        "baseline_contract",
        "claim_boundary",
    }.issubset(contract_props)


def test_core_state_schemas_are_promoted_from_skill_references() -> None:
    mirrors = [
        (
            "schemas/project_state.schema.json",
            ".agents/skills/orchestrator/references/project-state-schema.json",
            ".claude/skills/orchestrator/templates/project-state-schema.json",
        ),
        (
            "schemas/iteration_log.schema.json",
            ".agents/skills/iterate/references/iteration-log-schema.json",
            ".claude/skills/iterate/templates/iteration-log-schema.json",
        ),
        (
            "schemas/project_map.schema.json",
            ".agents/skills/build-plan/references/project-map-schema.json",
            ".claude/skills/build-plan/templates/project-map-schema.json",
        ),
    ]
    for root_schema, agents_schema, claude_schema in mirrors:
        root_text = (REPO_ROOT / root_schema).read_text(encoding="utf-8")
        assert root_text == (REPO_ROOT / agents_schema).read_text(encoding="utf-8")
        assert root_text == (REPO_ROOT / claude_schema).read_text(encoding="utf-8")


def test_stage_gates_preserve_legacy_compatibility() -> None:
    text = (
        REPO_ROOT / ".agents/skills/orchestrator/references/stage-gates.md"
    ).read_text(encoding="utf-8")
    assert "dynamic-protocol-v1" in text
    assert "compatibility inputs" in text
    assert "fact layer" in text
    assert "Evaluation_Contract.md" in text


def test_gate_ledger_rule_lives_in_existing_references() -> None:
    for path in [
        ".agents/references/workflow-guide.md",
        ".claude/Workflow_Guide.md",
        ".agents/references/contract-gating-rule.md",
        ".claude/shared/contract-gating-rule.md",
    ]:
        text = (REPO_ROOT / path).read_text(encoding="utf-8")
        assert "Gate ledger" in text
        assert "NOT_RUN" in text


def test_workflow_guides_document_wf0_operator_context_boundary() -> None:
    for path in [
        ".agents/references/workflow-guide.md",
        ".claude/Workflow_Guide.md",
    ]:
        text = (REPO_ROOT / path).read_text(encoding="utf-8")
        assert "WF0 bootstrap/init" in text
        assert "does not create or infer `OPERATOR_CONTEXT.md`" in text


def test_codex_skills_report_gate_ledgers_without_separate_rule_file() -> None:
    contracts = json.loads(
        (REPO_ROOT / "schemas/skill_contracts.json").read_text(encoding="utf-8")
    )["contracts"]
    required_skills = [
        contract["skill"]
        for contract in contracts
        if "gate_ledger" in contract.get("required_actions", [])
    ]
    for skill in required_skills:
        text = (REPO_ROOT / ".agents" / "skills" / skill / "SKILL.md").read_text(
            encoding="utf-8"
        )
        assert "ledger" in text.lower()


def test_docs_site_skill_has_durable_markdown_handoff() -> None:
    required_snippets = {
        ".agents/skills/docs-site/SKILL.md": [
            "durable documentation boundary",
            "Do not run this skill after every temporary Markdown edit",
            "docs/_site/**",
            "Markdown as source of truth",
        ],
        ".claude/skills/docs-site/SKILL.md": [
            "durable documentation boundary",
            "Do not run this skill after every temporary Markdown edit",
            "docs/_site/**",
            "Markdown as source of truth",
        ],
        ".agents/skills/doc-compiler/SKILL.md": ["$docs-site"],
        ".claude/skills/doc-compiler/SKILL.md": ["/docs-site"],
        ".agents/skills/build-plan/SKILL.md": ["docs_site_render_or_NOT_RUN"],
        ".claude/skills/build-plan/SKILL.md": ["docs_site_render_or_NOT_RUN"],
        ".agents/skills/code-expert/SKILL.md": [
            "compile_doc_or_NOT_RUN",
            "$docs-site",
        ],
        ".claude/skills/code-expert/SKILL.md": [
            "compile_doc_or_NOT_RUN",
            "/docs-site",
        ],
        ".agents/skills/code-debug/SKILL.md": [
            "compile_doc_or_NOT_RUN",
            "$docs-site",
        ],
        ".claude/skills/code-debug/SKILL.md": [
            "compile_doc_or_NOT_RUN",
            "/docs-site",
        ],
        ".agents/skills/validate-run/SKILL.md": ["docs_site_render_or_NOT_RUN"],
        ".claude/skills/validate-run/SKILL.md": ["docs_site_render_or_NOT_RUN"],
        "AGENTS.md.template": ["$docs-site", "docs/_site/**"],
        "CLAUDE.md.template": ["/docs-site", "docs/_site/**"],
        ".agents/skills/init-project/references/claude-md-template.md": [
            "$docs-site",
            "docs/_site/**",
        ],
        ".claude/skills/init-project/templates/claude-md-template.md": [
            "/docs-site",
            "docs/_site/**",
        ],
    }

    for relative, snippets in required_snippets.items():
        text = (REPO_ROOT / relative).read_text(encoding="utf-8")
        missing = [snippet for snippet in snippets if snippet not in text]
        assert not missing, f"{relative} missing {missing}"

    durable_markdown_skills = [
        "review-packet",
        "protocol-compiler",
        "protocol-drift-check",
        "survey-idea",
        "idea-debate",
        "refine-idea",
        "data-prep",
        "baseline-repro",
        "deep-check",
        "evaluate",
        "init-project",
        "iterate",
        "auto-iterate-goal",
        "final-exp",
        "release",
    ]
    for skill in durable_markdown_skills:
        agents_text = (REPO_ROOT / f".agents/skills/{skill}/SKILL.md").read_text(
            encoding="utf-8"
        )
        claude_text = (REPO_ROOT / f".claude/skills/{skill}/SKILL.md").read_text(
            encoding="utf-8"
        )
        assert "$docs-site" in agents_text
        assert "/docs-site" in claude_text
        assert "docs_site_render_or_NOT_RUN" in agents_text
        assert "docs_site_render_or_NOT_RUN" in claude_text


def test_auto_iterate_goal_claude_matches_codex_gate_inputs() -> None:
    agents_text = (REPO_ROOT / ".agents/skills/auto-iterate-goal/SKILL.md").read_text(
        encoding="utf-8"
    )
    claude_text = (REPO_ROOT / ".claude/skills/auto-iterate-goal/SKILL.md").read_text(
        encoding="utf-8"
    )

    for required in ["Baseline_Contract.md", "Evaluation_Contract.md", "Gate ledger"]:
        assert required in agents_text
        assert required in claude_text


def test_claude_iterate_keeps_wf10_gate_ledger_handoff() -> None:
    text = (REPO_ROOT / ".claude/skills/iterate/SKILL.md").read_text(encoding="utf-8")

    assert "Gate ledger" in text
    assert "check_workflow_state.py" in text


def test_ubiquitous_language_is_workflow_scoped() -> None:
    for path in [
        ".agents/references/ubiquitous-language.md",
        ".claude/shared/ubiquitous-language.md",
    ]:
        text = (REPO_ROOT / path).read_text(encoding="utf-8")
        assert "Workflow Skill Language" in text
        assert "Application Codebase Language" not in text
        assert "| Domain Term | Code Term |" not in text
        assert "generated by WF6" in text


def test_ai_coding_methods_are_wired_into_workflow_skills() -> None:
    required_snippets = {
        ".agents/skills/survey-idea/SKILL.md": [
            "Explore Intake Grill",
            "Explore Synthesis Grill",
        ],
        ".agents/skills/refine-arch/references/technical-spec.md": [
            "first_vertical_slice",
            "module_boundaries",
            "application_codebase_language_seed",
            "Project_Glossary.md",
        ],
        ".agents/skills/build-plan/references/implementation-roadmap.md": [
            "Slice Trace",
            "application_codebase_language_updates",
            "test_plan",
            "complexity_budget",
        ],
        ".agents/skills/code-expert/SKILL.md": [
            "current roadmap slice",
            "Project_Glossary.md",
            "first focused test or smoke check",
        ],
        ".agents/skills/validate-run/references/validate-run-report.md": [
            "Slice Completion Review",
            "Language / Boundary / Complexity Review",
        ],
        ".agents/skills/iterate/references/iteration-constraints.md": [
            "vertical slice boundary",
            "complexity and boundary observations",
        ],
    }

    for relative, snippets in required_snippets.items():
        text = (REPO_ROOT / relative).read_text(encoding="utf-8")
        missing = [snippet for snippet in snippets if snippet not in text]
        assert not missing, f"{relative} missing {missing}"


def test_claude_ai_coding_methods_match_codex_surface() -> None:
    required_snippets = {
        ".claude/skills/survey-idea/SKILL.md": ["Explore Intake Grill"],
        ".claude/skills/refine-arch/templates/technical-spec.md": [
            "first_vertical_slice",
            "module_boundaries",
            "application_codebase_language_seed",
            "Project_Glossary.md",
        ],
        ".claude/skills/build-plan/templates/implementation-roadmap.md": [
            "Slice Trace",
            "application_codebase_language_updates",
            "test_plan",
            "complexity_budget",
        ],
        ".claude/skills/code-expert/SKILL.md": [
            "current roadmap slice",
            "Project_Glossary.md",
        ],
        ".claude/skills/validate-run/SKILL.md": [
            "slice completion",
            "Project_Glossary.md",
        ],
        ".claude/skills/iterate/SKILL.md": [
            "vertical slice boundary",
            "complexity and boundary observations",
        ],
    }

    for relative, snippets in required_snippets.items():
        text = (REPO_ROOT / relative).read_text(encoding="utf-8")
        missing = [snippet for snippet in snippets if snippet not in text]
        assert not missing, f"{relative} missing {missing}"
