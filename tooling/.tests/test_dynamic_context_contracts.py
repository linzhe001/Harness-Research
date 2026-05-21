from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_dynamic_context_templates_exist() -> None:
    required = [
        "OPERATOR_CONTEXT.md.template",
        "templates/docs/00_START_HERE.md",
        "templates/docs/10_contract/Project_Contract.md",
        "templates/docs/10_contract/Evaluation_Contract.md",
        "templates/docs/10_contract/Baseline_Contract.md",
        "templates/docs/10_contract/Claim_Boundary.md",
        "templates/docs/20_facts/Project_Glossary.md",
        "templates/docs/30_evidence/Evidence_Index.md",
        "templates/docs/35_protocol/Research_Protocol.md",
        "templates/docs/40_iterations/latest.md",
        "templates/docs/50_memory/Lessons.md",
        "schemas/evidence_chain.schema.json",
        "schemas/source_manifest.schema.json",
        "schemas/doc_audit.schema.json",
        ".agents/skills/doc-compiler/SKILL.md",
        ".claude/skills/doc-compiler/SKILL.md",
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
        (
            REPO_ROOT
            / ".agents/skills/orchestrator/references/project-state-schema.json"
        ).read_text(encoding="utf-8")
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
        (REPO_ROOT / ".agents/skill-contracts/contracts.json").read_text(
            encoding="utf-8"
        )
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
    text = (REPO_ROOT / ".claude/skills/iterate/SKILL.md").read_text(
        encoding="utf-8"
    )

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
