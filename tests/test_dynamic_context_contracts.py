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
