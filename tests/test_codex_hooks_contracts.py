from __future__ import annotations

import json
import shutil
import subprocess
import sys
from io import StringIO
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tooling" / "codex_hooks"))

from harness_contracts import (  # noqa: E402
    READ_LEDGER_PATH,
    RUNTIME_DIR,
    block_pre_tool,
    classify_prompt_intent,
    consume_gate_ledger_notice,
    contract_by_skill,
    daily_context_for_workspace,
    detect_skill,
    detect_skill_match,
    external_review_output_paths,
    is_harness_workspace,
    load_contracts,
    load_pending,
    load_read_ledger,
    load_session,
    looks_mutating_bash,
    mark_pending_for_changes,
    mark_tool_activity,
    mutating_event_paths,
    python_script_from_command,
    record_command_reads,
    record_direct_tool_read,
    required_existing_files,
    reset_read_ledger,
    save_pending,
    save_read_ledger,
    save_session,
    stop_decision,
    validate_contract_files,
)
from hook_status import build_status  # noqa: E402
from install_hooks import (  # noqa: E402
    _copy_rule_templates,
    _copy_runtime_scripts,
    _ensure_codex_hooks_enabled,
    _load_hook_config,
    _remove_rule_templates,
)
from user_prompt_submit import main as user_prompt_submit_main  # noqa: E402


def _clean_runtime() -> None:
    shutil.rmtree(REPO_ROOT / RUNTIME_DIR, ignore_errors=True)


def _write_contracts(root: Path, contracts: list[dict[str, object]]) -> None:
    contracts_path = root / ".agents" / "skill-contracts" / "contracts.json"
    contracts_path.parent.mkdir(parents=True, exist_ok=True)
    contracts_path.write_text(
        json.dumps({"schema_version": "0.1", "contracts": contracts}) + "\n",
        encoding="utf-8",
    )


@pytest.fixture(autouse=True)
def clean_hook_runtime() -> None:
    _clean_runtime()
    yield
    _clean_runtime()


def test_skill_contract_files_are_valid() -> None:
    errors = validate_contract_files(REPO_ROOT)
    assert not errors

    skills = {contract["skill"] for contract in load_contracts(REPO_ROOT)}
    available_skills = {
        path.parent.name
        for path in (REPO_ROOT / ".agents" / "skills").glob("*/SKILL.md")
    }
    assert available_skills.issubset(skills)


def test_iterate_contract_covers_eval_iteration_reports() -> None:
    contract = contract_by_skill(REPO_ROOT, "iterate")
    assert contract is not None

    assert "iteration_report_write" in contract["gate_ledger_required_when"]
    assert "docs/iterations/" in contract["sensitive_paths"]


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
    updated = _ensure_codex_hooks_enabled(text)

    assert "[features]\nexperimental = true\ncodex_hooks = true\n\n[tools]" in updated
    assert updated.count("[features]") == 1


def test_hook_status_reports_user_runtime_and_workspace_policy(tmp_path: Path) -> None:
    codex_dir = tmp_path / ".codex"
    runtime_dir = codex_dir / "harness_hooks"
    _copy_runtime_scripts(REPO_ROOT, runtime_dir)
    (codex_dir / "config.toml").write_text(
        "[features]\ncodex_hooks = true\n", encoding="utf-8"
    )
    (codex_dir / "hooks.json").write_text(
        _load_hook_config(REPO_ROOT / "tooling/codex_hooks/hooks.json", runtime_dir),
        encoding="utf-8",
    )

    status = build_status(REPO_ROOT, codex_dir=codex_dir)
    assert status["codex_hooks_enabled"] is True
    assert status["harness_workspace"] is True
    assert status["workspace_policy_effect"] == "active"
    assert status["user_hook_errors"] == []
    assert status["hook_install_ready"] is True


