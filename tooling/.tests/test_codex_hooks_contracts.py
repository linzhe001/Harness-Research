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

import check_contracts  # noqa: E402
import generate_stage_cards  # noqa: E402
import hook_status  # noqa: E402
from harness_contracts import (  # noqa: E402
    CONTRACTS_PATH,
    READ_LEDGER_PATH,
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
    save_read_ledger_for_event,
    save_session,
    stop_decision,
    tool_owned_output_paths,
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
    for contract in load_contracts(REPO_ROOT):
        assert contract.get("write_scope", {}).get("allowed_paths"), contract["skill"]
        assert contract.get("artifact_outputs"), contract["skill"]


def test_iterate_contract_covers_eval_iteration_reports() -> None:
    contract = contract_by_skill(REPO_ROOT, "iterate")
    assert contract is not None

    assert "iteration_report_write" in contract["gate_ledger_required_when"]
    assert "docs/iterations/" in contract["sensitive_paths"]


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
        assert "docs_site_render_or_NOT_RUN" in contract["required_actions"]
        assert "docs_site_render" in contract["gate_ledger_required_when"]
        assert "docs/_views/" in contract["write_scope"]["allowed_paths"]
        assert "docs/_site/" in contract["write_scope"]["allowed_paths"]
        assert any(
            output["kind"] == "generated_view"
            and output["owner"] == "docs-site"
            and output["requires_tool"] is True
            and output["paths"] == ["docs/_views/", "docs/_site/"]
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

    assert "# Harness Workflow Stage Cards" in rendered
    assert "## code-debug" in rendered
    assert "## harness-maintenance" in rendered
    assert "Can write:" in rendered
    assert "Final outputs:" in rendered
    assert "Tool-owned outputs:" in rendered
    assert "`conclusion_evidence: docs/30_evidence/Dataset_Table.md`" in rendered
    assert "`src/`" in rendered
    assert "`tooling/codex_hooks/`" in rendered
    assert "`docs/`" in rendered
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
    assert "## harness-maintenance" in text
    assert "Gate ledger" in text
    assert "--output docs/Workflow_Stage_Cards.md" not in text


def test_workflow_handbook_stage_cards_match_generated_output() -> None:
    output = REPO_ROOT / "workflow_handbook" / "Workflow_Stage_Cards.md"

    expected = generate_stage_cards.render_stage_cards(REPO_ROOT)

    assert output.exists()
    assert output.read_text(encoding="utf-8") == expected


def test_workflow_handbook_keeps_two_human_entrypoints() -> None:
    handbook_dir = REPO_ROOT / "workflow_handbook"
    files = sorted(path.name for path in handbook_dir.glob("*.md"))

    assert files == [
        "Workflow_Operator_Handbook.md",
        "Workflow_Stage_Cards.md",
    ]
    handbook = (handbook_dir / "Workflow_Operator_Handbook.md").read_text(
        encoding="utf-8"
    )
    assert "Handbook 和 Stage Cards 的分工" in handbook
    assert "AI Coding Discipline In Harness" in handbook
    assert "不要再在 `workflow_handbook/` 下新增平行叙事文档" in handbook


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

    assert "Harness daily workspace context" in context
    assert "AGENTS.md" in context
    assert "CLAUDE.md" in context


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


def test_pre_tool_blocks_git_commit_until_sliced_commit_rule_read() -> None:
    event = {
        "tool_name": "Bash",
        "tool_input": {"command": "git commit -m 'docs: update workflow'"},
    }

    reason = block_pre_tool(REPO_ROOT, event)

    assert reason is not None
    assert "sliced commit guidance" in reason
    assert SLICED_COMMIT_RULE_PATH in reason


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
    assert match["skill"] == "init-project"
    assert match["trigger"] in {"wf0", "bootstrap init"}
    assert match["read_contract_stop_required"] is True


def test_detection_maps_init_alias_to_init_project() -> None:
    match = detect_skill_match(REPO_ROOT, "请运行 $init init")

    assert match is not None
    assert match["skill"] == "init-project"
    assert match["trigger"] == "$init"
    assert match["trigger_type"] == "explicit"


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
    assert match["skill"] == "orchestrator"
    assert match["intent_class"] == "workflow_action"
    assert match["enforcement_mode"] == "active_read"


def test_detection_keeps_explicit_iterate_trigger_hard() -> None:
    status = detect_skill_match(REPO_ROOT, "/iterate status")
    plan = detect_skill_match(REPO_ROOT, '$iterate plan "try smaller lr"')
    decision = detect_skill_match(REPO_ROOT, "$iterate eval CONTINUE")

    assert status is not None
    assert status["skill"] == "iterate"
    assert status["enforcement_mode"] == "active_read"
    assert plan is not None
    assert plan["skill"] == "iterate"
    assert plan["enforcement_mode"] == "active_write"
    assert decision is not None
    assert decision["skill"] == "iterate"
    assert decision["enforcement_mode"] == "active_write"


def test_detection_infers_code_debug_for_ordinary_code_modification() -> None:
    match = detect_skill_match(REPO_ROOT, "帮我修改 Python 模块中的数据处理逻辑")

    assert match is not None
    assert match["skill"] == "code-debug"
    assert match["trigger_type"] == "inferred"
    assert match["intent_class"] == "code_write"
    assert match["read_contract_stop_required"] is False


def test_detection_infers_harness_maintenance_for_skill_detection() -> None:
    match = detect_skill_match(
        REPO_ROOT, "帮我修改 Skill Detection 和 read-only/code-search 相关内容"
    )

    assert match is not None
    assert match["skill"] == "harness-maintenance"
    assert match["trigger_type"] in {"implicit", "inferred"}
    assert match["intent_class"] == "code_write"
    assert match["read_contract_stop_required"] is False


def test_detection_infers_harness_maintenance_for_hook_trigger_text() -> None:
    match = detect_skill_match(REPO_ROOT, "帮我修改 hook的判断和触发")

    assert match is not None
    assert match["skill"] == "harness-maintenance"
    assert match["trigger_type"] in {"implicit", "inferred"}


def test_detection_infers_harness_maintenance_over_generic_fix() -> None:
    match = detect_skill_match(REPO_ROOT, "fix hooks trust routing")

    assert match is not None
    assert match["skill"] == "harness-maintenance"
    assert match["trigger_type"] == "inferred"
    assert match["intent_class"] == "code_write"


def test_detection_infers_harness_maintenance_for_workflow_language() -> None:
    match = detect_skill_match(
        REPO_ROOT, "帮我优化 workflow 通用语言、关键概念和 Stage Card generator"
    )

    assert match is not None
    assert match["skill"] == "harness-maintenance"
    assert match["intent_class"] == "code_write"


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


def test_detection_keeps_imperative_workflow_trigger_hard() -> None:
    match = detect_skill_match(
        REPO_ROOT,
        "帮我修改 prompt routing 和 workflow 触发规则",
    )

    assert match is not None
    assert match["skill"] == "harness-maintenance"
    assert match["intent_class"] == "code_write"
    assert match["enforcement_mode"] == "active_write"


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


def test_detection_prefers_plain_code_debug_over_review_phrase() -> None:
    match = detect_skill_match(
        REPO_ROOT,
        "帮我修复上次 code review 中发现的问题 code-debug",
    )

    assert match is not None
    assert match["skill"] == "code-debug"
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
    assert "Harness advisory skill context: harness-maintenance" in output
    assert "does not grant Write Scope" in output
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


def test_pre_tool_blocks_docs_site_renderer_without_active_contract() -> None:
    _clean_runtime()
    save_session(REPO_ROOT, {"active_skill": None, "enforcement_mode": "none"})
    event = {
        "tool_name": "Bash",
        "tool_input": {
            "command": "python tooling/evidence/build_docs_site.py --workspace-root ."
        },
    }

    reason = block_pre_tool(REPO_ROOT, event)

    assert reason is not None
    assert "requires an active `$docs-site`" in reason
    assert "docs/_site/" in reason
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


def test_pre_tool_blocks_write_outside_active_stage_scope() -> None:
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

    reason = block_pre_tool(REPO_ROOT, event)

    assert reason is not None
    assert "outside the active `validate-run` stage write scope" in reason
    assert "README.md" in reason
    assert "docs/Validate_Run_Report.md" in reason
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


def test_pre_tool_blocks_active_read_subject_write_even_inside_write_scope() -> None:
    _clean_runtime()
    contract = contract_by_skill(REPO_ROOT, "iterate")
    assert contract is not None
    save_session(
        REPO_ROOT,
        {"active_skill": "iterate", "enforcement_mode": "active_read"},
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

    reason = block_pre_tool(REPO_ROOT, event)

    assert reason is not None
    assert "active_read mode" in reason
    assert "iteration_log.json" in reason
    _clean_runtime()


def test_pre_tool_blocks_guardrail_write_without_active_contract() -> None:
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

    reason = block_pre_tool(REPO_ROOT, event)

    assert reason is not None
    assert "guardrail-sensitive" in reason
    assert "`harness-maintenance`" in reason
    assert load_session(REPO_ROOT).get("active_skill") is None
    _clean_runtime()


def test_pre_tool_blocks_contract_owned_write_without_active_contract() -> None:
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

    reason = block_pre_tool(REPO_ROOT, event)

    assert reason is not None
    assert "no hard active skill is selected" in reason
    assert "validate-run" in reason
    assert load_session(REPO_ROOT).get("active_skill") is None
    _clean_runtime()


def test_pre_tool_asks_explicit_stage_for_ambiguous_docs_write() -> None:
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

    reason = block_pre_tool(REPO_ROOT, event)

    assert reason is not None
    assert "no hard active skill is selected" in reason
    assert "Possible owners" in reason
    assert "harness-maintenance" in reason
    assert "init-project" in reason
    assert "release" in reason
    assert load_session(REPO_ROOT).get("active_skill") is None
    _clean_runtime()


def test_pre_tool_blocks_guardrail_bash_token_without_active_contract() -> None:
    _clean_runtime()
    save_session(REPO_ROOT, {"active_skill": None, "enforcement_mode": "none"})
    event = {
        "tool_name": "Bash",
        "tool_input": {"command": "echo test > tooling/codex_hooks/tmp.txt"},
    }

    reason = block_pre_tool(REPO_ROOT, event)

    assert reason is not None
    assert "guardrail-sensitive" in reason
    assert "`harness-maintenance`" in reason
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

    reason = block_pre_tool(root, blocked)

    assert reason is not None
    assert "outside the active `scoped-stage` stage write scope" in reason
    assert block_pre_tool(root, allowed) is None


def test_pre_tool_missing_write_scope_fails_closed(tmp_path: Path) -> None:
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

    reason = block_pre_tool(root, event)

    assert reason is not None
    assert "outside the active `legacy-stage` stage write scope" in reason


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


def test_pre_tool_blocks_code_debug_hook_guardrail_write() -> None:
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

    reason = block_pre_tool(REPO_ROOT, event)

    assert reason is not None
    assert "outside the active `code-debug` stage write scope" in reason
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
    (root / CONTRACTS_PATH).parent.mkdir(parents=True)
    (root / CONTRACTS_PATH).write_text(
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
