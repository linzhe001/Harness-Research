from __future__ import annotations

import json
import shutil
import subprocess
import sys
from io import StringIO
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "tooling" / "codex_hooks"))

VISIBLE_SKILL_ALIASES = {
    "analyze",
    "build",
    "change",
    "grill",
    "prepare",
    "run",
    "write",
}

import check_contracts  # noqa: E402
import generate_stage_cards  # noqa: E402
import harness_contracts  # noqa: E402
import hook_status  # noqa: E402
from harness_contracts import (  # noqa: E402
    CONTRACTS_PATH,
    LAST_ROUTE_PATH,
    READ_LEDGER_PATH,
    READ_LEDGERS_DIR,
    RUNTIME_DIR,
    SLICED_COMMIT_RULE_PATH,
    block_pre_tool,
    classify_prompt_intent,
    consume_gate_ledger_notice,
    contract_by_skill,
    daily_context_for_workspace,
    detect_skill,
    detect_skill_match,
    external_review_output_paths,
    is_git_commit_command,
    is_harness_workspace,
    load_contracts,
    load_pending,
    load_read_ledger,
    load_read_ledger_for_event,
    load_session,
    looks_mutating_bash,
    mark_pending_for_changes,
    mark_tool_activity,
    mutating_event_paths,
    pre_tool_notice,
    python_script_from_command,
    record_command_reads,
    record_direct_tool_read,
    record_read,
    required_existing_files,
    reset_read_ledger,
    save_pending,
    save_read_ledger,
    save_read_ledger_for_event,
    save_session,
    stop_decision,
    tool_owned_output_paths,
    truncate_user_prompt_context,
    validate_contract_files,
)
from hook_status import (  # noqa: E402
    build_status,
    hook_trust_entries_from_response,
    render_status,
    summarize_hook_trust,
)
from install_hooks import (  # noqa: E402
    _copy_rule_templates,
    _copy_runtime_scripts,
    _ensure_hooks_enabled,
    _load_hook_config,
    _remove_rule_templates,
)
from user_prompt_submit import main as user_prompt_submit_main  # noqa: E402


def _clean_runtime() -> None:
    shutil.rmtree(REPO_ROOT / RUNTIME_DIR, ignore_errors=True)


def _write_contracts(root: Path, contracts: list[dict[str, object]]) -> None:
    contracts_path = root / CONTRACTS_PATH
    contracts_path.parent.mkdir(parents=True, exist_ok=True)
    contracts_path.write_text(
        json.dumps({"schema_version": "0.1", "contracts": contracts}) + "\n",
        encoding="utf-8",
    )


@pytest.fixture(autouse=True)
def clean_hook_runtime(tmp_path: Path) -> None:
    runtime = REPO_ROOT / RUNTIME_DIR
    backup = tmp_path / "hook_runtime_backup"
    if runtime.exists():
        shutil.copytree(runtime, backup)
    _clean_runtime()
    yield
    _clean_runtime()
    if backup.exists():
        shutil.copytree(backup, runtime)


def test_skill_contract_files_are_valid() -> None:
    errors = validate_contract_files(REPO_ROOT)
    assert not errors

    for contract in load_contracts(REPO_ROOT):
        assert contract.get("write_scope", {}).get("allowed_paths"), contract["skill"]
        assert contract.get("artifact_outputs"), contract["skill"]


def _frontmatter_skill_names(surface: str) -> set[str]:
    return {
        path.parent.name
        for path in (REPO_ROOT / surface / "skills").glob("*/SKILL.md")
        if path.read_text(encoding="utf-8").startswith("---\n")
    }


def _codex_skill_names() -> set[str]:
    return {
        path.parent.name
        for path in (REPO_ROOT / ".agents" / "skills").glob("*/SKILL.md")
    }


def _policy_block(metadata_text: str) -> str:
    lines = metadata_text.splitlines()
    try:
        start = lines.index("policy:")
    except ValueError:
        return ""
    end = len(lines)
    for index in range(start + 1, len(lines)):
        if lines[index] and not lines[index].startswith(" "):
            end = index
            break
    return "\n".join(lines[start:end])


def test_codex_skill_sources_are_loader_clean() -> None:
    assert _frontmatter_skill_names(".agents") == _codex_skill_names()


def test_only_human_facing_claude_aliases_have_frontmatter() -> None:
    assert _frontmatter_skill_names(".claude") == VISIBLE_SKILL_ALIASES


def test_internal_codex_skill_sources_are_product_filtered() -> None:
    for skill in _codex_skill_names() - VISIBLE_SKILL_ALIASES:
        metadata_path = (
            REPO_ROOT / ".agents" / "skills" / skill / "agents" / "openai.yaml"
        )
        metadata_text = metadata_path.read_text(encoding="utf-8")
        policy = _policy_block(metadata_text)
        assert "products:" in policy, skill
        assert "- chatgpt" in policy, skill
        assert "- codex" not in policy.lower(), skill
        assert "allow_implicit_invocation: false" in policy, skill


def test_internal_claude_skill_sources_are_not_autocomplete_entries() -> None:
    internal_skills = {
        "auto-paper",
        "auto-iterate-goal",
        "change-intake",
        "code-debug",
        "docs-site",
        "evaluate",
        "harness-maintenance",
        "iterate",
        "workflow-supervisor",
    }

    for skill in internal_skills:
        path = REPO_ROOT / ".claude" / "skills" / skill / "SKILL.md"
        assert path.exists(), path.relative_to(REPO_ROOT).as_posix()
        assert not path.read_text(encoding="utf-8").startswith("---\n")


def test_iterate_contract_covers_eval_iteration_reports() -> None:
    contract = contract_by_skill(REPO_ROOT, "iterate")
    assert contract is not None

    assert "wf10_state_preflight" in contract["required_actions"]
    assert "single_next_command" in contract["required_actions"]
    assert "run_local_promotion_check" in contract["required_actions"]
    assert "iteration_report_write" in contract["gate_ledger_required_when"]
    assert "docs/iterations/" in contract["sensitive_paths"]
    assert (
        ".agents/references/run-artifact-contract.md"
        in contract["required_read_set"]["harness"]
    )


def test_run_artifact_contract_is_required_for_training_result_skills() -> None:
    for skill in [
        "baseline-repro",
        "build-plan",
        "validate-run",
        "iterate",
        "evaluate",
    ]:
        contract = contract_by_skill(REPO_ROOT, skill)
        assert contract is not None
        assert (
            ".agents/references/run-artifact-contract.md"
            in contract["required_read_set"]["harness"]
        ), skill


def test_code_debug_contract_excludes_harness_maintenance_paths() -> None:
    contract = contract_by_skill(REPO_ROOT, "code-debug")
    assert contract is not None

    allowed = contract["write_scope"]["allowed_paths"]
    assert "tooling/codex_hooks/" not in allowed
    assert "schemas/" not in allowed
    assert ".agents/skills/" not in allowed


def test_harness_maintenance_contract_covers_guardrail_paths() -> None:
    contract = contract_by_skill(REPO_ROOT, "harness-maintenance")
    assert contract is not None

    allowed = contract["write_scope"]["allowed_paths"]
    assert "tooling/codex_hooks/" in allowed
    assert "schemas/" in allowed
    assert ".agents/skills/" in allowed
    assert ".claude/Workflow_Guide.md" in allowed
    assert ".claude/skills/" in allowed
    assert ".claude/rules/" in allowed
    assert "docs/" in allowed
    assert "workflow_handbook/" in allowed
    assert "templates/" in allowed
    assert ".gitignore" in allowed
    assert "AGENTS.md.template" in allowed
    assert "CLAUDE.md.template" in allowed
    assert (
        ".agents/references/ubiquitous-language.md"
        in contract["required_read_set"]["harness"]
    )


def test_workflow_gate_optimization_routes_to_harness_maintenance() -> None:
    prompt = (
        "根据 优化workflow建议.pdf 看看怎么优化我的workflow。"
        "gate 设置很多导致自动 supervisor 下载 baseline 和 dataset 经常被阻拦，"
        "而且 token 消耗很快，可能和提示词注入或 context budget 有关。"
    )

    match = detect_skill_match(REPO_ROOT, prompt)

    assert match is not None
    assert match["candidate_skill"] == "harness-maintenance"
    assert match["candidate_trigger"] == "inferred_harness_maintenance"


def test_high_frequency_skill_bodies_stay_compact() -> None:
    high_frequency_skills = {
        ".claude/skills/iterate/SKILL.md": 250,
        ".claude/skills/orchestrator/SKILL.md": 250,
        ".claude/skills/init-project/SKILL.md": 250,
        ".claude/skills/validate-run/SKILL.md": 250,
        ".agents/skills/workflow-supervisor/SKILL.md": 250,
        ".agents/skills/grill/SKILL.md": 250,
    }

    for relative_path, hard_limit in high_frequency_skills.items():
        lines = (REPO_ROOT / relative_path).read_text(encoding="utf-8").splitlines()
        assert len(lines) <= hard_limit, relative_path


def test_codex_skill_bodies_stay_under_compact_budget() -> None:
    hard_limit = 130

    for path in sorted((REPO_ROOT / ".agents" / "skills").glob("*/SKILL.md")):
        lines = path.read_text(encoding="utf-8").splitlines()
        assert len(lines) <= hard_limit, path.relative_to(REPO_ROOT).as_posix()


def test_claude_skill_bodies_stay_under_compact_budget() -> None:
    hard_limit = 160

    for path in sorted((REPO_ROOT / ".claude" / "skills").glob("*/SKILL.md")):
        lines = path.read_text(encoding="utf-8").splitlines()
        assert len(lines) <= hard_limit, path.relative_to(REPO_ROOT).as_posix()


def test_heavy_workflow_skills_have_context_budgets() -> None:
    expected = {
        "survey-idea": "source_count_max",
        "idea-debate": "candidate_count_max",
        "deep-check": "design_target_count_max",
        "iterate": "recent_iteration_count_max",
        "evaluate": "report_word_count_max",
    }

    for skill, key in expected.items():
        budget = contract_by_skill(REPO_ROOT, skill).get("context_budget", {})
        assert budget.get(key), skill
    assert contract_by_skill(REPO_ROOT, "iterate")["context_budget"][
        "gate_ledger_summary_count_max"
    ] == 5


def test_generated_docs_site_assets_are_not_gitignored() -> None:
    paths = [
        "docs/_site/manifest.json",
        "docs/_site/assets/site.css",
        "docs/_site/assets/evidence-preview.js",
    ]

    for path in paths:
        result = subprocess.run(
            ["git", "check-ignore", "-q", path],
            cwd=REPO_ROOT,
            check=False,
        )
        assert result.returncode == 1, path


def test_historical_supervisor_design_docs_are_not_default_reads() -> None:
    removed_paths = [
        "docs/grill_execution_supervisor.md",
        "docs/grill_execution_supervisor_implementation_plan.md",
    ]

    for path in removed_paths:
        assert not (REPO_ROOT / path).exists(), path

    checked_files = [
        ".agents/skills/grill/SKILL.md",
        ".agents/skills/workflow-supervisor/SKILL.md",
        ".agents/skills/change-intake/SKILL.md",
        "README.md",
    ]
    for file_path in checked_files:
        text = (REPO_ROOT / file_path).read_text(encoding="utf-8")
        for removed in removed_paths:
            assert removed not in text, file_path


def test_core_documented_harness_paths_exist() -> None:
    paths = [
        "tooling/codex_hooks",
        "tooling/evidence",
        "tooling/workflow_supervisor",
        ".agents/skills/grill/SKILL.md",
        ".agents/skills/workflow-supervisor/SKILL.md",
        ".claude/skills/grill/SKILL.md",
        ".claude/skills/workflow-supervisor/SKILL.md",
    ]

    for path in paths:
        assert (REPO_ROOT / path).exists(), path


def test_artifact_outputs_mark_tool_owned_and_legacy_paths() -> None:
    contracts = {contract["skill"]: contract for contract in load_contracts(REPO_ROOT)}

    for contract in contracts.values():
        for output in contract["artifact_outputs"]:
            if any(path.startswith(".evidence/") for path in output["paths"]):
                assert output["requires_tool"] is True
            if any(path.startswith("docs/_views/") for path in output["paths"]):
                assert output["requires_tool"] is True
            if any(path.startswith("docs/_site/") for path in output["paths"]):
                assert output["requires_tool"] is True
            if any(
                path.startswith(".workflow_supervisor/")
                for path in output["paths"]
            ):
                assert output["requires_tool"] is True
            if any(path.startswith(".auto_paper/") for path in output["paths"]):
                assert output["requires_tool"] is True
            if output["kind"] == "legacy_compat":
                assert output.get("replacement")

    iterate_outputs = contracts["iterate"]["artifact_outputs"]
    assert any(
        output["kind"] == "current_doc" and "docs/40_iterations/" in output["paths"]
        for output in iterate_outputs
    )
    assert any(
        output["kind"] == "legacy_compat"
        and "docs/iterations/" in output["paths"]
        and output["replacement"] == "docs/40_iterations/"
        for output in iterate_outputs
    )
    assert not any(
        path.startswith(".auto_iterate/")
        for contract in contracts.values()
        for output in contract["artifact_outputs"]
        for path in output["paths"]
    )


def test_run_write_experiment_evidence_bridge_contracts() -> None:
    json_path = "docs/30_evidence/Experiment_Evidence_Index.json"
    md_path = "docs/30_evidence/Experiment_Evidence_Index.md"

    for skill in ["iterate", "evaluate"]:
        contract = contract_by_skill(REPO_ROOT, skill)
        assert contract is not None
        assert (
            "build_experiment_evidence_index_or_NOT_RUN"
            in contract["required_actions"]
        )
        assert json_path in contract["write_scope"]["allowed_paths"]
        assert md_path in contract["write_scope"]["allowed_paths"]
        assert any(
            output["kind"] == "conclusion_evidence"
            and output["requires_tool"] is True
            and json_path in output["paths"]
            and md_path in output["paths"]
            for output in contract["artifact_outputs"]
        )

    auto_paper = contract_by_skill(REPO_ROOT, "auto-paper")
    assert auto_paper is not None
    assert json_path in auto_paper["required_read_set"]["project_optional"]
    assert md_path in auto_paper["required_read_set"]["project_optional"]
    assert "iteration_log.json" in auto_paper["required_read_set"]["project_optional"]
    assert json_path not in auto_paper["write_scope"]["allowed_paths"]
    assert "iteration_log.json" in auto_paper["sensitive_paths"]
    assert "iteration_log.json" not in auto_paper["write_scope"]["allowed_paths"]
    assert any(
        output["kind"] == "tool_trace"
        and output["requires_tool"] is True
        and ".auto_paper/" in output["paths"]
        for output in auto_paper["artifact_outputs"]
    )


def test_supervisor_skill_contracts_are_guardrail_scoped() -> None:
    for skill in ["grill", "workflow-supervisor", "change-intake"]:
        contract = contract_by_skill(REPO_ROOT, skill)
        assert contract is not None
        assert "AGENTS.md" in contract["required_read_set"]["project_when_present"]
        assert "gate_ledger" in contract["required_actions"]
        assert "direct_edit_workflow_supervisor" in contract["forbidden_actions"]
        assert any(
            output["owner"] in {"workflow-supervisor", "grill-tooling"}
            and output["requires_tool"] is True
            and any(
                path.startswith(".workflow_supervisor/")
                for path in output["paths"]
            )
            for output in contract["artifact_outputs"]
        )


def test_grill_contract_requires_discussion_round_state() -> None:
    contract = contract_by_skill(REPO_ROOT, "grill")
    assert contract is not None

    assert "grill_round_contract" in contract["required_actions"]
    assert "gap_check" in contract["required_actions"]
    assert "human_exit_decision_status" in contract["required_actions"]