def test_hook_status_accepts_workspace_only_install(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    root.mkdir()
    (root / ".git").mkdir()
    (root / ".agents/skill-contracts").mkdir(parents=True)
    (root / ".agents/skill-contracts/contracts.json").write_text(
        '{"contracts":[]}\n', encoding="utf-8"
    )
    (root / ".codex").mkdir()
    (root / ".codex/config.toml").write_text(
        "[features]\ncodex_hooks = true\n", encoding="utf-8"
    )
    (root / ".codex/hooks.json").write_text(
        (REPO_ROOT / "tooling/codex_hooks/hooks.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    status = build_status(root, codex_dir=tmp_path / "empty-user-codex")
    assert status["codex_hooks_enabled"] is True
    assert status["repo_codex_hooks_enabled"] is True
    assert status["user_hooks_exists"] is False
    assert status["user_hook_errors"] == []
    assert status["active_hook_source"] == "workspace"
    assert status["hook_install_ready"] is True


def test_daily_context_lists_repo_guidance_files(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    root.mkdir()
    (root / ".git").mkdir()
    (root / ".agents/skill-contracts").mkdir(parents=True)
    (root / ".agents/skill-contracts/contracts.json").write_text(
        '{"contracts":[]}\n', encoding="utf-8"
    )
    (root / "AGENTS.md").write_text("# Agent guidance\n", encoding="utf-8")
    (root / "CLAUDE.md").write_text("# Claude guidance\n", encoding="utf-8")

    context = daily_context_for_workspace(root)

    assert "Harness daily workspace context" in context
    assert "AGENTS.md" in context
    assert "CLAUDE.md" in context


def test_detect_skill_from_prompt() -> None:
    contract = detect_skill(REPO_ROOT, "请运行 $validate-run 并准备 WF10 readiness")
    assert contract is not None
    assert contract["skill"] == "validate-run"


def test_detection_ignores_trigger_words_inside_file_paths() -> None:
    prompt = "Harness_Workflow_Implementation_Review.md 这个文件在哪？"
    assert classify_prompt_intent(prompt) == "code_search"
    assert detect_skill_match(REPO_ROOT, prompt) is None


def test_detection_infers_code_debug_for_ordinary_code_modification() -> None:
    match = detect_skill_match(
        REPO_ROOT, "帮我修改 Skill Detection 和 read-only/code-search 相关内容"
    )
    assert match is not None
    assert match["skill"] == "code-debug"
    assert match["trigger_type"] == "inferred"
    assert match["intent_class"] == "code_write"
    assert match["read_contract_stop_required"] is False


def test_detection_infers_code_expert_for_new_implementation_request() -> None:
    match = detect_skill_match(REPO_ROOT, "帮我实现一个新的 Python 数据处理模块")
    assert match is not None
    assert match["skill"] == "code-expert"
    assert match["trigger_type"] == "inferred"


def test_detection_infers_code_review_for_diff_review_request() -> None:
    match = detect_skill_match(
        REPO_ROOT, "帮我对当前 git diff 做 code review，带上行号"
    )
    assert match is not None
    assert match["skill"] == "code-review"
    assert match["intent_class"] == "code_review_medium"
    assert match["read_contract_stop_required"] is True


def test_detection_infers_heavy_code_review_for_docs_evidence() -> None:
    match = detect_skill_match(
        REPO_ROOT, "对阶段文档和证据链做 heavy code review 交叉验证"
    )
    assert match is not None
    assert match["skill"] == "code-review"
    assert match["intent_class"] == "code_review_heavy"


def test_detection_classifies_cjk_adjacent_hook_review_as_heavy() -> None:
    prompt = "使用code review heavy 审查这套workflow"

    match = detect_skill_match(REPO_ROOT, prompt)

    assert match is not None
    assert match["skill"] == "code-review"
    assert match["intent_class"] == "code_review_heavy"


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
    assert session["active_skill"] == "code-review"
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


def test_pre_tool_blocks_manual_tool_owned_patch_delete(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    (root / ".agents" / "skill-contracts").mkdir(parents=True)
    (root / ".agents" / "skill-contracts" / "contracts.json").write_text(
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
    assert "review-only" in reason
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
    assert "review-only" in reason
    _clean_runtime()


def test_pre_tool_blocks_write_before_required_reads() -> None:
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
    reason = block_pre_tool(REPO_ROOT, event)
    assert reason is not None
    assert "Required read set is incomplete" in reason
    _clean_runtime()


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


def test_stop_blocks_explicit_skill_missing_reads() -> None:
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
    assert decision is not None
    assert decision["decision"] == "block"
    assert "Read the required files" in decision["reason"]
    _clean_runtime()


def test_stop_blocks_implicit_skill_after_mutation_if_reads_missing() -> None:
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
    assert decision is not None
    assert "code-debug" in decision["reason"]
    _clean_runtime()


def test_stop_blocks_inferred_code_review_missing_reads_even_without_writes() -> None:
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
    assert decision is not None
    assert "code-review" in decision["reason"]
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
    assert decision is not None
    assert "Read the required files" in decision["reason"]
    _clean_runtime()


def test_reset_read_ledger_clears_recorded_reads() -> None:
    _clean_runtime()
    save_read_ledger(REPO_ROOT, {"reads": {"AGENTS.md": {"events": []}}})

    reset_read_ledger(REPO_ROOT)

    assert load_read_ledger(REPO_ROOT) == {"reads": {}}
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


def test_mark_pending_includes_untracked_sensitive_paths(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    root.mkdir()
    subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.DEVNULL)
    (root / ".agents" / "skill-contracts").mkdir(parents=True)
    (root / ".agents" / "skill-contracts" / "contracts.json").write_text(
        '{"schema_version":"0.1","contracts":[]}\n',
        encoding="utf-8",
    )
    (root / "docs").mkdir()
    (root / "docs" / "New.md").write_text("# New\n", encoding="utf-8")

    pending = mark_pending_for_changes(root, {"turn_id": "t"})

    assert pending["requires_gate_ledger"] is True
    assert pending["changed_paths"] == ["docs/New.md"]


def test_mark_pending_includes_staged_sensitive_paths(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    root.mkdir()
    subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.DEVNULL)
    (root / ".agents" / "skill-contracts").mkdir(parents=True)
    (root / ".agents" / "skill-contracts" / "contracts.json").write_text(
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

    assert pending["requires_gate_ledger"] is True
    assert pending["changed_paths"] == ["docs/Staged.md"]


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

    assert pending["requires_gate_ledger"] is True
    assert pending["changed_paths"] == ["docs/Reviewed.md"]


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


def test_stop_blocks_missing_gate_ledger_when_pending() -> None:
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
    assert decision is not None
    assert decision["decision"] == "block"

    allowed = stop_decision(
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
    assert allowed is None
    pending = load_pending(REPO_ROOT)
    assert pending["requires_gate_ledger"] is False
    assert pending["changed_paths"] == []
    assert pending["reasons"] == []
    _clean_runtime()


def test_stop_does_not_accept_gate_ledger_words_without_fields() -> None:
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

    assert decision is not None
    assert decision["decision"] == "block"
    _clean_runtime()