def test_grill_hands_accepted_draft_to_init_project() -> None:
    agents_skill = (REPO_ROOT / ".agents/skills/grill/SKILL.md").read_text(
        encoding="utf-8"
    )
    claude_skill = (REPO_ROOT / ".claude/skills/grill/SKILL.md").read_text(
        encoding="utf-8"
    )

    assert "`init-project update-from-grill`" in agents_skill
    assert "`init-project update-from-grill`" in claude_skill
    for text in [agents_skill, claude_skill]:
        assert "docs/Research_Intent_Draft.md" in text
        assert "docs/Grill_Round_Log.md" in text
        assert "docs/Execution_Readiness_Packet.md" in text
        assert "README.md" in text


def test_grill_skill_requires_execution_intent_ledger() -> None:
    agents_skill = (REPO_ROOT / ".agents/skills/grill/SKILL.md").read_text(
        encoding="utf-8"
    )
    claude_skill = (REPO_ROOT / ".claude/skills/grill/SKILL.md").read_text(
        encoding="utf-8"
    )

    for text in [agents_skill, claude_skill]:
        assert "Execution Intent Ledger" in text
        assert "hf_access_policy" in text
        assert "non_hf_registration_policy" in text
        assert "baseline_clone_policy" in text
        assert "baseline_clone_scope" in text
        assert "kind: policy" in text


def test_grill_skill_requires_executable_source_provenance() -> None:
    agents_skill = (REPO_ROOT / ".agents/skills/grill/SKILL.md").read_text(
        encoding="utf-8"
    )
    claude_skill = (REPO_ROOT / ".claude/skills/grill/SKILL.md").read_text(
        encoding="utf-8"
    )

    for text in [agents_skill, claude_skill]:
        assert "code repository URL" in text
        assert "direct downloadable" in text
        assert "Baseline Source Ledger" in text
        assert "baseline_repo_missing" in text
        assert "non-executable" in text


def test_init_project_contract_supports_grill_handoff() -> None:
    contract = contract_by_skill(REPO_ROOT, "init-project")
    assert contract is not None

    assert "update-from-grill" in contract["triggers"]
    assert "$init-project update-from-grill" in contract["triggers"]
    assert "README.md" in contract["required_read_set"]["project_when_present"]
    for path in [
        "docs/Research_Intent_Draft.md",
        "docs/Grill_Round_Log.md",
        "docs/Execution_Readiness_Packet.md",
        ".workflow_supervisor/readiness.json",
    ]:
        assert path in contract["required_read_set"]["project_optional"]

    assert "grill_handoff_read_or_NOT_RUN" in contract["required_actions"]
    assert "README_write" in contract["gate_ledger_required_when"]
    assert "grill_handoff_guidance_write" in contract["gate_ledger_required_when"]
    assert "README.md" in contract["write_scope"]["allowed_paths"]
    assert "README.md" in contract["sensitive_paths"]
    assert any(
        output["kind"] == "guidance" and "README.md" in output["paths"]
        for output in contract["artifact_outputs"]
    )


def test_init_project_skill_describes_update_from_grill_mode() -> None:
    agents_skill = (REPO_ROOT / ".agents/skills/init-project/SKILL.md").read_text(
        encoding="utf-8"
    )
    claude_skill = (REPO_ROOT / ".claude/skills/init-project/SKILL.md").read_text(
        encoding="utf-8"
    )
    agents_template = (
        REPO_ROOT / ".agents/skills/init-project/references/claude-md-template.md"
    ).read_text(encoding="utf-8")
    claude_template = (
        REPO_ROOT / ".claude/skills/init-project/templates/claude-md-template.md"
    ).read_text(encoding="utf-8")

    for text in [agents_skill, claude_skill, agents_template, claude_template]:
        assert "update-from-grill" in text
        assert "README.md" in text
        assert "WF1-WF3" in text

    for text in [agents_skill, claude_skill]:
        assert "docs/Research_Intent_Draft.md" in text
        assert "docs/Grill_Round_Log.md" in text
        assert "docs/Execution_Readiness_Packet.md" in text
        assert ".workflow_supervisor/readiness.json" in text
        assert "Do not create `PROJECT_STATE.json`, `project_map.json`, or" in text
        lowered = text.lower()
        assert "absence of" in lowered
        assert "`project_state.json`" in lowered
        assert "`project_map.json`" in lowered
        assert "`iteration_log.json`" in lowered


def test_workflow_supervisor_skill_describes_bare_post_grill_start() -> None:
    agents_skill = (
        REPO_ROOT / ".agents/skills/workflow-supervisor/SKILL.md"
    ).read_text(encoding="utf-8")
    claude_skill = (
        REPO_ROOT / ".claude/skills/workflow-supervisor/SKILL.md"
    ).read_text(encoding="utf-8")

    for text in [agents_skill, claude_skill]:
        assert "status --json" in text
        assert "--segment prepare" in text
        assert "--complete" in text
        assert "--goal-file docs/Research_Intent_Draft.md" in text
        assert "typed pending requests" in text
        assert "recover --repair-stale-running --auto-resume-answered --json" in text
        assert "resume_answered_pending_request" in text
        assert "--allow-external-downloads" in text


def test_markdown_writing_contracts_declare_docs_site_render_boundary() -> None:
    skills = [
        "doc-compiler",
        "review-packet",
        "protocol-compiler",
        "protocol-drift-check",
        "survey-idea",
        "idea-debate",
        "refine-idea",
        "data-prep",
        "baseline-repro",
        "refine-arch",
        "deep-check",
        "evaluate",
        "init-project",
        "build-plan",
        "code-expert",
        "code-debug",
        "validate-run",
        "iterate",
        "auto-iterate-goal",
        "final-exp",
        "release",
    ]

    for skill in skills:
        contract = contract_by_skill(REPO_ROOT, skill)
        assert contract is not None
        assert "docs_site_boundary_report" in contract["required_actions"]
        assert "docs_site_boundary_report" in contract["gate_ledger_required_when"]
        assert "docs_site_render" not in contract["gate_ledger_required_when"]
        assert "docs/_views/" not in contract["write_scope"]["allowed_paths"]
        assert "docs/_site/" not in contract["write_scope"]["allowed_paths"]
        assert not any(
            output["kind"] == "generated_view"
            and output["owner"] == "docs-site"
            for output in contract["artifact_outputs"]
        )


def test_docs_site_contract_only_writes_generated_views() -> None:
    contract = contract_by_skill(REPO_ROOT, "docs-site")
    assert contract is not None

    assert contract["write_scope"]["allowed_paths"] == ["docs/_views/", "docs/_site/"]
    assert "build_evidence_preview_index_or_NOT_RUN" in contract["required_actions"]
    assert "build_docs_site_or_NOT_RUN" in contract["required_actions"]
    assert "validate_docs_site_or_NOT_RUN" in contract["required_actions"]
    assert "edit_source_markdown_during_render" in contract["forbidden_actions"]
    assert "html_as_source_of_truth" in contract["forbidden_actions"]
    assert "docs_site_render" in contract["gate_ledger_required_when"]
    assert "docs/20_facts/Codebase_Map.md" in contract["required_read_set"][
        "project_when_present"
    ]

    agents_skill = (REPO_ROOT / ".agents/skills/docs-site/SKILL.md").read_text(
        encoding="utf-8"
    )
    claude_skill = (REPO_ROOT / ".claude/skills/docs-site/SKILL.md").read_text(
        encoding="utf-8"
    )
    for text in [agents_skill, claude_skill]:
        assert "Do not run this skill after every temporary Markdown edit" in text
        assert "Markdown as source of truth" in text
        assert "docs/_site/**" in text


def test_stage_specific_coding_contracts_require_glossary_when_present() -> None:
    required_skills = [
        "survey-idea",
        "idea-debate",
        "refine-idea",
        "data-prep",
        "baseline-repro",
        "refine-arch",
        "build-plan",
        "code-expert",
        "code-debug",
        "validate-run",
        "iterate",
    ]

    for skill in required_skills:
        contract = contract_by_skill(REPO_ROOT, skill)
        assert contract is not None
        read_set = contract["required_read_set"]
        assert ".agents/references/ubiquitous-language.md" in read_set["harness"]
        assert "docs/20_facts/Project_Glossary.md" in read_set[
            "project_when_present"
        ]


def test_commit_stage_contracts_require_sliced_commit_rule() -> None:
    for skill in ["build-plan", "code-expert", "code-debug"]:
        contract = contract_by_skill(REPO_ROOT, skill)
        assert contract is not None
        assert SLICED_COMMIT_RULE_PATH in contract["required_read_set"]["harness"]


def test_refine_arch_and_build_plan_own_project_glossary_writes() -> None:
    for skill in ["refine-arch", "build-plan"]:
        contract = contract_by_skill(REPO_ROOT, skill)
        assert contract is not None

        assert "docs/20_facts/Project_Glossary.md" in contract["sensitive_paths"]
        assert "docs/20_facts/Project_Glossary.md" in contract["write_scope"][
            "allowed_paths"
        ]
        assert "project_glossary_write" in contract["gate_ledger_required_when"]


def test_post_survey_stages_can_update_conclusion_evidence_tables() -> None:
    expectations = {
        "data-prep": "docs/30_evidence/Dataset_Table.md",
        "baseline-repro": "docs/30_evidence/Baseline_Table.md",
        "validate-run": "docs/30_evidence/Validation_Table.md",
    }

    for skill, path in expectations.items():
        contract = contract_by_skill(REPO_ROOT, skill)
        assert contract is not None

        assert path in contract["sensitive_paths"]
        assert path in contract["write_scope"]["allowed_paths"]
        assert "evidence_table_write" in contract["gate_ledger_required_when"]
        assert any(
            output["kind"] == "conclusion_evidence" and path in output["paths"]
            for output in contract["artifact_outputs"]
        )


def test_data_prep_contract_requires_dataset_acquisition_gate() -> None:
    contract = contract_by_skill(REPO_ROOT, "data-prep")
    assert contract is not None

    assert "archive_existing_data_docs_or_NOT_RUN" in contract["required_actions"]
    assert "dataset_acquisition_or_NOT_RUN" in contract["required_actions"]
    assert (
        "dataset_acquisition_decision_request_or_NOT_RUN"
        in contract["required_actions"]
    )
    assert "data_doc_archive" in contract["gate_ledger_required_when"]
    assert "dataset_acquisition" in contract["gate_ledger_required_when"]

    read_set = contract["required_read_set"]
    for path in [
        "docs/Refined_Idea.md",
        "docs/20_facts/Execution_Contract.md",
        "docs/30_evidence/Dataset_Table.md",
    ]:
        assert path in read_set["project_when_present"]

    skill_texts = [
        (REPO_ROOT / ".agents/skills/data-prep/SKILL.md").read_text(
            encoding="utf-8"
        ),
        (REPO_ROOT / ".claude/skills/data-prep/SKILL.md").read_text(
            encoding="utf-8"
        ),
    ]
    for text in skill_texts:
        assert "Remote Repository Selection" in text
        assert "archive_existing_data_docs_or_NOT_RUN" in text
        assert "docs/90_legacy/<YYYY-MM-DD>/" in text
        assert "candidate matrix" in text
        assert "dataset_acquisition_decision_request_or_NOT_RUN" in text
        assert "download/mount choice and target directory" in text
        assert "docs/Refined_Idea.md" in text
        assert "smoke" in text
        assert "dehaze" in text


def test_data_prep_stop_does_not_block_acquisition_decision_when_root_unresolved(
    tmp_path: Path,
) -> None:
    contract = contract_by_skill(REPO_ROOT, "data-prep")
    assert contract is not None
    _write_contracts(tmp_path, [contract])
    (tmp_path / "PROJECT_STATE.json").write_text(
        json.dumps(
            {
                "dataset_paths": {
                    "realx3d": {
                        "remote": "https://huggingface.co/datasets/ToferFish/RealX3D",
                        "local_root": None,
                        "local_archive": (
                            "/mnt/c/Users/Linzhe/Downloads/data4_smoke.tar.gz"
                        ),
                        "status": "archive_verified_extraction_pending",
                    }
                }
            }
        )
        + "\n",
        encoding="utf-8",
    )
    save_session(
        tmp_path,
        {
            "active_skill": "data-prep",
            "intent_class": "unknown",
            "read_contract_stop_required": False,
            "mutating_tool_seen": True,
        },
    )
    save_read_ledger(
        tmp_path,
        {
            "reads": {
                path: {"events": []}
                for path in required_existing_files(tmp_path, contract)
            }
        },
    )
    save_pending(
        tmp_path,
        {
            "requires_gate_ledger": True,
            "reasons": ["sensitive workflow files changed"],
            "changed_paths": ["docs/Dataset_Stats.md", "PROJECT_STATE.json"],
        },
    )

    decision = stop_decision(
        tmp_path,
        {
            "last_assistant_message": (
                "Gate ledger\n"
                "- command: not run\n"
                "- result: NOT_RUN\n"
                "- reason: dataset root unresolved\n"
                "- artifacts: docs/Dataset_Stats.md"
            ),
            "stop_hook_active": False,
        },
    )
    assert decision is None

    allowed = stop_decision(
        tmp_path,
        {
            "last_assistant_message": (
                "请确认：使用已有本地 archive 还是重新下载 dataset？"
                "下载/解压目标目录是哪一个？\n\n"
                "Gate ledger\n"
                "- command: not run\n"
                "- result: NOT_RUN\n"
                "- reason: waiting for operator download/mount choice "
                "and target directory\n"
                "- artifacts: docs/Dataset_Stats.md"
            ),
            "stop_hook_active": False,
        },
    )
    assert allowed is None


def test_codebase_map_is_created_and_synced_with_stable_code_contracts() -> None:
    codebase_map = "docs/20_facts/Codebase_Map.md"

    build_plan = contract_by_skill(REPO_ROOT, "build-plan")
    assert build_plan is not None
    assert codebase_map in build_plan["required_read_set"]["project_when_present"]
    assert codebase_map in build_plan["sensitive_paths"]
    assert codebase_map in build_plan["write_scope"]["allowed_paths"]
    assert "codebase_map_write" in build_plan["gate_ledger_required_when"]
    assert any(
        output["kind"] == "fact_doc" and codebase_map in output["paths"]
        for output in build_plan["artifact_outputs"]
    )

    for skill in ["baseline-repro", "code-expert", "code-debug"]:
        contract = contract_by_skill(REPO_ROOT, skill)
        assert contract is not None
        assert codebase_map in contract["required_read_set"]["project_when_present"]
        assert codebase_map in contract["sensitive_paths"]
        assert codebase_map in contract["write_scope"]["allowed_paths"]
        assert "codebase_map_write" in contract["gate_ledger_required_when"]

    for skill in ["code-expert", "code-debug"]:
        contract = contract_by_skill(REPO_ROOT, skill)
        assert contract is not None
        assert "compile_doc_or_NOT_RUN" in contract["required_actions"]
        assert "codebase_map_docchain" in contract["gate_ledger_required_when"]
        assert ".evidence/chains/" in contract["write_scope"]["allowed_paths"]
        assert ".evidence/index.json" in contract["write_scope"]["allowed_paths"]
        assert any(
            output["kind"] == "tool_trace"
            and output["owner"] == "evidence-tooling"
            and output["requires_tool"] is True
            and ".evidence/chains/" in output["paths"]
            and ".evidence/index.json" in output["paths"]
            for output in contract["artifact_outputs"]
        )

    validate_run = contract_by_skill(REPO_ROOT, "validate-run")
    assert validate_run is not None
    assert codebase_map in validate_run["required_read_set"]["project_when_present"]


def test_validate_run_contract_reads_slice_plan_when_present() -> None:
    contract = contract_by_skill(REPO_ROOT, "validate-run")
    assert contract is not None

    assert "docs/Implementation_Roadmap.md" in contract["required_read_set"][
        "project_when_present"
    ]


def test_stage_card_generator_renders_core_skill_boundaries() -> None:
    rendered = generate_stage_cards.render_stage_cards(REPO_ROOT)

    assert "# Detailed Workflow Stage Reference" in rendered
    assert "不是\noperator 的第一层入口" in rendered
    assert "visible aliases 选择" in rendered
    assert (
        "`$grill`, `$prepare`, `$build`, `$run`, `$analyze`, `$write`, `$change`"
        in rendered
    )
    assert "不是 autocomplete 入口" in rendered
    assert "## Explore" in rendered
    assert "## Contract & Plan" in rendered
    assert "## Build & Validate" in rendered
    assert "## Iterate & Release" in rendered
    assert "### WF8 Code Expert" in rendered
    assert "### WF10 Iterate" in rendered
    assert "怎么启动:" in rendered
    assert "完成后得到:" in rendered
    assert "深入阅读:" in rendered
    assert "[[stage:WF10|WF10 details]]" in rendered
    assert "[[skill:iterate|iterate Skill]]" in rendered
    assert "Can write:" not in rendered
    assert "Tool-owned outputs:" not in rendered
    assert "--output docs/Workflow_Stage_Cards.md" not in rendered


def test_stage_card_generator_writes_output(tmp_path: Path) -> None:
    output = tmp_path / "stage_cards.md"

    result = subprocess.run(
        [
            sys.executable,
            "tooling/codex_hooks/generate_stage_cards.py",
            "--workspace-root",
            str(REPO_ROOT),
            "--output",
            str(output),
        ],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    text = output.read_text(encoding="utf-8")
    assert "## Iterate & Release" in text
    assert "### WF12 Release" in text
    assert "详细排查时的读法" in text
    assert "Stage -> 一句话 -> 怎么启动 -> 完成后得到 -> 深入阅读" in text
    assert "[[skill:release|release Skill]]" in text
    assert "--output docs/Workflow_Stage_Cards.md" not in text


def test_workflow_handbook_stage_cards_match_generated_output() -> None:
    output = REPO_ROOT / "workflow_handbook" / "Workflow_Stage_Cards.md"

    expected = generate_stage_cards.render_stage_cards(REPO_ROOT)

    assert output.exists()
    assert output.read_text(encoding="utf-8") == expected


def test_workflow_handbook_keeps_visible_alias_entrypoints() -> None:
    handbook_dir = REPO_ROOT / "workflow_handbook"
    files = sorted(path.name for path in handbook_dir.glob("*.md"))

    assert files == [
        "Workflow_Operator_Handbook.md",
        "Workflow_Stage_Cards.md",
    ]
    handbook = (handbook_dir / "Workflow_Operator_Handbook.md").read_text(
        encoding="utf-8"
    )
    assert "Start Here" in handbook
    assert "Quick Action Index" in handbook
    assert "Visible Aliases" in handbook
    assert "内部执行细节不属于第一层界面" in handbook
    assert (
        "Intent\n"
        "  -> visible alias\n"
        "  -> internal runtime / typed request / worker result / Gate ledger\n"
        "  -> Human Approval or next safe action"
    ) in handbook
    assert "| `$grill` |" in handbook
    assert "| `$prepare` / `$build` |" in handbook
    assert "| `$run` / `$analyze` |" in handbook
    assert "| `$write` / `$change` |" in handbook
    assert "[[page:workflow_supervisor_model|Runtime Routing Model]]" in handbook
    assert "[[page:operator_task_index|Operator Action Index]]" in handbook
    assert "Daily Run Shape" in handbook
    assert "Detailed Reference" in handbook
    assert "[[page:stage_cards|Stage Reference]]" in handbook
    assert "Generated Views" in handbook
    assert "Currentness" in handbook
    assert "docs/_views/workflow_handbook_reference_index.json" in handbook
    assert "不要再在 `workflow_handbook/` 下新增平行叙事文档" in handbook

    html_plan = handbook_dir / "plans" / "HTML_Rendering_Handbook_Plan.md"
    assert html_plan.exists()
    plan_text = html_plan.read_text(encoding="utf-8")
    assert "workflow_handbook/pages/**" in plan_text
    assert "workflow_handbook_reference_index.schema.json" in plan_text


def test_hooks_json_references_existing_scripts() -> None:
    hooks = json.loads(
        (REPO_ROOT / "tooling/codex_hooks/hooks.json").read_text(encoding="utf-8")
    )
    commands: list[str] = []
    for groups in hooks["hooks"].values():
        for group in groups:
            for hook in group["hooks"]:
                commands.append(hook["command"])

    for script in [
        "user_prompt_submit.py",
        "pre_tool_use_policy.py",
        "post_tool_use_markers.py",
        "require_gate_ledger.py",
    ]:
        assert any(script in command for command in commands)
        assert (REPO_ROOT / "tooling" / "codex_hooks" / script).exists()


def test_user_scope_install_rewrites_to_copied_runtime(tmp_path: Path) -> None:
    runtime_dir = tmp_path / "harness_hooks"
    _copy_runtime_scripts(REPO_ROOT, runtime_dir)
    rendered = _load_hook_config(
        REPO_ROOT / "tooling/codex_hooks/hooks.json", runtime_dir
    )
    hooks = json.loads(rendered)

    commands = [
        hook["command"]
        for groups in hooks["hooks"].values()
        for group in groups
        for hook in group["hooks"]
    ]
    assert all(str(runtime_dir) in command for command in commands)
    assert all("tooling/codex_hooks" not in command for command in commands)
    assert (runtime_dir / "harness_contracts.py").exists()


def test_rule_template_installs_external_review_allow_rule(tmp_path: Path) -> None:
    codex_dir = tmp_path / ".codex"

    _copy_rule_templates(REPO_ROOT, codex_dir)

    rule = codex_dir / "rules" / "harness_external_review.rules"
    assert rule.exists()
    text = rule.read_text(encoding="utf-8")
    assert "harness_external_review.py" in text
    assert "agentic_review.py" in text


def test_user_scope_install_removes_external_review_allow_rule(tmp_path: Path) -> None:
    codex_dir = tmp_path / ".codex"
    _copy_rule_templates(REPO_ROOT, codex_dir)
    rule = codex_dir / "rules" / "harness_external_review.rules"
    assert rule.exists()

    _remove_rule_templates(codex_dir)

    assert not rule.exists()


def test_enable_feature_flag_updates_existing_features_table() -> None:
    text = (
        'model = "gpt-5.3-codex"\n\n'
        "[features]\nexperimental = true\n\n"
        "[tools]\nweb = true\n"
    )
    updated = _ensure_hooks_enabled(text)

    assert "[features]\nexperimental = true\nhooks = true\n\n[tools]" in updated
    assert updated.count("[features]") == 1


def test_enable_feature_flag_migrates_legacy_codex_hooks_flag() -> None:
    updated = _ensure_hooks_enabled("[features]\ncodex_hooks = true\n")

    assert updated == "[features]\nhooks = true\n"


def test_hook_status_reports_user_runtime_and_workspace_policy(tmp_path: Path) -> None:
    codex_dir = tmp_path / ".codex"
    runtime_dir = codex_dir / "harness_hooks"
    _copy_runtime_scripts(REPO_ROOT, runtime_dir)
    (codex_dir / "config.toml").write_text(
        "[features]\nhooks = true\n", encoding="utf-8"
    )
    (codex_dir / "hooks.json").write_text(
        _load_hook_config(REPO_ROOT / "tooling/codex_hooks/hooks.json", runtime_dir),
        encoding="utf-8",
    )

    status = build_status(REPO_ROOT, codex_dir=codex_dir)
    assert status["hooks_feature_enabled"] is True
    assert status["harness_workspace"] is True
    assert status["workspace_policy_effect"] == "active"
    assert status["user_hook_errors"] == []
    assert status["hook_install_ready"] is True


def test_hook_status_accepts_workspace_only_install(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    root.mkdir()
    (root / ".git").mkdir()
    (root / CONTRACTS_PATH).parent.mkdir(parents=True)
    (root / CONTRACTS_PATH).write_text(
        '{"contracts":[]}\n', encoding="utf-8"
    )
    (root / ".codex").mkdir()
    (root / ".codex/config.toml").write_text(
        "[features]\nhooks = true\n", encoding="utf-8"
    )
    (root / ".codex/hooks.json").write_text(
        (REPO_ROOT / "tooling/codex_hooks/hooks.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    status = build_status(root, codex_dir=tmp_path / "empty-user-codex")
    assert status["hooks_feature_enabled"] is True
    assert status["repo_hooks_feature_enabled"] is True
    assert status["user_hooks_exists"] is False
    assert status["user_hook_errors"] == []
    assert status["active_hook_source"] == "workspace"
    assert status["hook_install_ready"] is True


def test_hook_trust_summary_reports_review_required() -> None:
    response = {
        "result": {
            "data": [
                {
                    "cwd": str(REPO_ROOT),
                    "hooks": [
                        {
                            "eventName": "preToolUse",
                            "source": "project",
                            "sourcePath": str(REPO_ROOT / ".codex/hooks.json"),
                            "command": "python pre_tool_use_policy.py",
                            "enabled": True,
                            "currentHash": "sha256:abc",
                            "trustStatus": "untrusted",
                        },
                        {
                            "eventName": "stop",
                            "source": "project",
                            "sourcePath": str(REPO_ROOT / ".codex/hooks.json"),
                            "command": "python require_gate_ledger.py",
                            "enabled": False,
                            "currentHash": "sha256:def",
                            "trustStatus": "untrusted",
                        },
                    ],
                }
            ]
        }
    }

    entries = hook_trust_entries_from_response(response)
    summary = summarize_hook_trust(entries)

    assert summary["hook_trust_ready"] is False
    assert len(summary["hook_trust_review_required"]) == 1
    assert summary["hook_trust_review_required"][0]["event_name"] == "preToolUse"


def test_hook_status_can_include_codex_trust_state(monkeypatch) -> None:
    def fake_fetch(root: Path, home: Path) -> tuple[list[dict[str, object]], None]:
        return (
            [
                {
                    "cwd": root.as_posix(),
                    "event_name": "preToolUse",
                    "source": "project",
                    "source_path": (root / ".codex/hooks.json").as_posix(),
                    "command": "python pre_tool_use_policy.py",
                    "enabled": True,
                    "current_hash": "sha256:abc",
                    "trust_status": "trusted",
                }
            ],
            None,
        )

    monkeypatch.setattr(hook_status, "fetch_hook_trust_entries", fake_fetch)

    status = build_status(REPO_ROOT, include_trust_status=True)

    assert status["hook_trust_checked"] is True
    assert status["hook_trust_ready"] is True
    assert "- hook trust status: trusted" in render_status(status)


def test_fetch_hook_trust_entries_uses_initialize_and_initialized(
    monkeypatch,
) -> None:
    class FakeStdin:
        def __init__(self) -> None:
            self.chunks: list[str] = []
            self.closed = False

        def write(self, chunk: str) -> int:
            self.chunks.append(chunk)
            return len(chunk)

        def flush(self) -> None:
            return None

        def close(self) -> None:
            self.closed = True

        def getvalue(self) -> str:
            return "".join(self.chunks)

    class FakeProcess:
        def __init__(self) -> None:
            self.stdin = FakeStdin()
            self.stdout = StringIO()
            self._terminated = False

        def poll(self) -> int | None:
            return 0 if self._terminated else None

        def terminate(self) -> None:
            self._terminated = True

        def wait(self, timeout: float | None = None) -> int:
            self._terminated = True
            return 0

        def kill(self) -> None:
            self._terminated = True

    fake_process = FakeProcess()
    requests: list[tuple[int, float]] = []

    def fake_popen(*args, **kwargs) -> FakeProcess:
        return fake_process

    def fake_read(
        process: subprocess.Popen[str],
        request_id: int,
        timeout_seconds: float,
    ) -> dict[str, object]:
        requests.append((request_id, timeout_seconds))
        if request_id == 1:
            return {"id": 1, "result": {"userAgent": "codex"}}
        if request_id == 2:
            return {
                "id": 2,
                "result": {
                    "data": [
                        {
                            "cwd": REPO_ROOT.as_posix(),
                            "hooks": [
                                {
                                    "eventName": "preToolUse",
                                    "source": "project",
                                    "sourcePath": (
                                        REPO_ROOT / ".codex/hooks.json"
                                    ).as_posix(),
                                    "command": "python pre_tool_use_policy.py",
                                    "enabled": True,
                                    "currentHash": "sha256:abc",
                                    "trustStatus": "trusted",
                                }
                            ],
                        }
                    ]
                },
            }
        raise AssertionError(f"unexpected request id {request_id}")

    monkeypatch.setattr(subprocess, "Popen", fake_popen)
    monkeypatch.setattr(hook_status, "_read_json_rpc_response", fake_read)

    entries, error = hook_status.fetch_hook_trust_entries(
        REPO_ROOT, Path.home() / ".codex", timeout_seconds=3.0
    )

    assert error is None
    assert entries[0]["trust_status"] == "trusted"
    assert requests == [(1, 3.0), (2, 3.0)]

    written = [json.loads(line) for line in fake_process.stdin.getvalue().splitlines()]
    assert written[0]["method"] == "initialize"
    assert "jsonrpc" not in written[0]
    assert "capabilities" not in written[0]
    assert written[1] == {"method": "initialized"}
    assert written[2]["method"] == "hooks/list"
    assert "jsonrpc" not in written[2]


def test_fetch_hook_trust_entries_reports_app_server_exit(monkeypatch) -> None:
    class FakeStdin:
        def __init__(self) -> None:
            self.chunks: list[str] = []
            self.closed = False

        def write(self, chunk: str) -> int:
            self.chunks.append(chunk)
            return len(chunk)

        def flush(self) -> None:
            return None

        def close(self) -> None:
            self.closed = True

    class FakeProcess:
        def __init__(self) -> None:
            self.stdin = FakeStdin()
            self.stdout = StringIO()
            self.stderr = StringIO(
                "Codex could not find bubblewrap on PATH.\n"
                "Error: Read-only file system (os error 30)\n"
            )

        def poll(self) -> int | None:
            return 1

        def terminate(self) -> None:
            return None

        def wait(self, timeout: float | None = None) -> int:
            return 1

        def kill(self) -> None:
            return None

    fake_process = FakeProcess()

    def fake_popen(*args, **kwargs) -> FakeProcess:
        return fake_process

    monkeypatch.setattr(subprocess, "Popen", fake_popen)

    entries, error = hook_status.fetch_hook_trust_entries(
        REPO_ROOT, Path.home() / ".codex", timeout_seconds=3.0
    )

    assert entries == []
    assert error is not None
    assert "Codex app-server exited with code 1" in error
    assert "bubblewrap" in error


def _fake_check_contracts_status(
    root: Path,
    *,
    hook_trust_ready: bool,
    review_required: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    return {
        "hook_trust_ready": hook_trust_ready,
        "hook_trust_checked": True,
        "hook_trust_error": None,
        "hook_install_ready": True,
        "harness_workspace": True,
        "contract_path": str(root / CONTRACTS_PATH),
        "workspace_root": str(root),
        "workspace_policy_effect": "active",
        "codex_home": str(Path.home() / ".codex"),
        "hooks_feature_enabled": True,
        "active_hook_source": "workspace",
        "repo_hooks_feature_enabled": True,
        "repo_config": str(root / ".codex/config.toml"),
        "user_hooks_feature_enabled": True,
        "user_config": str(Path.home() / ".codex/config.toml"),
        "user_hooks_exists": False,
        "user_hooks": str(Path.home() / ".codex/hooks.json"),
        "user_runtime_exists": False,
        "user_runtime": str(Path.home() / ".codex/harness_hooks"),
        "repo_codex_kind": "directory",
        "repo_codex": str(root / ".codex"),
        "repo_hooks_exists": True,
        "repo_hooks": str(root / ".codex/hooks.json"),
        "user_hook_errors": [],
        "repo_hook_errors": [],
        "user_hook_commands": [],
        "repo_hook_commands": [],
        "hook_trust_review_required": review_required or [],
    }


def test_check_contracts_hook_status_can_fail_on_untrusted_hooks(
    monkeypatch,
    capsys,
) -> None:
    def fake_build_status(
        root: Path,
        include_trust_status: bool = False,
    ) -> dict[str, object]:
        assert include_trust_status is True
        return _fake_check_contracts_status(
            root,
            hook_trust_ready=False,
            review_required=[
                {
                    "event_name": "preToolUse",
                    "trust_status": "untrusted",
                    "current_hash": "sha256:abc",
                    "command": "python pre_tool_use_policy.py",
                }
            ],
        )

    monkeypatch.setattr(check_contracts, "build_status", fake_build_status)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "check_contracts.py",
            "--workspace-root",
            str(REPO_ROOT),
            "--hook-status",
            "--trust-status",
        ],
    )

    assert check_contracts.main() == 1
    assert "review required" in capsys.readouterr().out


def test_check_contracts_hook_status_passes_when_trusted(
    monkeypatch,
    capsys,
) -> None:
    def fake_build_status(
        root: Path,
        include_trust_status: bool = False,
    ) -> dict[str, object]:
        assert include_trust_status is True
        return _fake_check_contracts_status(root, hook_trust_ready=True)

    monkeypatch.setattr(check_contracts, "build_status", fake_build_status)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "check_contracts.py",
            "--workspace-root",
            str(REPO_ROOT),
            "--hook-status",
            "--trust-status",
        ],
    )

    assert check_contracts.main() == 0
    assert "hook trust status: trusted" in capsys.readouterr().out


def test_check_contracts_trust_status_requires_hook_status(monkeypatch) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "check_contracts.py",
            "--workspace-root",
            str(REPO_ROOT),
            "--trust-status",
        ],
    )

    with pytest.raises(SystemExit) as exc_info:
        check_contracts.main()

    assert exc_info.value.code == 2


def test_daily_context_lists_repo_guidance_files(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    root.mkdir()
    (root / ".git").mkdir()
    (root / CONTRACTS_PATH).parent.mkdir(parents=True)
    (root / CONTRACTS_PATH).write_text(
        '{"contracts":[]}\n', encoding="utf-8"
    )
    (root / "AGENTS.md").write_text("# Agent guidance\n", encoding="utf-8")
    (root / "CLAUDE.md").write_text("# Claude guidance\n", encoding="utf-8")

    context = daily_context_for_workspace(root)

    assert "Harness workspace capsule" in context
    assert "AGENTS.md" in context
    assert "CLAUDE.md" in context


def test_user_prompt_context_is_capped() -> None:
    context = truncate_user_prompt_context("x" * 5000)

    assert len(context) <= harness_contracts.USER_PROMPT_CONTEXT_MAX_CHARS
    assert "truncated Harness route context" in context


def test_command_reads_track_sliced_commit_rule_without_active_contract() -> None:
    event = {
        "tool_name": "Bash",
        "tool_input": {
            "command": f"sed -n '1,40p' {SLICED_COMMIT_RULE_PATH}",
        },
    }

    recorded = record_command_reads(
        REPO_ROOT,
        event["tool_input"]["command"],
        event,
    )

    assert SLICED_COMMIT_RULE_PATH in recorded
    assert SLICED_COMMIT_RULE_PATH in load_read_ledger(REPO_ROOT)["reads"]


def test_pre_tool_warns_git_commit_until_sliced_commit_rule_read() -> None:
    event = {
        "tool_name": "Bash",
        "tool_input": {"command": "git commit -m 'docs: update workflow'"},
    }

    notice = pre_tool_notice(REPO_ROOT, event)

    assert block_pre_tool(REPO_ROOT, event) is None
    assert notice is not None
    assert "sliced commit guidance" in notice
    assert SLICED_COMMIT_RULE_PATH in notice


def test_git_commit_detection_ignores_search_text() -> None:
    assert not is_git_commit_command("rg -n 'git commit' tooling/codex_hooks")
    assert is_git_commit_command("git status && git commit -m 'docs: update'")


def test_pre_tool_allows_git_commit_after_sliced_commit_rule_read() -> None:
    save_read_ledger(
        REPO_ROOT,
        {
            "reads": {
                SLICED_COMMIT_RULE_PATH: {
                    "events": [{"turn_id": "turn-1"}],
                    "sha256": "test",
                }
            }
        },
    )
    event = {
        "tool_name": "Bash",
        "tool_input": {
            "command": "git -c commit.gpgsign=false commit -m 'docs: update workflow'"
        },
    }

    assert block_pre_tool(REPO_ROOT, event) is None


def test_detect_skill_from_prompt() -> None:
    contract = detect_skill(REPO_ROOT, "请运行 $validate-run 并准备 WF10 readiness")
    assert contract is not None
    assert contract["skill"] == "validate-run"


def test_detection_maps_wf0_bootstrap_to_init_project() -> None:
    match = detect_skill_match(REPO_ROOT, "请执行 WF0 bootstrap init")

    assert match is not None
    assert match["skill"] is None
    assert match["candidate_skill"] == "init-project"
    assert match["trigger"] in {"wf0", "bootstrap init"}
    assert match["read_contract_stop_required"] is False


def test_detection_maps_init_alias_to_init_project() -> None:
    match = detect_skill_match(REPO_ROOT, "请运行 $init init")

    assert match is not None
    assert match["skill"] is None
    assert match["candidate_skill"] == "init-project"
    assert match["trigger"] == "$init"
    assert match["trigger_type"] == "explicit"


def test_detection_treats_explicit_init_project_update_as_write() -> None:
    prompt = "$init-project update"

    assert classify_prompt_intent(prompt) == "code_write"
    match = detect_skill_match(REPO_ROOT, prompt)

    assert match is not None
    assert match["skill"] is None
    assert match["candidate_skill"] == "init-project"
    assert match["trigger"] == "$init-project"
    assert match["trigger_type"] == "explicit"
    assert match["enforcement_mode"] == "context_only"


def test_detection_maps_update_from_grill_to_init_project() -> None:
    prompt = "$init-project update-from-grill"

    assert classify_prompt_intent(prompt) == "code_write"
    match = detect_skill_match(REPO_ROOT, prompt)

    assert match is not None
    assert match["candidate_skill"] == "init-project"
    assert match["trigger"] == "$init-project"
    assert match["trigger_type"] == "explicit"
    assert match["enforcement_mode"] == "context_only"


def test_detection_treats_bare_explicit_stage_skill_as_route_hint() -> None:
    match = detect_skill_match(REPO_ROOT, "$survey-idea")

    assert match is not None
    assert match["skill"] is None
    assert match["candidate_skill"] == "survey-idea"
    assert match["trigger"] == "$survey-idea"
    assert match["trigger_type"] == "explicit"
    assert match["intent_class"] == "unknown"
    assert match["enforcement_mode"] == "context_only"
    assert match["read_contract_stop_required"] is False


def test_detection_ignores_trigger_words_inside_file_paths() -> None:
    prompt = "Harness_Workflow_Implementation_Review.md 这个文件在哪？"
    assert classify_prompt_intent(prompt) == "code_search"
    assert detect_skill_match(REPO_ROOT, prompt) is None


def test_detection_treats_workflow_mapping_question_as_question() -> None:
    match = detect_skill_match(REPO_ROOT, "WF8 -> WF10 这个正确吗？")

    assert match is not None
    assert match["skill"] is None
    assert match["candidate_skill"] == "orchestrator"
    assert match["intent_class"] == "workflow_question"
    assert match["enforcement_mode"] == "context_only"


def test_detection_treats_hook_design_question_as_context_only() -> None:
    match = detect_skill_match(REPO_ROOT, "hook 的意图判断怎么完善？")

    assert match is not None
    assert match["skill"] is None
    assert match["candidate_skill"] == "harness-maintenance"
    assert match["intent_class"] == "design_discussion"
    assert match["enforcement_mode"] == "context_only"
    assert match["read_contract_stop_required"] is False


def test_intent_router_infers_prepare_stage() -> None:
    match = detect_skill_match(
        REPO_ROOT,
        "prepare 下载数据集并克隆 baseline，然后跑通 baseline smoke check",
    )

    assert match is not None
    assert match["candidate_skill"] == "workflow-supervisor"
    assert match["candidate_trigger_type"] == "intent_router"
    assert match["intent_route"]["route"] == "prepare"


def test_detection_does_not_let_llm_design_question_activate_write_scope() -> None:
    match = detect_skill_match(REPO_ROOT, "是否可以由 LLM 先判断意图然后选择 hook？")

    assert match is not None
    assert match["skill"] is None
    assert match["candidate_skill"] == "harness-maintenance"
    assert match["intent_class"] == "design_discussion"


def test_detection_question_markers_beat_write_verbs() -> None:
    assert classify_prompt_intent("这个方案应该怎么修改？") == "design_discussion"
    match = detect_skill_match(REPO_ROOT, "这个方案应该怎么修改？")
    assert match is None


@pytest.mark.parametrize(
    "prompt",
    [
        "$harness-maintenance 帮我修改 hook intent 分类，"
        "看看怎么让直接写入请求进 code_write",
        "$harness-maintenance please modify tooling/codex_hooks/harness_contracts.py "
        "so phrases like 帮我修改 still enter code_write even with 怎么 or 看看",
        "$harness-maintenance 修改一下各个 skill 权限，有些权限不对吧，"
        "检查下所有 skill 权限是否正确，然后进行修改",
    ],
)
def test_detection_direct_write_phrases_override_discussion_markers(
    prompt: str,
) -> None:
    assert classify_prompt_intent(prompt) == "code_write"
    match = detect_skill_match(REPO_ROOT, prompt)

    assert match is not None
    assert match["skill"] is None
    assert match["candidate_skill"] == "harness-maintenance"
    assert match["intent_class"] == "code_write"
    assert match["enforcement_mode"] == "context_only"


def test_detection_explicit_harness_design_question_stays_advisory() -> None:
    prompt = "$harness-maintenance hook 的意图判断怎么完善？"

    assert classify_prompt_intent(prompt) == "design_discussion"
    match = detect_skill_match(REPO_ROOT, prompt)

    assert match is not None
    assert match["skill"] is None
    assert match["candidate_skill"] == "harness-maintenance"
    assert match["intent_class"] == "design_discussion"
    assert match["enforcement_mode"] == "context_only"
    assert match["read_contract_stop_required"] is False


def test_detection_action_gates_bare_workflow_ids() -> None:
    match = detect_skill_match(REPO_ROOT, "这里提到 WF10 是否合适？")

    assert match is not None
    assert match["skill"] is None
    assert match["intent_class"] == "workflow_question"


def test_detection_action_gates_iterate_decision_vocabulary() -> None:
    match = detect_skill_match(REPO_ROOT, "NEXT_ROUND 是不是只能在 WF10 eval 后使用？")

    assert match is not None
    assert match["skill"] is None
    assert match["candidate_skill"] == "iterate"
    assert match["intent_class"] == "decision_question"


def test_detection_decision_questions_do_not_trigger_code_debug() -> None:
    match = detect_skill_match(REPO_ROOT, "DEBUG 和 PIVOT 的区别是什么？")

    assert match is not None
    assert match["skill"] is None
    assert match["candidate_skill"] == "iterate"
    assert match["intent_class"] == "decision_question"


def test_detection_exact_continue_decision_is_not_continuation() -> None:
    assert not detect_skill_match(REPO_ROOT, "continue")
    match = detect_skill_match(REPO_ROOT, "这里写 CONTINUE 是否合适？")

    assert match is not None
    assert match["skill"] is None
    assert match["intent_class"] == "decision_question"


def test_detection_routes_stage_lifecycle_to_orchestrator() -> None:
    match = detect_skill_match(REPO_ROOT, "进入 WF10")

    assert match is not None
    assert match["skill"] is None
    assert match["candidate_skill"] == "orchestrator"
    assert match["intent_class"] == "workflow_action"
    assert match["enforcement_mode"] == "context_only"


def test_detection_keeps_explicit_iterate_trigger_advisory() -> None:
    status = detect_skill_match(REPO_ROOT, "/iterate status")
    plan = detect_skill_match(REPO_ROOT, '$iterate plan "try smaller lr"')
    decision = detect_skill_match(REPO_ROOT, "$iterate eval CONTINUE")

    assert status is not None
    assert status["skill"] is None
    assert status["candidate_skill"] == "iterate"
    assert status["enforcement_mode"] == "context_only"
    assert plan is not None
    assert plan["skill"] is None
    assert plan["candidate_skill"] == "iterate"
    assert plan["enforcement_mode"] == "context_only"
    assert decision is not None
    assert decision["skill"] is None
    assert decision["candidate_skill"] == "iterate"
    assert decision["enforcement_mode"] == "context_only"


def test_detection_infers_code_debug_for_ordinary_code_modification() -> None:
    match = detect_skill_match(REPO_ROOT, "帮我修改 Python 模块中的数据处理逻辑")

    assert match is not None
    assert match["skill"] is None
    assert match["candidate_skill"] == "code-debug"
    assert match["trigger_type"] == "inferred"
    assert match["intent_class"] == "code_write"
    assert match["read_contract_stop_required"] is False


def test_detection_infers_harness_maintenance_for_skill_detection() -> None:
    match = detect_skill_match(
        REPO_ROOT, "帮我修改 Skill Detection 和 read-only/code-search 相关内容"
    )

    assert match is not None
    assert match["skill"] is None
    assert match["candidate_skill"] == "harness-maintenance"
    assert match["trigger_type"] in {"implicit", "inferred"}
    assert match["intent_class"] == "code_write"
    assert match["read_contract_stop_required"] is False


def test_detection_infers_harness_maintenance_for_hook_trigger_text() -> None:
    match = detect_skill_match(REPO_ROOT, "帮我修改 hook的判断和触发")

    assert match is not None
    assert match["skill"] is None
    assert match["candidate_skill"] == "harness-maintenance"
    assert match["trigger_type"] in {"implicit", "inferred"}


def test_detection_infers_harness_maintenance_over_generic_fix() -> None:
    match = detect_skill_match(REPO_ROOT, "fix hooks trust routing")

    assert match is not None
    assert match["skill"] is None
    assert match["candidate_skill"] == "harness-maintenance"
    assert match["trigger_type"] == "inferred"
    assert match["intent_class"] == "code_write"


def test_detection_treats_explicit_harness_maintenance_fix_as_write() -> None:
    match = detect_skill_match(
        REPO_ROOT,
        "$harness-maintenance 修复 AI_AGENT_SETUP.md 的临时源目录清理说明",
    )

    assert match is not None
    assert match["skill"] is None
    assert match["candidate_skill"] == "harness-maintenance"
    assert match["trigger_type"] == "explicit"
    assert match["intent_class"] == "code_write"
    assert match["enforcement_mode"] == "context_only"


def test_detection_routes_ai_agent_setup_writes_to_harness_maintenance() -> None:
    match = detect_skill_match(
        REPO_ROOT,
        "现在这个 AI_AGENT_SETUP.md 有问题，"
        "将文件复制出去之后没有引导 LLM 删除临时目录",
    )

    assert match is not None
    assert match["skill"] is None
    assert match["candidate_skill"] == "harness-maintenance"
    assert match["trigger_type"] == "inferred"
    assert match["intent_class"] == "code_write"
    assert match["enforcement_mode"] == "context_only"


def test_detection_keeps_ai_agent_setup_question_context_only() -> None:
    match = detect_skill_match(REPO_ROOT, "AI_AGENT_SETUP.md 应该怎么修改？")

    assert match is not None
    assert match["skill"] is None
    assert match["candidate_skill"] == "harness-maintenance"
    assert match["intent_class"] == "design_discussion"
    assert match["enforcement_mode"] == "context_only"


def test_detection_infers_single_owner_for_commit_prompt(monkeypatch) -> None:
    monkeypatch.setattr(
        harness_contracts,
        "changed_paths",
        lambda root: [
            "AI_AGENT_SETUP.md",
            "tooling/.tests/test_codex_hooks_contracts.py",
            "tooling/codex_hooks/harness_contracts.py",
        ],
    )

    match = detect_skill_match(REPO_ROOT, "帮我把这次的 git 提交了把")

    assert match is not None
    assert match["skill"] is None
    assert match["candidate_skill"] == "harness-maintenance"
    assert match["trigger"] == "changed_paths_single_owner"
    assert match["trigger_type"] == "inferred"
    assert match["intent_class"] == "code_write"
    assert match["enforcement_mode"] == "context_only"


def test_detection_keeps_mixed_owner_commit_prompt_inactive(monkeypatch) -> None:
    monkeypatch.setattr(
        harness_contracts,
        "changed_paths",
        lambda root: [
            "AI_AGENT_SETUP.md",
            "src/pipeline.py",
        ],
    )

    match = detect_skill_match(REPO_ROOT, "帮我把这次的 git 提交了把")

    assert match is not None
    assert match["skill"] is None
    assert match["candidate_skill"] is None
    assert match["trigger"] == "changed_paths_mixed_owner"
    assert match["intent_class"] == "code_write"
    assert match["enforcement_mode"] == "none"
    assert "Possible owners" in match["candidate_reason"]


def test_user_prompt_commit_single_owner_enters_candidate_context(
    monkeypatch,
    capsys,
) -> None:
    _clean_runtime()
    monkeypatch.setattr(
        harness_contracts,
        "changed_paths",
        lambda root: [
            "AI_AGENT_SETUP.md",
            "tooling/codex_hooks/harness_contracts.py",
        ],
    )
    monkeypatch.setattr(
        sys,
        "stdin",
        StringIO(
            json.dumps(
                {
                    "cwd": str(REPO_ROOT),
                    "prompt": "帮我把这次的 git 提交了把",
                    "session_id": "commit-session",
                    "turn_id": "commit-turn",
                }
            )
        ),
    )

    assert user_prompt_submit_main() == 0
    capsys.readouterr()

    session = load_session(REPO_ROOT)
    assert session["active_skill"] is None
    assert session["candidate_skill"] == "harness-maintenance"
    assert session["skill_trigger"] == "changed_paths_single_owner"
    assert session["enforcement_mode"] == "context_only"
    _clean_runtime()


def test_detection_infers_harness_maintenance_for_workflow_language() -> None:
    match = detect_skill_match(
        REPO_ROOT, "帮我优化 workflow 通用语言、关键概念和 Stage Card generator"
    )

    assert match is not None
    assert match["skill"] is None
    assert match["candidate_skill"] == "harness-maintenance"
    assert match["intent_class"] == "code_write"


def test_detection_does_not_treat_stage_card_as_commit_prompt(monkeypatch) -> None:
    monkeypatch.setattr(
        harness_contracts,
        "changed_paths",
        lambda root: [
            "AI_AGENT_SETUP.md",
            "src/pipeline.py",
        ],
    )

    match = detect_skill_match(
        REPO_ROOT, "帮我优化 workflow 通用语言、关键概念和 Stage Card generator"
    )

    assert match is not None
    assert match["skill"] is None
    assert match["candidate_skill"] == "harness-maintenance"
    assert match["trigger"] == "inferred_harness_maintenance"
    assert match["enforcement_mode"] == "context_only"


def test_detection_prefers_harness_maintenance_for_prompt_routing_terms() -> None:
    match = detect_skill_match(
        REPO_ROOT,
        "workflow 语言为什么被归到 code-debug，触发规则在哪里错了",
    )

    assert match is not None
    assert match["skill"] is None
    assert match["candidate_skill"] == "harness-maintenance"
    assert match["intent_class"] == "design_discussion"
    assert match["enforcement_mode"] == "context_only"
    assert match["trigger_type"] == "inferred"


def test_detection_keeps_mixed_workflow_question_context_only() -> None:
    match = detect_skill_match(
        REPO_ROOT,
        "帮我看下 prompt routing 和 workflow 触发规则怎么修改",
    )

    assert match is not None
    assert match["skill"] is None
    assert match["candidate_skill"] == "harness-maintenance"
    assert match["intent_class"] == "design_discussion"


def test_detection_keeps_imperative_workflow_trigger_advisory() -> None:
    match = detect_skill_match(
        REPO_ROOT,
        "帮我修改 prompt routing 和 workflow 触发规则",
    )

    assert match is not None
    assert match["skill"] is None
    assert match["candidate_skill"] == "harness-maintenance"
    assert match["intent_class"] == "code_write"
    assert match["enforcement_mode"] == "context_only"


def test_detection_infers_code_expert_for_new_implementation_request() -> None:
    match = detect_skill_match(REPO_ROOT, "帮我实现一个新的 Python 数据处理模块")
    assert match is not None
    assert match["skill"] is None
    assert match["candidate_skill"] == "code-expert"
    assert match["trigger_type"] == "inferred"


def test_detection_infers_code_review_for_diff_review_request() -> None:
    match = detect_skill_match(
        REPO_ROOT, "帮我对当前 git diff 做 code review，带上行号"
    )
    assert match is not None
    assert match["skill"] is None
    assert match["candidate_skill"] == "code-review"
    assert match["intent_class"] == "code_review_medium"
    assert match["read_contract_stop_required"] is False


def test_detection_keeps_explicit_code_review_review_only() -> None:
    match = detect_skill_match(REPO_ROOT, "$code-review heavy 当前 diff")

    assert match is not None
    assert match["skill"] is None
    assert match["candidate_skill"] == "code-review"
    assert match["trigger_type"] == "explicit"
    assert match["intent_class"] == "code_review_heavy"
    assert match["enforcement_mode"] == "context_only"
    assert match["read_contract_stop_required"] is False


def test_detection_infers_heavy_code_review_for_docs_evidence() -> None:
    match = detect_skill_match(
        REPO_ROOT, "对阶段文档和证据链做 heavy code review 交叉验证"
    )
    assert match is not None
    assert match["skill"] is None
    assert match["candidate_skill"] == "code-review"
    assert match["intent_class"] == "code_review_heavy"


def test_detection_classifies_cjk_adjacent_hook_review_as_heavy() -> None:
    prompt = "使用code review heavy 审查这套workflow"

    match = detect_skill_match(REPO_ROOT, prompt)

    assert match is not None
    assert match["skill"] is None
    assert match["candidate_skill"] == "code-review"
    assert match["intent_class"] == "code_review_heavy"


def test_detection_prefers_plain_code_debug_over_review_phrase() -> None:
    match = detect_skill_match(
        REPO_ROOT,
        "帮我修复上次 code review 中发现的问题 code-debug",
    )

    assert match is not None
    assert match["skill"] is None
    assert match["candidate_skill"] == "code-debug"
    assert match["trigger"] == "code-debug"


def test_user_prompt_continuation_preserves_heavy_review_session(
    monkeypatch, capsys
) -> None:
    _clean_runtime()
    monkeypatch.setattr(
        sys,
        "stdin",
        StringIO(
            json.dumps(
                {
                    "cwd": str(REPO_ROOT),
                    "prompt": "使用 code review heavy 来检查 workflow hook",
                    "session_id": "session-1",
                    "turn_id": "turn-1",
                }
            )
        ),
    )
    assert user_prompt_submit_main() == 0
    capsys.readouterr()
    save_read_ledger(
        REPO_ROOT,
        {"reads": {"AGENTS.md": {"events": [{"turn_id": "turn-1"}]}}},
    )

    monkeypatch.setattr(
        sys,
        "stdin",
        StringIO(
            json.dumps(
                {
                    "cwd": str(REPO_ROOT),
                    "prompt": "继续",
                    "session_id": "session-1",
                    "turn_id": "turn-2",
                }
            )
        ),
    )
    assert user_prompt_submit_main() == 0
    capsys.readouterr()

    session = load_session(REPO_ROOT)
    assert session["active_skill"] is None
    assert session["candidate_skill"] == "code-review"
    assert session["intent_class"] == "code_review_heavy"
    assert session["skill_trigger_type"] == "continuation"
    assert session["continued_from_previous_prompt"] is True
    assert "AGENTS.md" in load_read_ledger(REPO_ROOT)["reads"]
    event = {
        "tool_name": "Bash",
        "tool_input": {
            "command": (
                "python tooling/model_api/harness_external_review.py "
                "agentic --provider deepseek"
            )
        },
    }
    assert block_pre_tool(REPO_ROOT, event) is None
    _clean_runtime()


def test_nested_session_does_not_clobber_parent_heavy_review_wrapper_access(
    monkeypatch,
    capsys,
) -> None:
    _clean_runtime()
    monkeypatch.setattr(
        sys,
        "stdin",
        StringIO(
            json.dumps(
                {
                    "cwd": str(REPO_ROOT),
                    "prompt": "使用 code review heavy 来检查 workflow hook",
                    "session_id": "parent-session",
                    "turn_id": "parent-turn",
                }
            )
        ),
    )
    assert user_prompt_submit_main() == 0
    capsys.readouterr()
    contract = contract_by_skill(REPO_ROOT, "code-review")
    assert contract is not None
    save_read_ledger_for_event(
        REPO_ROOT,
        {"session_id": "parent-session"},
        {
            "reads": {
                path: {"events": [{"turn_id": "parent-turn"}]}
                for path in required_existing_files(REPO_ROOT, contract)
            }
        },
    )

    monkeypatch.setattr(
        sys,
        "stdin",
        StringIO(
            json.dumps(
                {
                    "cwd": str(REPO_ROOT),
                    "prompt": "Review this repository and fix workflow risks",
                    "session_id": "nested-session",
                    "turn_id": "nested-turn",
                }
            )
        ),
    )
    assert user_prompt_submit_main() == 0
    capsys.readouterr()
    assert load_session(REPO_ROOT)["session_id"] == "nested-session"

    event = {
        "session_id": "parent-session",
        "tool_name": "Bash",
        "tool_input": {
            "command": (
                "python tooling/model_api/harness_external_review.py "
                "agentic --provider deepseek --output "
                ".agents/state/review_traces/code-review/run05/review.md"
            )
        },
    }
    assert block_pre_tool(REPO_ROOT, event) is None
    _clean_runtime()


def test_user_prompt_continuation_does_not_cross_session_boundary(
    monkeypatch, capsys
) -> None:
    _clean_runtime()
    save_session(
        REPO_ROOT,
        {
            "session_id": "old-session",
            "active_skill": "code-review",
            "intent_class": "code_review_heavy",
        },
    )
    monkeypatch.setattr(
        sys,
        "stdin",
        StringIO(
            json.dumps(
                {
                    "cwd": str(REPO_ROOT),
                    "prompt": "continue",
                    "session_id": "new-session",
                    "turn_id": "turn-1",
                }
            )
        ),
    )

    assert user_prompt_submit_main() == 0
    capsys.readouterr()

    session = load_session(REPO_ROOT)
    assert not (
        session["active_skill"] == "code-review"
        and session["intent_class"] == "code_review_heavy"
    )
    event = {
        "tool_name": "Bash",
        "tool_input": {
            "command": (
                "python tooling/model_api/harness_external_review.py "
                "agentic --provider deepseek"
            )
        },
    }
    reason = block_pre_tool(REPO_ROOT, event)
    assert reason is not None
    assert "$code-review heavy" in reason
    _clean_runtime()


def test_user_prompt_context_only_writes_candidate_skill_not_active_skill(
    monkeypatch,
    capsys,
) -> None:
    _clean_runtime()
    monkeypatch.setattr(
        sys,
        "stdin",
        StringIO(
            json.dumps(
                {
                    "cwd": str(REPO_ROOT),
                    "prompt": "hook 的意图判断怎么完善？",
                    "session_id": "session-context",
                    "turn_id": "turn-1",
                }
            )
        ),
    )

    assert user_prompt_submit_main() == 0
    output = capsys.readouterr().out

    session = load_session(REPO_ROOT)
    assert session["active_skill"] is None
    assert session["candidate_skill"] == "harness-maintenance"
    assert session["enforcement_mode"] == "context_only"
    assert "Harness route hint: harness-maintenance" in output
    assert "Concrete tool calls are checked at tool time" in output
    _clean_runtime()


def test_user_prompt_writes_last_intent_route(monkeypatch, capsys) -> None:
    _clean_runtime()
    monkeypatch.setattr(
        sys,
        "stdin",
        StringIO(
            json.dumps(
                {
                    "cwd": str(REPO_ROOT),
                    "prompt": "prepare 下载数据集并克隆 baseline",
                    "session_id": "session-route",
                    "turn_id": "turn-route",
                }
            )
        ),
    )

    assert user_prompt_submit_main() == 0
    output = capsys.readouterr().out

    session = load_session(REPO_ROOT)
    route = json.loads((REPO_ROOT / LAST_ROUTE_PATH).read_text(encoding="utf-8"))
    assert session["candidate_skill"] == "workflow-supervisor"
    assert session["intent_route"]["route"] == "prepare"
    assert route["route"] == "prepare"
    assert "Intent route: prepare" in output
    _clean_runtime()


def test_user_prompt_context_only_continuation_does_not_silently_promote(
    monkeypatch,
    capsys,
) -> None:
    _clean_runtime()
    monkeypatch.setattr(
        sys,
        "stdin",
        StringIO(
            json.dumps(
                {
                    "cwd": str(REPO_ROOT),
                    "prompt": "hook 的意图判断怎么完善？",
                    "session_id": "session-context",
                    "turn_id": "turn-1",
                }
            )
        ),
    )
    assert user_prompt_submit_main() == 0
    capsys.readouterr()

    monkeypatch.setattr(
        sys,
        "stdin",
        StringIO(
            json.dumps(
                {
                    "cwd": str(REPO_ROOT),
                    "prompt": "那就按这个方案改",
                    "session_id": "session-context",
                    "turn_id": "turn-2",
                }
            )
        ),
    )
    assert user_prompt_submit_main() == 0
    capsys.readouterr()

    session = load_session(REPO_ROOT)
    assert session["active_skill"] is None
    assert session["candidate_skill"] == "harness-maintenance"
    assert session["pending_candidate_activation"] is True
    assert session["enforcement_mode"] == "context_only"
    _clean_runtime()


def test_user_prompt_continuation_requires_current_session_id(
    monkeypatch, capsys
) -> None:
    _clean_runtime()
    save_session(
        REPO_ROOT,
        {
            "session_id": "old-session",
            "active_skill": "code-review",
            "intent_class": "code_review_heavy",
            "read_contract_stop_required": True,
        },
    )
    save_read_ledger(
        REPO_ROOT,
        {"reads": {"AGENTS.md": {"events": [{"turn_id": "old-turn"}]}}},
    )
    monkeypatch.setattr(
        sys,
        "stdin",
        StringIO(
            json.dumps(
                {
                    "cwd": str(REPO_ROOT),
                    "prompt": "继续",
                    "turn_id": "turn-without-session",
                }
            )
        ),
    )

    assert user_prompt_submit_main() == 0
    capsys.readouterr()

    session = load_session(REPO_ROOT)
    assert session["active_skill"] is None
    assert session["skill_trigger_type"] is None
    assert session["intent_class"] == "unknown"
    assert load_read_ledger(REPO_ROOT)["reads"] == {}
    event = {
        "tool_name": "Bash",
        "tool_input": {
            "command": (
                "python tooling/model_api/harness_external_review.py "
                "agentic --provider deepseek"
            )
        },
    }
    reason = block_pre_tool(REPO_ROOT, event)
    assert reason is not None
    assert "$code-review heavy" in reason
    _clean_runtime()


def test_pre_tool_blocks_local_reference_git_add() -> None:
    event = {
        "tool_name": "Bash",
        "tool_input": {"command": "git add ref/Auto-claude-code-research-in-sleep"},
    }
    reason = block_pre_tool(REPO_ROOT, event)
    assert reason is not None
    assert "do not add" in reason


def test_pre_tool_blocks_mixed_manual_tool_owned_mutation() -> None:
    event = {
        "tool_name": "Bash",
        "tool_input": {
            "command": (
                "rm .evidence/review_packets/old.json && "
                "python tooling/evidence/check_dynamic_context.py --workspace-root ."
            )
        },
    }

    reason = block_pre_tool(REPO_ROOT, event)

    assert reason is not None
    assert "tool/controller-owned paths" in reason


def test_pre_tool_blocks_interpreter_write_to_tool_owned_path() -> None:
    event = {
        "tool_name": "Bash",
        "tool_input": {
            "command": (
                "python -c "
                "\"open('.evidence/review_packets/x.json', 'w').write('x')\""
            )
        },
    }

    reason = block_pre_tool(REPO_ROOT, event)

    assert reason is not None
    assert "tool/controller-owned paths" in reason


def test_pre_tool_blocks_manual_tool_owned_patch_delete(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    (root / CONTRACTS_PATH).parent.mkdir(parents=True)
    (root / CONTRACTS_PATH).write_text(
        '{"schema_version":"0.1","contracts":[]}\n',
        encoding="utf-8",
    )
    event = {
        "tool_name": "apply_patch",
        "tool_input": {
            "command": (
                "*** Begin Patch\n"
                "*** Delete File: "
                ".evidence/foo.json\n"
                "*** End Patch\n"
            )
        },
    }

    reason = block_pre_tool(root, event)

    assert reason is not None
    assert "manually patch" in reason


def test_pre_tool_blocks_manual_tool_owned_write_tool(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    (root / CONTRACTS_PATH).parent.mkdir(parents=True)
    (root / CONTRACTS_PATH).write_text(
        '{"schema_version":"0.1","contracts":[]}\n',
        encoding="utf-8",
    )
    event = {
        "tool_name": "Write",
        "tool_input": {"filePath": ".evidence/chains/wf9/evidence_chain.json"},
    }

    reason = block_pre_tool(root, event)

    assert reason is not None
    assert "do not manually edit or write" in reason
    assert ".evidence/chains/wf9/evidence_chain.json" in reason


def test_pre_tool_blocks_manual_generated_view_patch(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    (root / CONTRACTS_PATH).parent.mkdir(parents=True)
    (root / CONTRACTS_PATH).write_text(
        '{"schema_version":"0.1","contracts":[]}\n',
        encoding="utf-8",
    )
    event = {
        "tool_name": "apply_patch",
        "tool_input": {
            "command": (
                "*** Begin Patch\n"
                "*** Add File: docs/"
                "_site/index.html\n"
                "+<html></html>\n"
                "*** End Patch\n"
            )
        },
    }

    reason = block_pre_tool(root, event)

    assert reason is not None
    assert "docs/_site/**" in reason


def test_pre_tool_blocks_manual_auto_iterate_edit_tool(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    (root / CONTRACTS_PATH).parent.mkdir(parents=True)
    (root / CONTRACTS_PATH).write_text(
        '{"schema_version":"0.1","contracts":[]}\n',
        encoding="utf-8",
    )
    event = {
        "tool_name": "Edit",
        "tool_input": {"filePath": ".auto_iterate/state.json"},
    }

    reason = block_pre_tool(root, event)

    assert reason is not None
    assert "do not manually edit or write" in reason
    assert ".auto_iterate/state.json" in reason


def test_pre_tool_blocks_manual_workflow_supervisor_edit_tool(
    tmp_path: Path,
) -> None:
    root = tmp_path / "workspace"
    (root / CONTRACTS_PATH).parent.mkdir(parents=True)
    (root / CONTRACTS_PATH).write_text(
        '{"schema_version":"0.1","contracts":[]}\n',
        encoding="utf-8",
    )
    event = {
        "tool_name": "Write",
        "tool_input": {"filePath": ".workflow_supervisor/state.json"},
    }

    reason = block_pre_tool(root, event)

    assert reason is not None
    assert "do not manually edit or write" in reason
    assert ".workflow_supervisor/state.json" in reason


def test_pre_tool_allows_primary_evidence_tool_mutation() -> None:
    event = {
        "tool_name": "Bash",
        "tool_input": {
            "command": (
                "python tooling/evidence/approve_contract.py --workspace-root . "
                "--approval-source .evidence/review_packets/wf10/packet.md"
            )
        },
    }

    assert block_pre_tool(REPO_ROOT, event) is None


def test_pre_tool_allows_workflow_supervisor_tool_mutation() -> None:
    event = {
        "tool_name": "Bash",
        "tool_input": {
            "command": (
                "python tooling/workflow_supervisor/scripts/workflow_ctl.py "
                "--workspace-root . status --json"
            )
        },
    }

    assert block_pre_tool(REPO_ROOT, event) is None


def test_pre_tool_allows_worker_result_handoff_with_evidence_refs() -> None:
    event = {
        "tool_name": "Bash",
        "tool_input": {
            "command": (
                "cat > .agents/state/workflow_supervisor_worker_results/"
                "sup_20260614_000000/build_code_debug.worker_result.json <<'JSON'\n"
                "{\n"
                "  \"artifact_refs\": [\".evidence/chains/example/doc_audit.json\"]\n"
                "}\n"
                "JSON"
            )
        },
    }

    assert block_pre_tool(REPO_ROOT, event) is None


def test_pre_tool_allows_build_writes_to_implementation_surfaces() -> None:
    event = {
        "tool_name": "Bash",
        "tool_input": {
            "command": (
                "python - <<'PY'\n"
                "from pathlib import Path\n"
                "Path('src/model.py').write_text('pass\\n')\n"
                "Path('configs/train.yaml').write_text('epochs: 1\\n')\n"
                "PY"
            )
        },
    }

    assert block_pre_tool(REPO_ROOT, event) is None


def test_pre_tool_allows_grill_tool_owned_readiness_mutation() -> None:
    event = {
        "tool_name": "Bash",
        "tool_input": {
            "command": (
                "python tooling/grill/readiness.py --workspace-root . "
                "--output .workflow_supervisor/readiness.json "
                "--write-readiness"
            )
        },
    }

    assert block_pre_tool(REPO_ROOT, event) is None


def test_docs_site_renderer_outputs_are_stage_scoped_tool_outputs() -> None:
    command = "python tooling/evidence/build_docs_site.py --workspace-root ."
    event = {"tool_name": "Bash", "tool_input": {"command": command}}

    assert tool_owned_output_paths(REPO_ROOT, command) == [
        "docs/_views/",
        "docs/_site/",
    ]
    assert mutating_event_paths(REPO_ROOT, event) == [
        "docs/_views/",
        "docs/_site/",
    ]


def test_pre_tool_allows_docs_site_renderer_without_active_contract() -> None:
    _clean_runtime()
    save_session(REPO_ROOT, {"active_skill": None, "enforcement_mode": "none"})
    event = {
        "tool_name": "Bash",
        "tool_input": {
            "command": "python tooling/evidence/build_docs_site.py --workspace-root ."
        },
    }

    assert block_pre_tool(REPO_ROOT, event) is None
    _clean_runtime()


def test_code_debug_can_run_docs_site_renderer_after_required_reads() -> None:
    _clean_runtime()
    contract = contract_by_skill(REPO_ROOT, "code-debug")
    assert contract is not None
    save_session(REPO_ROOT, {"active_skill": "code-debug"})
    save_read_ledger(
        REPO_ROOT,
        {
            "reads": {
                path: {"events": []}
                for path in required_existing_files(REPO_ROOT, contract)
            }
        },
    )
    event = {
        "tool_name": "Bash",
        "tool_input": {
            "command": "python tooling/evidence/build_docs_site.py --workspace-root ."
        },
    }

    assert block_pre_tool(REPO_ROOT, event) is None
    _clean_runtime()


def test_approve_contract_python_variants_are_mutating() -> None:
    commands = [
        "python3 tooling/evidence/approve_contract.py --workspace-root .",
        "/usr/bin/python3.12 tooling/evidence/approve_contract.py --workspace-root .",
        "py tooling/evidence/approve_contract.py --workspace-root .",
    ]

    assert all(looks_mutating_bash(command) for command in commands)


def test_comparison_operators_are_not_shell_mutations() -> None:
    assert not looks_mutating_bash("awk 'NR>=620 && NR<=760 {print}' file.py")
    assert not looks_mutating_bash("python -c \"print(3 >= 2)\"")
    assert looks_mutating_bash("echo value > output.txt")
    assert looks_mutating_bash("echo value 2> error.log")


def test_pre_tool_allows_primary_evidence_tool_mutation_python3() -> None:
    event = {
        "tool_name": "Bash",
        "tool_input": {
            "command": (
                "python3 tooling/evidence/approve_contract.py --workspace-root . "
                "--approval-source .evidence/review_packets/wf10/packet.md"
            )
        },
    }

    assert block_pre_tool(REPO_ROOT, event) is None


def test_pre_tool_allows_primary_evidence_tool_mutation_dot_slash() -> None:
    event = {
        "tool_name": "Bash",
        "tool_input": {
            "command": (
                "python ./tooling/evidence/approve_contract.py --workspace-root . "
                "--approval-source .evidence/review_packets/wf10/packet.md"
            )
        },
    }

    assert block_pre_tool(REPO_ROOT, event) is None


def test_python_script_from_command_normalizes_workspace_paths() -> None:
    command = "python ./tooling/model_api/harness_external_review.py agentic"

    assert (
        python_script_from_command(REPO_ROOT, command)
        == "tooling/model_api/harness_external_review.py"
    )


def test_pre_tool_blocks_direct_external_review_script() -> None:
    _clean_runtime()
    save_session(
        REPO_ROOT,
        {"active_skill": "code-review", "intent_class": "code_review_heavy"},
    )
    event = {
        "tool_name": "Bash",
        "tool_input": {
            "command": "python tooling/model_api/agentic_review.py --provider deepseek"
        },
    }

    reason = block_pre_tool(REPO_ROOT, event)

    assert reason is not None
    assert "harness_external_review.py" in reason


def test_pre_tool_blocks_external_review_wrapper_outside_heavy_review() -> None:
    _clean_runtime()
    save_session(
        REPO_ROOT,
        {"active_skill": "code-review", "intent_class": "code_review_medium"},
    )
    event = {
        "tool_name": "Bash",
        "tool_input": {
            "command": (
                "python tooling/model_api/harness_external_review.py "
                "agentic --provider deepseek"
            )
        },
    }

    reason = block_pre_tool(REPO_ROOT, event)

    assert reason is not None
    assert "$code-review heavy" in reason


def test_pre_tool_allows_external_review_wrapper_for_heavy_review() -> None:
    _clean_runtime()
    save_session(
        REPO_ROOT,
        {"active_skill": "code-review", "intent_class": "code_review_heavy"},
    )
    event = {
        "tool_name": "Bash",
        "tool_input": {
            "command": (
                "python tooling/model_api/harness_external_review.py "
                "agentic --provider deepseek"
            )
        },
    }

    assert block_pre_tool(REPO_ROOT, event) is None


def test_pre_tool_blocks_external_review_wrapper_output_outside_trace() -> None:
    _clean_runtime()
    contract = contract_by_skill(REPO_ROOT, "code-review")
    assert contract is not None
    save_session(
        REPO_ROOT,
        {"active_skill": "code-review", "intent_class": "code_review_heavy"},
    )
    save_read_ledger(
        REPO_ROOT,
        {
            "reads": {
                path: {"events": []}
                for path in required_existing_files(REPO_ROOT, contract)
            }
        },
    )
    event = {
        "tool_name": "Bash",
        "tool_input": {
            "command": (
                "python tooling/model_api/harness_external_review.py "
                "agentic --provider deepseek --output README.md"
            )
        },
    }

    reason = block_pre_tool(REPO_ROOT, event)

    assert external_review_output_paths(
        REPO_ROOT,
        event["tool_input"]["command"],
    ) == ["README.md"]
    assert reason is not None
    assert "external review wrapper outputs" in reason
    _clean_runtime()


def test_pre_tool_allows_external_review_wrapper_output_inside_trace() -> None:
    _clean_runtime()
    contract = contract_by_skill(REPO_ROOT, "code-review")
    assert contract is not None
    save_session(
        REPO_ROOT,
        {"active_skill": "code-review", "intent_class": "code_review_heavy"},
    )
    save_read_ledger(
        REPO_ROOT,
        {
            "reads": {
                path: {"events": []}
                for path in required_existing_files(REPO_ROOT, contract)
            }
        },
    )
    event = {
        "tool_name": "Bash",
        "tool_input": {
            "command": (
                "python tooling/model_api/harness_external_review.py "
                "agentic --provider deepseek --output "
                ".agents/state/review_traces/code-review/run05/review.md"
            )
        },
    }

    assert block_pre_tool(REPO_ROOT, event) is None
    _clean_runtime()


def test_pre_tool_blocks_external_review_wrapper_shell_redirection() -> None:
    _clean_runtime()
    contract = contract_by_skill(REPO_ROOT, "code-review")
    assert contract is not None
    save_session(
        REPO_ROOT,
        {"active_skill": "code-review", "intent_class": "code_review_heavy"},
    )
    save_read_ledger(
        REPO_ROOT,
        {
            "reads": {
                path: {"events": []}
                for path in required_existing_files(REPO_ROOT, contract)
            }
        },
    )
    event = {
        "tool_name": "Bash",
        "tool_input": {
            "command": (
                "python tooling/model_api/harness_external_review.py "
                "agentic --provider deepseek --output "
                ".agents/state/review_traces/code-review/run05/review.md "
                "> README.md"
            )
        },
    }

    assert mutating_event_paths(REPO_ROOT, event) == [
        ".agents/state/review_traces/code-review/run05/review.md",
        "<bash mutation>",
    ]
    reason = block_pre_tool(REPO_ROOT, event)

    assert reason is not None
    assert "external review wrapper outputs" in reason
    _clean_runtime()


def test_pre_tool_warns_write_before_recommended_reads() -> None:
    _clean_runtime()
    save_session(REPO_ROOT, {"active_skill": "validate-run"})
    event = {
        "tool_name": "apply_patch",
        "tool_input": {
            "command": "*** Begin Patch\n"
            "*** Update File: README.md\n"
            "@@\n-test\n+test\n"
            "*** End Patch\n"
        },
    }
    assert block_pre_tool(REPO_ROOT, event) is None
    notice = pre_tool_notice(REPO_ROOT, event)
    assert notice is not None
    assert "recommended reads are missing" in notice
    assert "AGENTS.md" in notice
    _clean_runtime()


def test_pre_tool_allows_write_outside_advisory_stage_scope() -> None:
    _clean_runtime()
    contract = contract_by_skill(REPO_ROOT, "validate-run")
    assert contract is not None
    save_session(REPO_ROOT, {"active_skill": "validate-run"})
    save_read_ledger(
        REPO_ROOT,
        {
            "reads": {
                path: {"events": []}
                for path in required_existing_files(REPO_ROOT, contract)
            }
        },
    )
    event = {
        "tool_name": "apply_patch",
        "tool_input": {
            "command": "*** Begin Patch\n"
            "*** Update File: README.md\n"
            "@@\n-test\n+test\n"
            "*** End Patch\n"
        },
    }

    assert block_pre_tool(REPO_ROOT, event) is None
    _clean_runtime()


def test_pre_tool_allows_write_inside_active_stage_scope() -> None:
    _clean_runtime()
    contract = contract_by_skill(REPO_ROOT, "validate-run")
    assert contract is not None
    save_session(REPO_ROOT, {"active_skill": "validate-run"})
    save_read_ledger(
        REPO_ROOT,
        {
            "reads": {
                path: {"events": []}
                for path in required_existing_files(REPO_ROOT, contract)
            }
        },
    )
    event = {
        "tool_name": "apply_patch",
        "tool_input": {
            "command": "*** Begin Patch\n"
            "*** Update File: docs/Validate_Run_Report.md\n"
            "@@\n-test\n+test\n"
            "*** End Patch\n"
        },
    }

    assert block_pre_tool(REPO_ROOT, event) is None
    _clean_runtime()


def test_pre_tool_allows_workflow_subject_write_without_read_mode_block() -> None:
    _clean_runtime()
    contract = contract_by_skill(REPO_ROOT, "iterate")
    assert contract is not None
    save_session(
        REPO_ROOT,
        {"candidate_skill": "iterate", "enforcement_mode": "context_only"},
    )
    save_read_ledger(
        REPO_ROOT,
        {
            "reads": {
                path: {"events": []}
                for path in required_existing_files(REPO_ROOT, contract)
            }
        },
    )
    event = {
        "tool_name": "apply_patch",
        "tool_input": {
            "command": "*** Begin Patch\n"
            "*** Update File: iteration_log.json\n"
            "@@\n-{}\n+{}\n"
            "*** End Patch\n"
        },
    }

    assert block_pre_tool(REPO_ROOT, event) is None
    _clean_runtime()


def test_pre_tool_warns_guardrail_write_without_active_contract() -> None:
    _clean_runtime()
    save_session(REPO_ROOT, {"active_skill": None, "enforcement_mode": "none"})
    event = {
        "tool_name": "apply_patch",
        "tool_input": {
            "command": "*** Begin Patch\n"
            "*** Update File: tooling/codex_hooks/harness_contracts.py\n"
            "@@\n-test\n+test\n"
            "*** End Patch\n"
        },
    }

    assert block_pre_tool(REPO_ROOT, event) is None
    notice = pre_tool_notice(REPO_ROOT, event)
    assert notice is not None
    assert "paths map to Harness workflow ownership" in notice
    assert "harness-maintenance" in notice
    assert load_session(REPO_ROOT).get("active_skill") is None
    _clean_runtime()


def test_pre_tool_warns_contract_owned_write_without_active_contract() -> None:
    _clean_runtime()
    save_session(REPO_ROOT, {"active_skill": None, "enforcement_mode": "none"})
    event = {
        "tool_name": "apply_patch",
        "tool_input": {
            "command": "*** Begin Patch\n"
            "*** Update File: docs/Validate_Run_Report.md\n"
            "@@\n-test\n+test\n"
            "*** End Patch\n"
        },
    }

    assert block_pre_tool(REPO_ROOT, event) is None
    notice = pre_tool_notice(REPO_ROOT, event)
    assert notice is not None
    assert "paths map to Harness workflow ownership" in notice
    assert "validate-run" in notice
    assert load_session(REPO_ROOT).get("active_skill") is None
    _clean_runtime()


def test_pre_tool_warns_for_ambiguous_docs_write() -> None:
    _clean_runtime()
    save_session(REPO_ROOT, {"active_skill": None, "enforcement_mode": "none"})
    event = {
        "tool_name": "apply_patch",
        "tool_input": {
            "command": "*** Begin Patch\n"
            "*** Add File: docs/Some_New_Report.md\n"
            "+# Some New Report\n"
            "*** End Patch\n"
        },
    }

    assert block_pre_tool(REPO_ROOT, event) is None
    notice = pre_tool_notice(REPO_ROOT, event)
    assert notice is not None
    assert "paths map to Harness workflow ownership" in notice
    assert "harness-maintenance" in notice
    assert "init-project" in notice
    assert "release" in notice
    assert load_session(REPO_ROOT).get("active_skill") is None
    _clean_runtime()


def test_pre_tool_warns_guardrail_bash_token_without_active_contract() -> None:
    _clean_runtime()
    save_session(REPO_ROOT, {"active_skill": None, "enforcement_mode": "none"})
    event = {
        "tool_name": "Bash",
        "tool_input": {"command": "echo test > tooling/codex_hooks/tmp.txt"},
    }

    assert block_pre_tool(REPO_ROOT, event) is None
    notice = pre_tool_notice(REPO_ROOT, event)
    assert notice is not None
    assert "harness-maintenance" in notice
    _clean_runtime()


def test_pre_tool_explicit_write_scope_overrides_sensitive_paths(
    tmp_path: Path,
) -> None:
    root = tmp_path / "workspace"
    root.mkdir()
    _write_contracts(
        root,
        [
            {
                "skill": "scoped-stage",
                "triggers": [],
                "required_read_set": {},
                "required_actions": [],
                "forbidden_actions": [],
                "gate_ledger_required_when": [],
                "sensitive_paths": ["docs/"],
                "write_scope": {"allowed_paths": ["reports/"]},
            }
        ],
    )
    save_session(root, {"active_skill": "scoped-stage"})
    blocked = {
        "tool_name": "apply_patch",
        "tool_input": {
            "command": "*** Begin Patch\n"
            "*** Add File: docs/Blocked.md\n"
            "+# Blocked\n"
            "*** End Patch\n"
        },
    }
    allowed = {
        "tool_name": "apply_patch",
        "tool_input": {
            "command": "*** Begin Patch\n"
            "*** Add File: reports/Allowed.md\n"
            "+# Allowed\n"
            "*** End Patch\n"
        },
    }

    assert block_pre_tool(root, blocked) is None
    assert block_pre_tool(root, allowed) is None


def test_pre_tool_missing_write_scope_no_longer_fails_closed(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    root.mkdir()
    _write_contracts(
        root,
        [
            {
                "skill": "legacy-stage",
                "triggers": [],
                "required_read_set": {},
                "required_actions": [],
                "forbidden_actions": [],
                "gate_ledger_required_when": [],
                "sensitive_paths": ["docs/"],
            }
        ],
    )
    save_session(root, {"active_skill": "legacy-stage"})
    event = {
        "tool_name": "apply_patch",
        "tool_input": {
            "command": "*** Begin Patch\n"
            "*** Add File: docs/Legacy.md\n"
            "+# Legacy\n"
            "*** End Patch\n"
        },
    }

    assert block_pre_tool(root, event) is None


def test_stop_allows_read_only_implicit_skill_without_writes() -> None:
    _clean_runtime()
    save_session(
        REPO_ROOT,
        {
            "active_skill": "code-expert",
            "intent_class": "code_search",
            "read_contract_stop_required": False,
            "mutating_tool_seen": False,
        },
    )
    assert (
        stop_decision(REPO_ROOT, {"last_assistant_message": "It is at repo root."})
        is None
    )
    _clean_runtime()


def test_stop_allows_explicit_skill_missing_reads() -> None:
    _clean_runtime()
    save_session(
        REPO_ROOT,
        {
            "active_skill": "code-expert",
            "intent_class": "unknown",
            "read_contract_stop_required": True,
            "mutating_tool_seen": False,
        },
    )
    decision = stop_decision(REPO_ROOT, {"last_assistant_message": "Done."})
    assert decision is None
    _clean_runtime()


def test_stop_allows_implicit_skill_after_mutation_if_reads_missing() -> None:
    _clean_runtime()
    save_session(
        REPO_ROOT,
        {
            "active_skill": "code-debug",
            "intent_class": "code_write",
            "read_contract_stop_required": False,
            "mutating_tool_seen": False,
        },
    )
    mark_tool_activity(
        REPO_ROOT,
        {
            "toolName": "apply_patch",
            "input": {
                "patch": "*** Begin Patch\n"
                "*** Update File: README.md\n"
                "@@\n-a\n+b\n"
                "*** End Patch\n"
            },
        },
    )
    decision = stop_decision(REPO_ROOT, {"last_assistant_message": "Done."})
    assert decision is None
    _clean_runtime()


def test_stop_allows_inferred_code_review_missing_reads_without_writes() -> None:
    _clean_runtime()
    save_session(
        REPO_ROOT,
        {
            "active_skill": "code-review",
            "intent_class": "code_review_medium",
            "read_contract_stop_required": True,
            "mutating_tool_seen": False,
        },
    )
    decision = stop_decision(REPO_ROOT, {"last_assistant_message": "Done."})
    assert decision is None
    _clean_runtime()


def test_pre_tool_blocks_subject_writes_during_code_review() -> None:
    _clean_runtime()
    contract = contract_by_skill(REPO_ROOT, "code-review")
    assert contract is not None
    save_session(REPO_ROOT, {"active_skill": "code-review"})
    save_read_ledger(
        REPO_ROOT,
        {
            "reads": {
                path: {"events": []}
                for path in required_existing_files(REPO_ROOT, contract)
            }
        },
    )
    event = {
        "tool_name": "apply_patch",
        "tool_input": {
            "command": "*** Begin Patch\n"
            "*** Update File: src/example.py\n"
            "@@\n-a\n+b\n"
            "*** End Patch\n"
        },
    }
    reason = block_pre_tool(REPO_ROOT, event)
    assert reason is not None
    assert "review-only" in reason
    _clean_runtime()


def test_pre_tool_allows_code_review_trace_writes() -> None:
    _clean_runtime()
    contract = contract_by_skill(REPO_ROOT, "code-review")
    assert contract is not None
    save_session(REPO_ROOT, {"active_skill": "code-review"})
    save_read_ledger(
        REPO_ROOT,
        {
            "reads": {
                path: {"events": []}
                for path in required_existing_files(REPO_ROOT, contract)
            }
        },
    )
    event = {
        "tool_name": "apply_patch",
        "tool_input": {
            "command": "*** Begin Patch\n"
            "*** Add File: .agents/state/review_traces/code-review/"
            "2026-05-04_run01/review_report.md\n"
            "+# Report\n"
            "*** End Patch\n"
        },
    }
    assert block_pre_tool(REPO_ROOT, event) is None
    _clean_runtime()


def test_pre_tool_warns_code_debug_hook_guardrail_write() -> None:
    _clean_runtime()
    contract = contract_by_skill(REPO_ROOT, "code-debug")
    assert contract is not None
    save_session(REPO_ROOT, {"active_skill": "code-debug"})
    save_read_ledger(
        REPO_ROOT,
        {
            "reads": {
                path: {"events": []}
                for path in required_existing_files(REPO_ROOT, contract)
            }
        },
    )
    event = {
        "tool_name": "apply_patch",
        "tool_input": {
            "command": "*** Begin Patch\n"
            "*** Update File: tooling/codex_hooks/README.md\n"
            "@@\n-test\n+test\n"
            "*** End Patch\n"
        },
    }

    assert block_pre_tool(REPO_ROOT, event) is None
    notice = pre_tool_notice(REPO_ROOT, event)
    assert notice is not None
    assert "recommended reads are missing" in notice
    _clean_runtime()


def test_pre_tool_allows_harness_maintenance_guardrail_write() -> None:
    _clean_runtime()
    contract = contract_by_skill(REPO_ROOT, "harness-maintenance")
    assert contract is not None
    save_session(REPO_ROOT, {"active_skill": "harness-maintenance"})
    save_read_ledger(
        REPO_ROOT,
        {
            "reads": {
                path: {"events": []}
                for path in required_existing_files(REPO_ROOT, contract)
            }
        },
    )
    event = {
        "tool_name": "apply_patch",
        "tool_input": {
            "command": "*** Begin Patch\n"
            "*** Update File: tooling/codex_hooks/README.md\n"
            "@@\n-test\n+test\n"
            "*** End Patch\n"
        },
    }

    assert block_pre_tool(REPO_ROOT, event) is None
    _clean_runtime()


def test_pre_tool_allows_single_owner_git_add_for_active_owner(monkeypatch) -> None:
    _clean_runtime()
    monkeypatch.setattr(
        harness_contracts,
        "changed_paths",
        lambda root: [
            "AI_AGENT_SETUP.md",
            "tooling/codex_hooks/harness_contracts.py",
        ],
    )
    contract = contract_by_skill(REPO_ROOT, "harness-maintenance")
    assert contract is not None
    save_session(
        REPO_ROOT,
        {
            "active_skill": "harness-maintenance",
            "enforcement_mode": "context_only",
        },
    )
    save_read_ledger(
        REPO_ROOT,
        {
            "reads": {
                path: {"events": []}
                for path in required_existing_files(REPO_ROOT, contract)
            }
        },
    )
    event = {"tool_name": "Bash", "tool_input": {"command": "git add -A"}}

    assert block_pre_tool(REPO_ROOT, event) is None
    _clean_runtime()


def test_pre_tool_warns_mixed_owner_git_add_for_active_owner(monkeypatch) -> None:
    _clean_runtime()
    monkeypatch.setattr(
        harness_contracts,
        "changed_paths",
        lambda root: [
            "AI_AGENT_SETUP.md",
            "src/pipeline.py",
        ],
    )
    contract = contract_by_skill(REPO_ROOT, "harness-maintenance")
    assert contract is not None
    save_session(
        REPO_ROOT,
        {
            "active_skill": "harness-maintenance",
            "enforcement_mode": "context_only",
        },
    )
    save_read_ledger(
        REPO_ROOT,
        {
            "reads": {
                path: {"events": []}
                for path in required_existing_files(REPO_ROOT, contract)
            }
        },
    )
    event = {"tool_name": "Bash", "tool_input": {"command": "git add -A"}}

    assert block_pre_tool(REPO_ROOT, event) is None
    notice = pre_tool_notice(REPO_ROOT, event)
    assert notice is not None
    assert "one owner" in notice
    assert "AI_AGENT_SETUP.md" in notice
    _clean_runtime()


def test_pre_tool_blocks_mixed_bash_write_during_code_review() -> None:
    _clean_runtime()
    contract = contract_by_skill(REPO_ROOT, "code-review")
    assert contract is not None
    save_session(REPO_ROOT, {"active_skill": "code-review"})
    save_read_ledger(
        REPO_ROOT,
        {
            "reads": {
                path: {"events": []}
                for path in required_existing_files(REPO_ROOT, contract)
            }
        },
    )
    event = {
        "tool_name": "Bash",
        "tool_input": {
            "command": (
                "mkdir -p .agents/state/review_traces/code-review/run01 "
                "&& git add README.md"
            )
        },
    }

    assert mutating_event_paths(REPO_ROOT, event) == ["<bash mutation>"]
    reason = block_pre_tool(REPO_ROOT, event)

    assert reason is not None
    assert "review-only" in reason
    _clean_runtime()


def test_post_tool_records_required_read_files() -> None:
    _clean_runtime()
    save_session(REPO_ROOT, {"active_skill": "validate-run"})
    event = {
        "hook_event_name": "PostToolUse",
        "turn_id": "turn-test",
        "tool_name": "Bash",
    }
    recorded = record_command_reads(
        REPO_ROOT,
        "nl -ba .agents/skills/validate-run/SKILL.md "
        ".agents/references/workflow-guide.md",
        event,
    )
    assert ".agents/skills/validate-run/SKILL.md" in recorded
    assert ".agents/references/workflow-guide.md" in recorded
    ledger = load_read_ledger(REPO_ROOT)
    assert ".agents/skills/validate-run/SKILL.md" in ledger["reads"]
    assert (REPO_ROOT / READ_LEDGER_PATH).exists()
    _clean_runtime()


def test_post_tool_only_reports_new_read_files() -> None:
    _clean_runtime()
    save_session(REPO_ROOT, {"active_skill": "validate-run"})
    event = {
        "hook_event_name": "PostToolUse",
        "turn_id": "turn-test",
        "tool_name": "Bash",
    }
    command = "nl -ba .agents/skills/validate-run/SKILL.md"

    first = record_command_reads(REPO_ROOT, command, event)
    second = record_command_reads(REPO_ROOT, command, event)

    assert first == [".agents/skills/validate-run/SKILL.md"]
    assert second == []
    ledger = load_read_ledger(REPO_ROOT)
    assert (
        len(ledger["reads"][".agents/skills/validate-run/SKILL.md"]["events"])
        == 2
    )
    _clean_runtime()


def test_post_tool_does_not_credit_required_read_from_piped_path_mention() -> None:
    _clean_runtime()
    save_session(REPO_ROOT, {"active_skill": "validate-run"})
    event = {
        "hook_event_name": "PostToolUse",
        "turn_id": "turn-test",
        "tool_name": "Bash",
    }

    recorded = record_command_reads(
        REPO_ROOT,
        "rg --files | rg '.agents/skills/validate-run/SKILL.md'",
        event,
    )

    assert recorded == []
    assert load_read_ledger(REPO_ROOT) == {"reads": {}}
    _clean_runtime()


def test_user_prompt_resets_stale_read_ledger(monkeypatch, capsys) -> None:
    _clean_runtime()
    contract = contract_by_skill(REPO_ROOT, "validate-run")
    assert contract is not None
    save_read_ledger(
        REPO_ROOT,
        {
            "reads": {
                path: {"events": [{"turn_id": "old-turn"}]}
                for path in required_existing_files(REPO_ROOT, contract)
            }
        },
    )
    monkeypatch.setattr(
        sys,
        "stdin",
        StringIO(
            json.dumps(
                {
                    "cwd": str(REPO_ROOT),
                    "prompt": "run $validate-run",
                    "turn_id": "new-turn",
                }
            )
        ),
    )

    assert user_prompt_submit_main() == 0
    capsys.readouterr()

    assert load_read_ledger(REPO_ROOT) == {"reads": {}}
    decision = stop_decision(
        REPO_ROOT,
        {"last_assistant_message": "Done.", "stop_hook_active": False},
    )
    assert decision is None
    _clean_runtime()


def test_reset_read_ledger_clears_recorded_reads() -> None:
    _clean_runtime()
    save_read_ledger(REPO_ROOT, {"reads": {"AGENTS.md": {"events": []}}})

    reset_read_ledger(REPO_ROOT)

    assert load_read_ledger(REPO_ROOT) == {"reads": {}}
    _clean_runtime()


def test_event_read_ledger_merges_global_and_session_reads() -> None:
    _clean_runtime()
    event = {
        "hookEventName": "PostToolUse",
        "session_id": "patch-tool",
        "turn_id": "turn-test",
        "toolName": "Read",
    }
    save_read_ledger(
        REPO_ROOT,
        {
            "reads": {
                "AGENTS.md": {
                    "sha256": "global",
                    "events": [{"source": "global"}],
                }
            }
        },
    )
    session_ledger = REPO_ROOT / READ_LEDGERS_DIR / "patch-tool.json"
    session_ledger.parent.mkdir(parents=True, exist_ok=True)
    session_ledger.write_text(
        json.dumps(
            {
                "reads": {
                    "CLAUDE.md": {
                        "sha256": "session",
                        "events": [{"source": "session"}],
                    }
                }
            }
        )
        + "\n",
        encoding="utf-8",
    )

    ledger = load_read_ledger_for_event(REPO_ROOT, event)

    assert set(ledger["reads"]) == {"AGENTS.md", "CLAUDE.md"}
    _clean_runtime()


def test_record_read_does_not_drop_global_reads_when_session_ledger_exists() -> None:
    _clean_runtime()
    event = {
        "hookEventName": "PostToolUse",
        "session_id": "patch-tool",
        "turn_id": "turn-test",
        "toolName": "Read",
    }
    save_read_ledger(
        REPO_ROOT,
        {
            "reads": {
                "AGENTS.md": {
                    "sha256": "global",
                    "events": [{"source": "global"}],
                }
            }
        },
    )
    session_ledger = REPO_ROOT / READ_LEDGERS_DIR / "patch-tool.json"
    session_ledger.parent.mkdir(parents=True, exist_ok=True)
    session_ledger.write_text('{"reads": {}}\n', encoding="utf-8")

    assert record_read(REPO_ROOT, "CLAUDE.md", event, source="Read") is True

    global_ledger = load_read_ledger(REPO_ROOT)
    event_ledger = load_read_ledger_for_event(REPO_ROOT, event)
    assert set(global_ledger["reads"]) == {"AGENTS.md", "CLAUDE.md"}
    assert set(event_ledger["reads"]) == {"AGENTS.md", "CLAUDE.md"}
    _clean_runtime()


def test_post_tool_records_direct_read_tool() -> None:
    _clean_runtime()
    save_session(REPO_ROOT, {"active_skill": "validate-run"})
    event = {
        "hookEventName": "PostToolUse",
        "turn_id": "turn-test",
        "toolName": "Read",
        "input": {"filePath": ".agents/skills/validate-run/SKILL.md"},
    }
    recorded = record_direct_tool_read(REPO_ROOT, event)
    assert recorded == [".agents/skills/validate-run/SKILL.md"]
    ledger = load_read_ledger(REPO_ROOT)
    assert (
        ledger["reads"][".agents/skills/validate-run/SKILL.md"]["events"][0][
            "tool_name"
        ]
        == "Read"
    )
    _clean_runtime()


def test_post_tool_only_reports_new_direct_read_files() -> None:
    _clean_runtime()
    save_session(REPO_ROOT, {"active_skill": "validate-run"})
    event = {
        "hookEventName": "PostToolUse",
        "turn_id": "turn-test",
        "toolName": "Read",
        "input": {"filePath": ".agents/skills/validate-run/SKILL.md"},
    }

    first = record_direct_tool_read(REPO_ROOT, event)
    second = record_direct_tool_read(REPO_ROOT, event)

    assert first == [".agents/skills/validate-run/SKILL.md"]
    assert second == []
    ledger = load_read_ledger(REPO_ROOT)
    assert (
        len(ledger["reads"][".agents/skills/validate-run/SKILL.md"]["events"])
        == 2
    )
    _clean_runtime()


def test_direct_read_tool_ignores_non_tracking_candidate() -> None:
    _clean_runtime()
    save_session(REPO_ROOT, {"active_skill": "validate-run"})
    event = {
        "hookEventName": "PostToolUse",
        "turn_id": "turn-test",
        "toolName": "Read",
        "input": {"filePath": "README.md"},
    }

    recorded = record_direct_tool_read(REPO_ROOT, event)

    assert recorded == []
    assert load_read_ledger(REPO_ROOT) == {"reads": {}}
    _clean_runtime()


def test_gate_ledger_notice_is_consumed_once() -> None:
    _clean_runtime()
    pending = {
        "requires_gate_ledger": True,
        "reasons": ["sensitive workflow files changed"],
        "changed_paths": ["tooling/codex_hooks/harness_contracts.py"],
    }

    assert consume_gate_ledger_notice(REPO_ROOT, pending) is True
    saved = load_pending(REPO_ROOT)
    assert saved["gate_ledger_notice_emitted"] is True
    assert consume_gate_ledger_notice(REPO_ROOT, saved) is False
    _clean_runtime()


def test_mark_pending_does_not_scan_untracked_sensitive_paths(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    root.mkdir()
    subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.DEVNULL)
    (root / CONTRACTS_PATH).parent.mkdir(parents=True)
    (root / CONTRACTS_PATH).write_text(
        '{"schema_version":"0.1","contracts":[]}\n',
        encoding="utf-8",
    )
    (root / "docs").mkdir()
    (root / "docs" / "New.md").write_text("# New\n", encoding="utf-8")

    pending = mark_pending_for_changes(root, {"turn_id": "t"})

    assert pending["requires_gate_ledger"] is False
    assert pending["changed_paths"] == []


def test_mark_pending_does_not_scan_staged_sensitive_paths(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    root.mkdir()
    subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.DEVNULL)
    (root / CONTRACTS_PATH).parent.mkdir(parents=True)
    (root / CONTRACTS_PATH).write_text(
        '{"schema_version":"0.1","contracts":[]}\n',
        encoding="utf-8",
    )
    (root / "docs").mkdir()
    (root / "docs" / "Staged.md").write_text("# Staged\n", encoding="utf-8")
    subprocess.run(
        ["git", "add", "docs/Staged.md"],
        cwd=root,
        check=True,
        stdout=subprocess.DEVNULL,
    )

    pending = mark_pending_for_changes(root, {"turn_id": "t"})

    assert pending["requires_gate_ledger"] is False
    assert pending["changed_paths"] == []


def test_mark_pending_ignores_local_code_review_trace_paths(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    root.mkdir()
    subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.DEVNULL)
    _write_contracts(
        root,
        [
            {
                "skill": "code-review",
                "triggers": [],
                "required_read_set": {},
                "required_actions": [],
                "forbidden_actions": [],
                "gate_ledger_required_when": [],
                "sensitive_paths": [".agents/state/review_traces/code-review/"],
            }
        ],
    )
    save_session(root, {"active_skill": "code-review"})
    trace_path = (
        root
        / ".agents"
        / "state"
        / "review_traces"
        / "code-review"
        / "run01"
        / "review_report.md"
    )
    trace_path.parent.mkdir(parents=True)
    trace_path.write_text("# Review\n", encoding="utf-8")

    pending = mark_pending_for_changes(root, {"turn_id": "t"})

    assert pending["requires_gate_ledger"] is False
    assert pending["changed_paths"] == []


def test_mark_pending_ignores_trace_but_keeps_other_sensitive_paths(
    tmp_path: Path,
) -> None:
    root = tmp_path / "workspace"
    root.mkdir()
    subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.DEVNULL)
    _write_contracts(
        root,
        [
            {
                "skill": "code-review",
                "triggers": [],
                "required_read_set": {},
                "required_actions": [],
                "forbidden_actions": [],
                "gate_ledger_required_when": [],
                "sensitive_paths": [
                    ".agents/state/review_traces/code-review/",
                    "docs/",
                ],
            }
        ],
    )
    save_session(root, {"active_skill": "code-review"})
    trace_path = (
        root
        / ".agents"
        / "state"
        / "review_traces"
        / "code-review"
        / "run01"
        / "review_report.md"
    )
    trace_path.parent.mkdir(parents=True)
    trace_path.write_text("# Review\n", encoding="utf-8")
    (root / "docs").mkdir()
    (root / "docs" / "Reviewed.md").write_text("# Reviewed\n", encoding="utf-8")

    pending = mark_pending_for_changes(root, {"turn_id": "t"})

    assert pending["requires_gate_ledger"] is False
    assert pending["changed_paths"] == []


def test_code_review_audit_write_does_not_inherit_existing_dirty_subject_paths(
    tmp_path: Path,
) -> None:
    root = tmp_path / "workspace"
    root.mkdir()
    subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.DEVNULL)
    _write_contracts(
        root,
        [
            {
                "skill": "code-review",
                "triggers": [],
                "required_read_set": {},
                "required_actions": [],
                "forbidden_actions": [],
                "gate_ledger_required_when": [],
                "sensitive_paths": [
                    ".agents/state/review_traces/code-review/",
                    "tests/",
                ],
            }
        ],
    )
    save_session(root, {"active_skill": "code-review"})
    (root / "tests").mkdir()
    (root / "tests" / "test_existing_dirty.py").write_text(
        "def test_existing_dirty():\n    assert True\n",
        encoding="utf-8",
    )
    event = {
        "tool_name": "apply_patch",
        "tool_input": {
            "command": (
                "*** Begin Patch\n"
                "*** Add File: .agents/state/review_traces/code-review/"
                "run01/review_report.md\n"
                "+# Review\n"
                "*** End Patch\n"
            )
        },
        "turn_id": "t",
    }

    pending = mark_pending_for_changes(root, event)

    assert pending["requires_gate_ledger"] is False
    assert pending["changed_paths"] == []


def test_code_review_external_review_output_does_not_inherit_dirty_subject_paths(
    tmp_path: Path,
) -> None:
    root = tmp_path / "workspace"
    root.mkdir()
    subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.DEVNULL)
    _write_contracts(
        root,
        [
            {
                "skill": "code-review",
                "triggers": [],
                "required_read_set": {},
                "required_actions": [],
                "forbidden_actions": [],
                "gate_ledger_required_when": [],
                "sensitive_paths": [
                    ".agents/state/review_traces/code-review/",
                    "tests/",
                ],
            }
        ],
    )
    save_session(root, {"active_skill": "code-review"})
    (root / "tests").mkdir()
    (root / "tests" / "test_existing_dirty.py").write_text(
        "def test_existing_dirty():\n    assert True\n",
        encoding="utf-8",
    )
    event = {
        "tool_name": "Bash",
        "tool_input": {
            "command": (
                "python tooling/model_api/harness_external_review.py "
                "agentic --provider deepseek --output "
                ".agents/state/review_traces/code-review/run01/deepseek.md"
            )
        },
        "turn_id": "t",
    }

    pending = mark_pending_for_changes(root, event)

    assert pending["requires_gate_ledger"] is False
    assert pending["changed_paths"] == []


def test_pre_tool_accepts_shell_alias_for_mutation_checks() -> None:
    event = {
        "toolName": "local_shell",
        "input": {"cmd": "git add plan.markdown"},
    }
    reason = block_pre_tool(REPO_ROOT, event)
    assert reason is not None
    assert "do not add" in reason


def test_non_harness_workspace_noops(tmp_path: Path) -> None:
    assert not is_harness_workspace(tmp_path)
    event = {
        "toolName": "Bash",
        "input": {"command": "git add ref/foo"},
    }
    assert block_pre_tool(tmp_path, event) is None
    assert stop_decision(tmp_path, {"last_assistant_message": "Done."}) is None
    pending = mark_pending_for_changes(tmp_path, {"turn_id": "t"})
    assert pending["requires_gate_ledger"] is False


def test_stop_allows_missing_gate_ledger_when_pending() -> None:
    _clean_runtime()
    save_pending(
        REPO_ROOT,
        {
            "requires_gate_ledger": True,
            "reasons": ["sensitive workflow files changed"],
            "changed_paths": ["PROJECT_STATE.json"],
        },
    )
    decision = stop_decision(
        REPO_ROOT,
        {
            "last_assistant_message": "Done.",
            "stop_hook_active": False,
        },
    )
    assert decision is None

    cleared = stop_decision(
        REPO_ROOT,
        {
            "last_assistant_message": (
                "Gate ledger\n"
                "- command: not run\n"
                "- result: NOT_RUN\n"
                "- reason: no external reviewer configured\n"
                "- artifacts: review_report.md"
            ),
            "stop_hook_active": False,
        },
    )
    assert cleared is None
    pending = load_pending(REPO_ROOT)
    assert pending["requires_gate_ledger"] is False
    assert pending["changed_paths"] == []
    assert pending["reasons"] == []
    _clean_runtime()


def test_stop_leaves_pending_when_gate_ledger_fields_are_missing() -> None:
    _clean_runtime()
    save_pending(
        REPO_ROOT,
        {
            "requires_gate_ledger": True,
            "reasons": ["sensitive workflow files changed"],
            "changed_paths": ["PROJECT_STATE.json"],
        },
    )

    decision = stop_decision(
        REPO_ROOT,
        {
            "last_assistant_message": "Gate ledger is not needed here. NOT_RUN.",
            "stop_hook_active": False,
        },
    )

    assert decision is None
    pending = load_pending(REPO_ROOT)
    assert pending["requires_gate_ledger"] is True
    _clean_runtime()
