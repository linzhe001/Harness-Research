"""Tests for external OpenAI-compatible model API tooling."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import urllib.error
from io import BytesIO
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
MODULE_PATH = REPO_ROOT / "tooling" / "model_api" / "external_chat.py"
PROMPT_BUILDER_PATH = REPO_ROOT / "tooling" / "model_api" / "build_review_prompt.py"
AGENTIC_REVIEW_PATH = REPO_ROOT / "tooling" / "model_api" / "agentic_review.py"
HARNESS_EXTERNAL_REVIEW_PATH = (
    REPO_ROOT / "tooling" / "model_api" / "harness_external_review.py"
)
sys.path.insert(0, str(REPO_ROOT / "tooling" / "model_api"))

spec = importlib.util.spec_from_file_location("external_chat", MODULE_PATH)
assert spec is not None
external_chat = importlib.util.module_from_spec(spec)
sys.modules["external_chat"] = external_chat
assert spec.loader is not None
spec.loader.exec_module(external_chat)

prompt_builder_spec = importlib.util.spec_from_file_location(
    "build_review_prompt",
    PROMPT_BUILDER_PATH,
)
assert prompt_builder_spec is not None
build_review_prompt = importlib.util.module_from_spec(prompt_builder_spec)
sys.modules["build_review_prompt"] = build_review_prompt
assert prompt_builder_spec.loader is not None
prompt_builder_spec.loader.exec_module(build_review_prompt)

agentic_review_spec = importlib.util.spec_from_file_location(
    "agentic_review",
    AGENTIC_REVIEW_PATH,
)
assert agentic_review_spec is not None
agentic_review = importlib.util.module_from_spec(agentic_review_spec)
sys.modules["agentic_review"] = agentic_review
assert agentic_review_spec.loader is not None
agentic_review_spec.loader.exec_module(agentic_review)

harness_external_review_spec = importlib.util.spec_from_file_location(
    "harness_external_review",
    HARNESS_EXTERNAL_REVIEW_PATH,
)
assert harness_external_review_spec is not None
harness_external_review = importlib.util.module_from_spec(harness_external_review_spec)
sys.modules["harness_external_review"] = harness_external_review
assert harness_external_review_spec.loader is not None
harness_external_review_spec.loader.exec_module(harness_external_review)


def test_deepseek_provider_defaults_to_v4_pro() -> None:
    provider = external_chat.load_provider_config("deepseek", env={})

    assert provider.name == "deepseek"
    assert provider.base_url == "https://api.deepseek.com"
    assert provider.api_key_env == "DEEPSEEK_API_KEY"
    assert provider.model == "deepseek-v4-pro"
    assert provider.extra_body["reasoning_effort"] == "max"


def test_external_review_wrapper_requires_heavy_code_review_session(
    tmp_path: Path,
) -> None:
    (tmp_path / ".git").mkdir()
    (tmp_path / ".harness_hooks").mkdir()
    (tmp_path / ".harness_hooks" / "session.json").write_text(
        json.dumps({
            "active_skill": "code-review",
            "intent_class": "code_review_medium",
        }),
        encoding="utf-8",
    )

    with pytest.raises(
        harness_external_review.HarnessExternalReviewError,
        match="code-review heavy",
    ):
        harness_external_review.validate_review_session(tmp_path)


def test_external_review_wrapper_accepts_heavy_code_review_session(
    tmp_path: Path,
) -> None:
    (tmp_path / ".git").mkdir()
    (tmp_path / ".harness_hooks").mkdir()
    (tmp_path / ".harness_hooks" / "session.json").write_text(
        json.dumps({
            "active_skill": "code-review",
            "intent_class": "code_review_heavy",
        }),
        encoding="utf-8",
    )

    session = harness_external_review.validate_review_session(tmp_path)

    assert session["active_skill"] == "code-review"


def test_external_review_wrapper_blocks_base_url_override() -> None:
    with pytest.raises(
        harness_external_review.HarnessExternalReviewError,
        match="providers.local.yaml",
    ):
        harness_external_review.validate_passthrough_args(
            REPO_ROOT,
            [
                "--provider",
                "deepseek",
                "--base-url",
                "https://example.test",
            ],
        )


@pytest.mark.parametrize(
    "config_args",
    [
        ["--config", "/tmp/providers.yaml"],
        ["--config=/tmp/providers.yaml"],
    ],
)
def test_external_review_wrapper_blocks_config_override(
    config_args: list[str],
) -> None:
    with pytest.raises(
        harness_external_review.HarnessExternalReviewError,
        match="providers.local.yaml",
    ):
        harness_external_review.validate_passthrough_args(
            REPO_ROOT,
            ["--provider", "deepseek", *config_args],
        )


def test_external_review_wrapper_allows_input_inside_trace(tmp_path: Path) -> None:
    trace_dir = (
        tmp_path / ".agents" / "state" / "review_traces" / "code-review" / "run01"
    )
    trace_dir.mkdir(parents=True)
    task = trace_dir / "task.md"
    task.write_text("Review this workflow.\n", encoding="utf-8")

    harness_external_review.validate_passthrough_args(
        tmp_path,
        [
            "--provider",
            "deepseek",
            "--task-file",
            str(task),
            "--output",
            str(trace_dir / "review.md"),
        ],
    )


def test_external_review_wrapper_rejects_input_outside_trace() -> None:
    with pytest.raises(
        harness_external_review.HarnessExternalReviewError,
        match="must read under",
    ):
        harness_external_review.validate_passthrough_args(
            REPO_ROOT,
            ["--provider", "deepseek", "--task-file", "README.md"],
        )


def test_external_review_wrapper_rejects_denied_input_name(tmp_path: Path) -> None:
    trace_dir = (
        tmp_path / ".agents" / "state" / "review_traces" / "code-review" / "run01"
    )
    trace_dir.mkdir(parents=True)
    prompt = trace_dir / "local.config.json"
    prompt.write_text("{}\n", encoding="utf-8")

    with pytest.raises(
        harness_external_review.HarnessExternalReviewError,
        match="local secrets",
    ):
        harness_external_review.validate_passthrough_args(
            tmp_path,
            ["--provider", "deepseek", f"--prompt-file={prompt}"],
        )


def test_external_review_wrapper_builds_fixed_agentic_command() -> None:
    command = harness_external_review.build_reviewer_command(
        REPO_ROOT,
        "agentic",
        [
            "--provider",
            "deepseek",
            "--output",
            ".agents/state/review_traces/code-review/run05/review.md",
        ],
    )

    assert command[0] == sys.executable
    assert command[1].endswith("tooling/model_api/agentic_review.py")
    assert command[-2:] == [
        "--output",
        ".agents/state/review_traces/code-review/run05/review.md",
    ]


def test_external_review_wrapper_defaults_chat_to_no_thinking() -> None:
    command = harness_external_review.build_reviewer_command(
        REPO_ROOT,
        "chat",
        [
            "--provider",
            "deepseek",
            "--output",
            ".agents/state/review_traces/code-review/run05/review.md",
        ],
    )

    assert command[-2:] == ["--thinking-scope", "none"]


def test_external_review_wrapper_preserves_explicit_chat_thinking_scope() -> None:
    command = harness_external_review.build_reviewer_command(
        REPO_ROOT,
        "chat",
        [
            "--provider",
            "deepseek",
            "--output",
            ".agents/state/review_traces/code-review/run05/review.md",
            "--thinking-scope",
            "all",
        ],
    )

    assert command[-2:] == ["--thinking-scope", "all"]


def test_external_review_wrapper_rejects_output_outside_trace() -> None:
    with pytest.raises(
        harness_external_review.HarnessExternalReviewError,
        match="must write under",
    ):
        harness_external_review.build_reviewer_command(
            REPO_ROOT,
            "agentic",
            ["--provider", "deepseek", "--output", "review.md"],
        )


def test_external_review_wrapper_times_out_child(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fake_run(command: list[str], *args: Any, **kwargs: Any) -> Any:
        del args
        assert kwargs["timeout"] == 3
        raise subprocess.TimeoutExpired(command, kwargs["timeout"])

    monkeypatch.setattr(harness_external_review.subprocess, "run", fake_run)

    code = harness_external_review.run_reviewer(
        ["python", "reviewer.py"],
        timeout_sec=3,
    )

    assert code == 124
    assert "timed out after 3s" in capsys.readouterr().err


def test_openai_compatible_provider_uses_env() -> None:
    provider = external_chat.load_provider_config(
        "openai_compatible",
        env={
            "OPENAI_BASE_URL": "https://review.example.test/v1",
            "OPENAI_API_KEY": "secret",
            "OPENAI_MODEL": "review-model",
        },
    )

    assert provider.base_url == "https://review.example.test/v1"
    assert provider.api_key_env == "OPENAI_API_KEY"
    assert provider.model == "review-model"


def test_custom_provider_from_json(tmp_path: Path) -> None:
    config_path = tmp_path / "providers.json"
    config_path.write_text(
        json.dumps({
            "providers": {
                "local_review": {
                    "base_url": "http://127.0.0.1:8000/v1",
                    "api_key_env": "LOCAL_REVIEW_API_KEY",
                    "model": "review-model",
                }
            }
        }),
        encoding="utf-8",
    )

    provider = external_chat.load_provider_config(
        "local_review",
        config_path=config_path,
        env={},
    )

    assert provider.base_url == "http://127.0.0.1:8000/v1"
    assert provider.api_key_env == "LOCAL_REVIEW_API_KEY"
    assert provider.model == "review-model"


def test_provider_config_can_supply_direct_api_key(tmp_path: Path) -> None:
    config_path = tmp_path / "providers.json"
    config_path.write_text(
        json.dumps({
            "providers": {
                "local_secret": {
                    "base_url": "https://api.example.test",
                    "api_key": "direct-secret",
                    "model": "review-model",
                }
            }
        }),
        encoding="utf-8",
    )

    provider = external_chat.load_provider_config(
        "local_secret",
        config_path=config_path,
        env={},
    )

    assert provider.api_key == "direct-secret"
    assert provider.api_key_env is None
    assert provider.model == "review-model"
    assert "direct-secret" not in repr(provider)


def test_provider_config_model_wins_over_env(tmp_path: Path) -> None:
    config_path = tmp_path / "providers.json"
    config_path.write_text(
        json.dumps({
            "providers": {
                "deepseek": {
                    "api_key": "direct-secret",
                    "model": "deepseek-v4-pro",
                }
            }
        }),
        encoding="utf-8",
    )

    provider = external_chat.load_provider_config(
        "deepseek",
        config_path=config_path,
        env={"DEEPSEEK_MODEL": "env-model"},
    )

    assert provider.model == "deepseek-v4-pro"


def test_default_config_path_prefers_local_yaml(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    local_config = tmp_path / "providers.local.yaml"
    example_config = tmp_path / "providers.example.yaml"
    local_config.write_text("providers: {}\n", encoding="utf-8")
    example_config.write_text("providers: {}\n", encoding="utf-8")
    monkeypatch.setattr(
        external_chat,
        "DEFAULT_CONFIG_CANDIDATES",
        (local_config, example_config),
    )

    assert external_chat.default_config_path() == local_config
    assert external_chat._default_config_path() == local_config


def test_default_config_path_falls_back_to_example_yaml(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    local_config = tmp_path / "providers.local.yaml"
    example_config = tmp_path / "providers.example.yaml"
    example_config.write_text("providers: {}\n", encoding="utf-8")
    monkeypatch.setattr(
        external_chat,
        "DEFAULT_CONFIG_CANDIDATES",
        (local_config, example_config),
    )
    monkeypatch.setattr(external_chat, "yaml", object())

    assert external_chat.default_config_path() == example_config
    assert external_chat._default_config_path() == example_config


def test_default_yaml_config_is_skipped_when_yaml_dependency_is_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    local_config = tmp_path / "providers.local.yaml"
    local_config.write_text(
        "providers:\n  deepseek:\n    api_key: direct-secret\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(external_chat, "DEFAULT_CONFIG_CANDIDATES", (local_config,))
    monkeypatch.setattr(external_chat, "yaml", None)

    assert external_chat.default_config_path() is None
    assert external_chat._default_config_path() is None
    provider = external_chat.load_provider_config(
        "deepseek",
        config_path=external_chat._default_config_path(),
        env={"DEEPSEEK_API_KEY": "env-secret"},
    )
    assert provider.api_key is None
    assert provider.api_key_env == "DEEPSEEK_API_KEY"


def test_build_chat_payload_includes_system_prompt_and_provider_extras() -> None:
    provider = external_chat.ProviderConfig(
        name="test",
        base_url="https://example.test",
        api_key_env="TEST_KEY",
        model="test-model",
        extra_body={"reasoning_effort": "high"},
    )

    payload = external_chat.build_chat_payload(
        provider,
        prompt="Review this diff.",
        system_prompt="You are a reviewer.",
        temperature=0.2,
        max_tokens=256,
    )

    assert payload["model"] == "test-model"
    assert payload["messages"] == [
        {"role": "system", "content": "You are a reviewer."},
        {"role": "user", "content": "Review this diff."},
    ]
    assert payload["temperature"] == 0.2
    assert payload["max_tokens"] == 256
    assert payload["reasoning_effort"] == "high"


def test_build_chat_payload_can_disable_provider_thinking_extras() -> None:
    provider = external_chat.ProviderConfig(
        name="test",
        base_url="https://example.test",
        api_key_env="TEST_KEY",
        model="test-model",
        extra_body={
            "reasoning_effort": "high",
            "thinking": {"type": "enabled"},
            "top_p": 0.9,
        },
    )

    payload = external_chat.build_chat_payload(
        provider,
        prompt="Review this diff.",
        thinking_scope="none",
    )

    assert "reasoning_effort" not in payload
    assert "thinking" not in payload
    assert payload["top_p"] == 0.9


def test_invoke_chat_completion_uses_bearer_auth() -> None:
    provider = external_chat.ProviderConfig(
        name="test",
        base_url="https://example.test/v1",
        api_key_env="TEST_KEY",
        model="test-model",
    )
    seen: dict[str, Any] = {}

    class Response:
        def __enter__(self) -> "Response":
            return self

        def __exit__(self, *_args: Any) -> None:
            return None

        def read(self) -> bytes:
            return json.dumps({
                "choices": [{"message": {"content": "ok"}}],
                "usage": {"total_tokens": 3},
            }).encode("utf-8")

    def opener(request: Any, timeout: int) -> Response:
        seen["url"] = request.full_url
        seen["authorization"] = request.get_header("Authorization")
        seen["timeout"] = timeout
        return Response()

    response = external_chat.invoke_chat_completion(
        provider,
        api_key="secret",
        payload={"model": "test-model", "messages": []},
        opener=opener,
    )

    assert seen == {
        "url": "https://example.test/v1/chat/completions",
        "authorization": "Bearer secret",
        "timeout": 120,
    }
    assert external_chat.extract_message_text(response) == "ok"


def test_invoke_chat_completion_retries_retryable_http_error() -> None:
    provider = external_chat.ProviderConfig(
        name="test",
        base_url="https://example.test/v1",
        api_key_env="TEST_KEY",
        model="test-model",
    )
    calls: list[str] = []
    sleeps: list[float] = []

    class Response:
        def __enter__(self) -> "Response":
            return self

        def __exit__(self, *_args: Any) -> None:
            return None

        def read(self) -> bytes:
            return json.dumps({
                "choices": [{"message": {"content": "ok"}}],
                "usage": {"total_tokens": 3},
            }).encode("utf-8")

    def opener(request: Any, timeout: int) -> Response:
        del request, timeout
        calls.append("attempt")
        if len(calls) == 1:
            raise urllib.error.HTTPError(
                url="https://example.test/v1/chat/completions",
                code=503,
                msg="unavailable",
                hdrs=None,
                fp=BytesIO(b"temporary outage"),
            )
        return Response()

    response = external_chat.invoke_chat_completion(
        provider,
        api_key="secret",
        payload={"model": "test-model", "messages": []},
        opener=opener,
        max_attempts=2,
        retry_delay_sec=4,
        sleeper=lambda seconds: sleeps.append(seconds),
    )

    assert len(calls) == 2
    assert sleeps == [4]
    assert external_chat.extract_message_text(response) == "ok"


def test_request_artifact_redacts_authorization(tmp_path: Path) -> None:
    provider = external_chat.ProviderConfig(
        name="test",
        base_url="https://example.test",
        api_key_env="TEST_KEY",
        model="test-model",
    )
    artifact_path = tmp_path / "request.json"

    external_chat.write_request_artifact(
        artifact_path,
        provider=provider,
        payload={"model": "test-model"},
    )

    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    assert artifact["headers"]["Authorization"] == "Bearer <redacted>"
    assert "secret" not in artifact_path.read_text(encoding="utf-8")


def test_request_artifact_does_not_write_direct_api_key(tmp_path: Path) -> None:
    provider = external_chat.ProviderConfig(
        name="test",
        base_url="https://example.test",
        api_key_env=None,
        api_key="direct-secret",
        model="test-model",
    )
    artifact_path = tmp_path / "request.json"

    external_chat.write_request_artifact(
        artifact_path,
        provider=provider,
        payload={"model": "test-model"},
    )

    artifact_text = artifact_path.read_text(encoding="utf-8")
    artifact = json.loads(artifact_text)
    assert artifact["api_key_configured"] is True
    assert "direct-secret" not in artifact_text


def test_request_artifact_redacts_payload_secrets(tmp_path: Path) -> None:
    provider = external_chat.ProviderConfig(
        name="test",
        base_url="https://example.test",
        api_key_env="TEST_KEY",
        model="test-model",
    )
    artifact_path = tmp_path / "request.json"

    external_chat.write_request_artifact(
        artifact_path,
        provider=provider,
        payload={
            "model": "test-model",
            "messages": [
                {
                    "role": "user",
                    "content": (
                        "api_key=raw-secret-value and "
                        "Authorization: Bearer raw-token-value"
                    ),
                }
            ],
        },
    )

    artifact_text = artifact_path.read_text(encoding="utf-8")
    artifact = json.loads(artifact_text)
    assert artifact["body"]["model"] == "test-model"
    assert "raw-secret-value" not in artifact_text
    assert "raw-token-value" not in artifact_text
    assert "<redacted>" in artifact_text


def test_meta_artifact_includes_cache_summary(tmp_path: Path) -> None:
    provider = external_chat.ProviderConfig(
        name="deepseek",
        base_url="https://api.deepseek.com",
        api_key_env="DEEPSEEK_API_KEY",
        model="deepseek-v4-pro",
    )
    artifact_path = tmp_path / "meta.json"

    external_chat.write_meta_artifact(
        artifact_path,
        provider=provider,
        response={
            "id": "response-id",
            "usage": {
                "prompt_cache_hit_tokens": 90,
                "prompt_cache_miss_tokens": 10,
                "total_tokens": 120,
            },
        },
    )

    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    assert artifact["cache"] == {
        "prompt_cache_hit_tokens": 90,
        "prompt_cache_miss_tokens": 10,
        "prompt_cache_total_tokens": 100,
        "prompt_cache_hit_rate": 0.9,
        "prompt_cache_miss_rate": 0.1,
    }


def test_unknown_provider_fails() -> None:
    with pytest.raises(external_chat.ModelApiError, match="Unknown provider"):
        external_chat.load_provider_config("missing", env={})


def test_agentic_review_tool_schema_exposes_repository_tools() -> None:
    tool_names = {
        tool["function"]["name"]
        for tool in agentic_review.AGENTIC_TOOLS
    }

    assert {
        "workflow_hints",
        "git_status",
        "list_files",
        "search_text",
        "read_file",
        "git_diff",
        "git_show",
    }.issubset(tool_names)


def test_agentic_review_workflow_hints_include_harness_rules() -> None:
    result = agentic_review.workflow_hints("hooks")

    assert result["ok"] is True
    assert "Hook model" in "\n".join(result["hints"]["hooks"])


def test_agentic_review_system_prompt_uses_provider_name() -> None:
    prompt = agentic_review.build_agentic_system_prompt(
        provider_name="openai_compatible",
    )

    assert "You are openai_compatible" in prompt
    assert "You are DeepSeek" not in prompt


def test_agentic_review_initial_prompt_redacts_task_secrets(tmp_path: Path) -> None:
    repo = _init_git_repo(tmp_path)
    (repo / "a.txt").write_text("tracked\n", encoding="utf-8")
    _git(repo, ["add", "a.txt"])
    _commit(repo, "initial")

    prompt = agentic_review.build_initial_user_prompt(
        repo,
        "Review api_key=raw-secret and sk-abcdefghijklmnopqrstuvwxyz12345",
    )

    assert "raw-secret" not in prompt
    assert "sk-abcdefghijklmnopqrstuvwxyz12345" not in prompt
    assert "<redacted>" in prompt


def test_redaction_preserves_api_key_annotations_and_lookups() -> None:
    annotation = "api_key: str | None = field(default=None)"
    lookup = 'api_key = _optional_str(merged.get("api_key"))'

    assert agentic_review.redact_secrets(annotation) == annotation
    assert agentic_review.redact_secrets(lookup) == lookup


def test_redaction_redacts_actual_api_key_values() -> None:
    text = (
        "api_key: sk-abcdefghijklmnopqrstuvwxyz\n"
        "deepseek_api_key=raw-secret-value\n"
        "api_key='direct-secret'\n"
    )

    redacted = agentic_review.redact_secrets(text)

    assert "sk-abcdefghijklmnopqrstuvwxyz" not in redacted
    assert "raw-secret-value" not in redacted
    assert "direct-secret" not in redacted
    assert redacted.count("<redacted>") == 3


def test_agentic_review_payload_scopes_thinking_extras() -> None:
    provider = external_chat.ProviderConfig(
        name="deepseek",
        base_url="https://api.deepseek.example",
        api_key_env="DEEPSEEK_API_KEY",
        model="deepseek-test",
        extra_body={
            "thinking": {"type": "enabled"},
            "reasoning_effort": "max",
            "metadata": {"review": "agentic"},
        },
    )
    messages = [{"role": "user", "content": "Review."}]

    default_payload = agentic_review.build_agentic_payload(
        provider,
        messages=messages,
        max_tokens=1024,
        temperature=None,
    )
    final_gather_payload = agentic_review.build_agentic_payload(
        provider,
        messages=messages,
        max_tokens=1024,
        temperature=None,
        thinking_scope="final",
        tool_choice="auto",
    )
    final_answer_payload = agentic_review.build_agentic_payload(
        provider,
        messages=messages,
        max_tokens=1024,
        temperature=None,
        thinking_scope="final",
        final_request=True,
    )
    none_payload = agentic_review.build_agentic_payload(
        provider,
        messages=messages,
        max_tokens=1024,
        temperature=None,
        thinking_scope="none",
    )

    assert default_payload["thinking"] == {"type": "enabled"}
    assert default_payload["reasoning_effort"] == "max"
    assert default_payload["metadata"] == {"review": "agentic"}
    assert "thinking" not in final_gather_payload
    assert "reasoning_effort" not in final_gather_payload
    assert final_gather_payload["metadata"] == {"review": "agentic"}
    assert final_answer_payload["thinking"] == {"type": "enabled"}
    assert final_answer_payload["reasoning_effort"] == "max"
    assert "thinking" not in none_payload
    assert "reasoning_effort" not in none_payload


def test_agentic_review_read_file_denies_ignored_local_secret(
    tmp_path: Path,
) -> None:
    repo = _init_git_repo(tmp_path)
    (repo / ".gitignore").write_text("*.local.yaml\n", encoding="utf-8")
    (repo / "tracked.txt").write_text("tracked\n", encoding="utf-8")
    _git(repo, ["add", ".gitignore", "tracked.txt"])
    _commit(repo, "initial")
    (repo / "providers.local.yaml").write_text(
        "api_key: sk-abcdefghijklmnopqrstuvwxyz\n",
        encoding="utf-8",
    )

    runtime = agentic_review.ToolRuntime(
        root=repo,
        limits=agentic_review.AgenticReviewLimits(),
    )
    tool_message = agentic_review.execute_tool_call(
        runtime,
        {
            "id": "call_read_secret",
            "function": {
                "name": "read_file",
                "arguments": json.dumps({"path": "providers.local.yaml"}),
            },
        },
    )
    result = json.loads(tool_message["content"])

    assert result["ok"] is False
    assert "not reviewable" in result["error"] or "secrets" in result["error"]


def test_agentic_review_read_file_denies_env_variants(tmp_path: Path) -> None:
    repo = _init_git_repo(tmp_path)
    (repo / ".env.production").write_text(
        "Authorization: Bearer raw-token-value\n",
        encoding="utf-8",
    )
    _git(repo, ["add", ".env.production"])
    _commit(repo, "initial")
    runtime = agentic_review.ToolRuntime(
        root=repo,
        limits=agentic_review.AgenticReviewLimits(),
    )

    tool_message = agentic_review.execute_tool_call(
        runtime,
        {
            "id": "call_read_env",
            "function": {
                "name": "read_file",
                "arguments": json.dumps({"path": ".env.production"}),
            },
        },
    )
    result = json.loads(tool_message["content"])

    assert result["ok"] is False
    assert "secrets" in result["error"]


def test_agentic_review_read_file_denies_untracked_by_default(
    tmp_path: Path,
) -> None:
    repo = _init_git_repo(tmp_path)
    (repo / "tracked.txt").write_text("tracked\n", encoding="utf-8")
    _git(repo, ["add", "tracked.txt"])
    _commit(repo, "initial")
    (repo / "local_note.txt").write_text("local only\n", encoding="utf-8")
    runtime = agentic_review.ToolRuntime(
        root=repo,
        limits=agentic_review.AgenticReviewLimits(),
    )

    tool_message = agentic_review.execute_tool_call(
        runtime,
        {
            "id": "call_read_untracked",
            "function": {
                "name": "read_file",
                "arguments": json.dumps({"path": "local_note.txt"}),
            },
        },
    )
    result = json.loads(tool_message["content"])

    assert result["ok"] is False
    assert "untracked file is not reviewable" in result["error"]


def test_agentic_review_read_file_allows_explicit_untracked_file(
    tmp_path: Path,
) -> None:
    repo = _init_git_repo(tmp_path)
    (repo / "tracked.txt").write_text("tracked\n", encoding="utf-8")
    _git(repo, ["add", "tracked.txt"])
    _commit(repo, "initial")
    (repo / "review_note.txt").write_text("local only\n", encoding="utf-8")
    runtime = agentic_review.ToolRuntime(
        root=repo,
        limits=agentic_review.AgenticReviewLimits(),
        allow_untracked_paths=("review_note.txt",),
    )

    tool_message = agentic_review.execute_tool_call(
        runtime,
        {
            "id": "call_read_untracked",
            "function": {
                "name": "read_file",
                "arguments": json.dumps({"path": "review_note.txt"}),
            },
        },
    )
    result = json.loads(tool_message["content"])

    assert result["ok"] is True
    assert "local only" in result["content"]


def test_agentic_review_git_status_hides_untracked_names_by_default(
    tmp_path: Path,
) -> None:
    repo = _init_git_repo(tmp_path)
    (repo / "tracked.txt").write_text("tracked\n", encoding="utf-8")
    _git(repo, ["add", "tracked.txt"])
    _commit(repo, "initial")
    (repo / "local_secret.json").write_text("token: opaque\n", encoding="utf-8")
    runtime = agentic_review.ToolRuntime(
        root=repo,
        limits=agentic_review.AgenticReviewLimits(),
    )

    result = agentic_review.run_local_tool(runtime, "git_status", {})

    assert result["ok"] is True
    assert "local_secret.json" not in result["status_short"]
    assert result["untracked_files"] == []
    assert result["untracked_omitted"] == 1


def test_agentic_review_rejects_unsafe_tool_arguments(tmp_path: Path) -> None:
    repo = _init_git_repo(tmp_path)
    (repo / "a.txt").write_text("tracked\n", encoding="utf-8")
    _git(repo, ["add", "a.txt"])
    _commit(repo, "initial")
    runtime = agentic_review.ToolRuntime(
        root=repo,
        limits=agentic_review.AgenticReviewLimits(),
    )

    tool_message = agentic_review.execute_tool_call(
        runtime,
        {
            "id": "call_bad_path",
            "function": {
                "name": "git_diff",
                "arguments": json.dumps({"path_prefix": "../outside"}),
            },
        },
    )
    result = json.loads(tool_message["content"])

    assert result["ok"] is False
    assert "escapes workspace" in result["error"]


def test_agentic_review_search_handles_dash_prefixed_patterns(tmp_path: Path) -> None:
    repo = _init_git_repo(tmp_path)
    (repo / "a.txt").write_text("value: -needle\n", encoding="utf-8")
    _git(repo, ["add", "a.txt"])
    _commit(repo, "initial")
    runtime = agentic_review.ToolRuntime(
        root=repo,
        limits=agentic_review.AgenticReviewLimits(),
    )

    result = agentic_review.run_local_tool(
        runtime,
        "search_text",
        {"pattern": "-needle"},
    )

    assert result["ok"] is True
    assert result["matches"] == ["a.txt:1:value: -needle"]


def test_agentic_review_search_ignores_untracked_files_by_default(
    tmp_path: Path,
) -> None:
    repo = _init_git_repo(tmp_path)
    (repo / "tracked.txt").write_text("tracked needle\n", encoding="utf-8")
    _git(repo, ["add", "tracked.txt"])
    _commit(repo, "initial")
    (repo / "local_note.txt").write_text("untracked needle\n", encoding="utf-8")
    runtime = agentic_review.ToolRuntime(
        root=repo,
        limits=agentic_review.AgenticReviewLimits(),
    )

    result = agentic_review.run_local_tool(
        runtime,
        "search_text",
        {"pattern": "needle"},
    )

    assert result["ok"] is True
    assert result["matches"] == ["tracked.txt:1:tracked needle"]


def test_agentic_review_denied_rg_globs_come_from_constants() -> None:
    args = agentic_review.denied_rg_glob_args()
    globs = [args[index + 1] for index in range(0, len(args), 2)]

    assert all(args[index] == "--glob" for index in range(0, len(args), 2))
    assert "!*.pem" in globs
    assert "!.env.*" in globs
    assert "!providers.local.yaml" in globs
    assert "!.harness_hooks/**" in globs


def test_agentic_review_denied_git_grep_pathspecs_come_from_constants() -> None:
    pathspecs = agentic_review.denied_git_grep_pathspecs()

    assert ":(exclude)*.pem" in pathspecs
    assert ":(exclude).env.*" in pathspecs
    assert ":(exclude)providers.local.yaml" in pathspecs
    assert ":(exclude).harness_hooks/**" in pathspecs


def test_agentic_review_search_falls_back_to_git_grep(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = _init_git_repo(tmp_path)
    (repo / "a.txt").write_text("value: needle\n", encoding="utf-8")
    _git(repo, ["add", "a.txt"])
    _commit(repo, "initial")
    runtime = agentic_review.ToolRuntime(
        root=repo,
        limits=agentic_review.AgenticReviewLimits(),
    )
    real_run = subprocess.run

    def fake_run(command: list[str], *args: Any, **kwargs: Any) -> Any:
        if command and command[0] == "rg":
            raise FileNotFoundError("rg")
        return real_run(command, *args, **kwargs)

    monkeypatch.setattr(agentic_review.subprocess, "run", fake_run)

    result = agentic_review.run_local_tool(
        runtime,
        "search_text",
        {"pattern": "needle"},
    )

    assert result["ok"] is True
    assert result["search_engine"] == "git grep"
    assert result["matches"] == ["a.txt:1:value: needle"]


def test_agentic_review_git_grep_fallback_omits_denied_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = _init_git_repo(tmp_path)
    (repo / ".env.production").write_text(
        "Authorization: Bearer raw-token-value\n",
        encoding="utf-8",
    )
    (repo / "a.txt").write_text("value: raw-token-value\n", encoding="utf-8")
    _git(repo, ["add", ".env.production", "a.txt"])
    _commit(repo, "initial")
    runtime = agentic_review.ToolRuntime(
        root=repo,
        limits=agentic_review.AgenticReviewLimits(),
    )
    real_run = subprocess.run
    commands: list[list[str]] = []

    def fake_run(command: list[str], *args: Any, **kwargs: Any) -> Any:
        if command and command[0] == "rg":
            raise FileNotFoundError("rg")
        commands.append(command)
        return real_run(command, *args, **kwargs)

    monkeypatch.setattr(agentic_review.subprocess, "run", fake_run)

    result = agentic_review.run_local_tool(
        runtime,
        "search_text",
        {"pattern": "raw-token-value"},
    )

    assert result["ok"] is True
    assert result["search_engine"] == "git grep"
    assert result["omitted_denied"] == 0
    assert result["matches"] == ["a.txt:1:value: raw-token-value"]
    assert any(token == ":(exclude).env.*" for token in commands[-1])


def test_agentic_review_search_timeout_is_reported(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = _init_git_repo(tmp_path)
    (repo / "a.txt").write_text("value: needle\n", encoding="utf-8")
    _git(repo, ["add", "a.txt"])
    _commit(repo, "initial")
    runtime = agentic_review.ToolRuntime(
        root=repo,
        limits=agentic_review.AgenticReviewLimits(tool_timeout_sec=7),
    )

    def fake_run(command: list[str], *args: Any, **kwargs: Any) -> Any:
        del args
        assert kwargs["timeout"] == 7
        raise subprocess.TimeoutExpired(command, kwargs["timeout"])

    monkeypatch.setattr(agentic_review.subprocess, "run", fake_run)

    with pytest.raises(agentic_review.AgenticReviewError, match="timed out after 7s"):
        agentic_review.run_local_tool(
            runtime,
            "search_text",
            {"pattern": "needle"},
        )


def test_agentic_review_truncates_text_on_utf8_boundary() -> None:
    text, truncated = agentic_review._truncate_text("a你b", 2)

    assert truncated is True
    assert text == "a"
    assert len(text.encode("utf-8")) <= 2


def test_agentic_review_git_show_denies_secret_paths(tmp_path: Path) -> None:
    repo = _init_git_repo(tmp_path)
    (repo / "a.txt").write_text("tracked\n", encoding="utf-8")
    _git(repo, ["add", "a.txt"])
    _commit(repo, "initial")
    runtime = agentic_review.ToolRuntime(
        root=repo,
        limits=agentic_review.AgenticReviewLimits(),
    )

    tool_message = agentic_review.execute_tool_call(
        runtime,
        {
            "id": "call_git_show_secret",
            "function": {
                "name": "git_show",
                "arguments": json.dumps({"path": "providers.local.yaml"}),
            },
        },
    )
    result = json.loads(tool_message["content"])

    assert result["ok"] is False
    assert "secrets" in result["error"]


def test_agentic_review_git_diff_omits_denied_paths(tmp_path: Path) -> None:
    repo = _init_git_repo(tmp_path)
    (repo / "safe.txt").write_text("safe base\n", encoding="utf-8")
    (repo / ".env.production").write_text(
        "LOCAL_PASSWORD=base-secret\n",
        encoding="utf-8",
    )
    _git(repo, ["add", "safe.txt", ".env.production"])
    _commit(repo, "initial")
    (repo / "safe.txt").write_text("safe current\n", encoding="utf-8")
    (repo / ".env.production").write_text(
        "LOCAL_PASSWORD=diff-secret\n",
        encoding="utf-8",
    )
    runtime = agentic_review.ToolRuntime(
        root=repo,
        limits=agentic_review.AgenticReviewLimits(),
    )

    result = agentic_review.run_local_tool(runtime, "git_diff", {})

    assert result["ok"] is True
    assert "safe current" in result["content"]
    assert "diff-secret" not in result["content"]
    assert result["omitted_denied_paths"] == [".env.production"]


def test_agentic_review_git_tools_include_staged_only_diff(tmp_path: Path) -> None:
    repo = _init_git_repo(tmp_path)
    (repo / "a.txt").write_text("base\n", encoding="utf-8")
    _git(repo, ["add", "a.txt"])
    _commit(repo, "initial")
    (repo / "a.txt").write_text("staged\n", encoding="utf-8")
    _git(repo, ["add", "a.txt"])
    (repo / "a.txt").write_text("base\n", encoding="utf-8")
    runtime = agentic_review.ToolRuntime(
        root=repo,
        limits=agentic_review.AgenticReviewLimits(),
    )

    status = agentic_review.tool_git_status(repo)
    diff = agentic_review.run_local_tool(runtime, "git_diff", {})

    assert status["status_short"].strip() == "MM a.txt"
    assert status["changed_files"] == ["a.txt"]
    assert "base HEAD -> index (staged)" in diff["content"]
    assert "staged" in diff["content"]
    assert "index -> worktree (unstaged)" in diff["content"]


def test_agentic_review_invalid_tool_json_returns_tool_error(tmp_path: Path) -> None:
    repo = _init_git_repo(tmp_path)
    (repo / "a.txt").write_text("tracked\n", encoding="utf-8")
    _git(repo, ["add", "a.txt"])
    _commit(repo, "initial")
    runtime = agentic_review.ToolRuntime(
        root=repo,
        limits=agentic_review.AgenticReviewLimits(),
    )

    tool_message = agentic_review.execute_tool_call(
        runtime,
        {
            "id": "call_bad_json",
            "function": {"name": "read_file", "arguments": "{bad json"},
        },
    )
    result = json.loads(tool_message["content"])

    assert result["ok"] is False
    assert "invalid tool arguments JSON" in result["error"]


def test_agentic_review_run_handles_tool_call_loop(tmp_path: Path) -> None:
    repo = _init_git_repo(tmp_path)
    (repo / "a.txt").write_text("line one\nline two\n", encoding="utf-8")
    _git(repo, ["add", "a.txt"])
    _commit(repo, "initial")
    provider = external_chat.ProviderConfig(
        name="deepseek",
        base_url="https://api.deepseek.example",
        api_key_env="DEEPSEEK_API_KEY",
        model="deepseek-test",
    )
    requests: list[dict[str, Any]] = []
    responses = [
        {
            "id": "resp-1",
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "",
                        "tool_calls": [
                            {
                                "id": "call-1",
                                "type": "function",
                                "function": {
                                    "name": "read_file",
                                    "arguments": json.dumps({"path": "a.txt"}),
                                },
                            }
                        ],
                    },
                    "finish_reason": "tool_calls",
                }
            ],
            "usage": {"prompt_tokens": 10, "completion_tokens": 2},
        },
        {
            "id": "resp-2",
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "No findings.\n",
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 20, "completion_tokens": 3},
        },
    ]

    class Response:
        def __init__(self, payload: dict[str, Any]) -> None:
            self.payload = payload

        def __enter__(self) -> "Response":
            return self

        def __exit__(self, *_args: Any) -> None:
            return None

        def read(self) -> bytes:
            return json.dumps(self.payload).encode("utf-8")

    def opener(request: Any, timeout: int) -> Response:
        del timeout
        requests.append(json.loads(request.data.decode("utf-8")))
        return Response(responses[len(requests) - 1])

    result = agentic_review.run_agentic_review(
        provider,
        api_key="secret",
        workspace_root=repo,
        task="Review a.txt",
        limits=agentic_review.AgenticReviewLimits(max_iterations=3),
        opener=opener,
    )

    assert result.text == "No findings.\n"
    assert requests[0]["tools"]
    assert any(message["role"] == "tool" for message in result.messages)
    assert result.meta["tool_calls"] == 1
    assert result.meta["usage"]["prompt_tokens"] == 30


def test_agentic_review_defaults_to_all_request_thinking_scope(
    tmp_path: Path,
) -> None:
    repo = _init_git_repo(tmp_path)
    (repo / "a.txt").write_text("line one\n", encoding="utf-8")
    _git(repo, ["add", "a.txt"])
    _commit(repo, "initial")
    provider = external_chat.ProviderConfig(
        name="deepseek",
        base_url="https://api.deepseek.example",
        api_key_env="DEEPSEEK_API_KEY",
        model="deepseek-test",
        extra_body={
            "thinking": {"type": "enabled"},
            "reasoning_effort": "max",
            "metadata": {"review": "agentic"},
        },
    )
    requests: list[dict[str, Any]] = []
    responses = [
        {
            "id": "resp-1",
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "",
                        "tool_calls": [
                            {
                                "id": "call-1",
                                "type": "function",
                                "function": {
                                    "name": "read_file",
                                    "arguments": json.dumps({"path": "a.txt"}),
                                },
                            }
                        ],
                    },
                    "finish_reason": "tool_calls",
                }
            ],
            "usage": {"prompt_tokens": 10, "completion_tokens": 2},
        },
        {
            "id": "resp-2",
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "Final review.\n",
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 20, "completion_tokens": 3},
        },
    ]

    class Response:
        def __init__(self, payload: dict[str, Any]) -> None:
            self.payload = payload

        def __enter__(self) -> "Response":
            return self

        def __exit__(self, *_args: Any) -> None:
            return None

        def read(self) -> bytes:
            return json.dumps(self.payload).encode("utf-8")

    def opener(request: Any, timeout: int) -> Response:
        del timeout
        requests.append(json.loads(request.data.decode("utf-8")))
        return Response(responses[len(requests) - 1])

    result = agentic_review.run_agentic_review(
        provider,
        api_key="secret",
        workspace_root=repo,
        task="Review a.txt",
        limits=agentic_review.AgenticReviewLimits(max_iterations=2),
        opener=opener,
    )

    assert result.meta["thinking_scope"] == "all"
    assert requests[0]["metadata"] == {"review": "agentic"}
    assert requests[0]["thinking"] == {"type": "enabled"}
    assert requests[0]["reasoning_effort"] == "max"
    assert requests[1]["thinking"] == {"type": "enabled"}
    assert requests[1]["reasoning_effort"] == "max"


def test_agentic_review_can_apply_thinking_to_all_requests(
    tmp_path: Path,
) -> None:
    repo = _init_git_repo(tmp_path)
    (repo / "a.txt").write_text("line one\n", encoding="utf-8")
    _git(repo, ["add", "a.txt"])
    _commit(repo, "initial")
    provider = external_chat.ProviderConfig(
        name="deepseek",
        base_url="https://api.deepseek.example",
        api_key_env="DEEPSEEK_API_KEY",
        model="deepseek-test",
        extra_body={
            "thinking": {"type": "enabled"},
            "reasoning_effort": "max",
        },
    )
    requests: list[dict[str, Any]] = []
    response = {
        "id": "resp-1",
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": "No findings.\n",
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 10, "completion_tokens": 2},
    }

    class Response:
        def __enter__(self) -> "Response":
            return self

        def __exit__(self, *_args: Any) -> None:
            return None

        def read(self) -> bytes:
            return json.dumps(response).encode("utf-8")

    def opener(request: Any, timeout: int) -> Response:
        del timeout
        requests.append(json.loads(request.data.decode("utf-8")))
        return Response()

    agentic_review.run_agentic_review(
        provider,
        api_key="secret",
        workspace_root=repo,
        task="Review a.txt",
        thinking_scope="all",
        opener=opener,
    )

    assert requests[0]["thinking"] == {"type": "enabled"}
    assert requests[0]["reasoning_effort"] == "max"


def test_agentic_review_forces_final_on_last_iteration(tmp_path: Path) -> None:
    repo = _init_git_repo(tmp_path)
    (repo / "a.txt").write_text("line one\n", encoding="utf-8")
    _git(repo, ["add", "a.txt"])
    _commit(repo, "initial")
    provider = external_chat.ProviderConfig(
        name="deepseek",
        base_url="https://api.deepseek.example",
        api_key_env="DEEPSEEK_API_KEY",
        model="deepseek-test",
    )
    requests: list[dict[str, Any]] = []
    responses = [
        {
            "id": "resp-1",
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "",
                        "tool_calls": [
                            {
                                "id": "call-1",
                                "type": "function",
                                "function": {
                                    "name": "read_file",
                                    "arguments": json.dumps({"path": "a.txt"}),
                                },
                            }
                        ],
                    },
                    "finish_reason": "tool_calls",
                }
            ],
            "usage": {"prompt_tokens": 10, "completion_tokens": 2},
        },
        {
            "id": "resp-2",
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "Final review.\n",
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 20, "completion_tokens": 3},
        },
    ]

    class Response:
        def __init__(self, payload: dict[str, Any]) -> None:
            self.payload = payload

        def __enter__(self) -> "Response":
            return self

        def __exit__(self, *_args: Any) -> None:
            return None

        def read(self) -> bytes:
            return json.dumps(self.payload).encode("utf-8")

    def opener(request: Any, timeout: int) -> Response:
        del timeout
        requests.append(json.loads(request.data.decode("utf-8")))
        return Response(responses[len(requests) - 1])

    result = agentic_review.run_agentic_review(
        provider,
        api_key="secret",
        workspace_root=repo,
        task="Review a.txt",
        limits=agentic_review.AgenticReviewLimits(max_iterations=2),
        opener=opener,
    )

    assert result.text == "Final review.\n"
    assert requests[0]["tool_choice"] == "auto"
    assert "tool_choice" not in requests[1]
    assert "tools" not in requests[1]
    assert requests[1]["messages"][-1]["content"].startswith("Stop using tools now")


def test_agentic_review_retries_final_after_rejected_tool_call(
    tmp_path: Path,
) -> None:
    repo = _init_git_repo(tmp_path)
    (repo / "a.txt").write_text("line one\n", encoding="utf-8")
    _git(repo, ["add", "a.txt"])
    _commit(repo, "initial")
    provider = external_chat.ProviderConfig(
        name="deepseek",
        base_url="https://api.deepseek.example",
        api_key_env="DEEPSEEK_API_KEY",
        model="deepseek-test",
    )
    requests: list[dict[str, Any]] = []
    responses = [
        {
            "id": "resp-tool-after-final",
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "",
                        "tool_calls": [
                            {
                                "id": "call-after-final",
                                "type": "function",
                                "function": {
                                    "name": "read_file",
                                    "arguments": json.dumps({"path": "a.txt"}),
                                },
                            }
                        ],
                    },
                    "finish_reason": "tool_calls",
                }
            ],
            "usage": {"prompt_tokens": 10, "completion_tokens": 2},
        },
        {
            "id": "resp-final-retry",
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "Final after rejection.\n",
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 20, "completion_tokens": 3},
        },
    ]

    class Response:
        def __init__(self, payload: dict[str, Any]) -> None:
            self.payload = payload

        def __enter__(self) -> "Response":
            return self

        def __exit__(self, *_args: Any) -> None:
            return None

        def read(self) -> bytes:
            return json.dumps(self.payload).encode("utf-8")

    def opener(request: Any, timeout: int) -> Response:
        del timeout
        requests.append(json.loads(request.data.decode("utf-8")))
        return Response(responses[len(requests) - 1])

    result = agentic_review.run_agentic_review(
        provider,
        api_key="secret",
        workspace_root=repo,
        task="Review a.txt",
        limits=agentic_review.AgenticReviewLimits(max_iterations=1),
        opener=opener,
    )

    assert result.text == "Final after rejection.\n"
    assert len(requests) == 2
    assert "tool_choice" not in requests[0]
    assert "tools" not in requests[0]
    assert "tool_choice" not in requests[1]
    assert "tools" not in requests[1]
    assert result.meta["final_rejected_tool_calls"] == 1
    assert result.trace["responses"][1]["final_retry_after_rejected_tools"] is True


def test_agentic_review_rejects_impossible_force_final_limit(tmp_path: Path) -> None:
    repo = _init_git_repo(tmp_path)
    (repo / "a.txt").write_text("line one\n", encoding="utf-8")
    _git(repo, ["add", "a.txt"])
    _commit(repo, "initial")
    provider = external_chat.ProviderConfig(
        name="deepseek",
        base_url="https://api.deepseek.example",
        api_key_env="DEEPSEEK_API_KEY",
        model="deepseek-test",
    )

    with pytest.raises(
        agentic_review.AgenticReviewError,
        match="force_final_after_tool_calls must be <= max_tool_calls",
    ):
        agentic_review.run_agentic_review(
            provider,
            api_key="secret",
            workspace_root=repo,
            task="Review a.txt",
            limits=agentic_review.AgenticReviewLimits(
                max_tool_calls=1,
                force_final_after_tool_calls=2,
            ),
        )


def test_agentic_cli_default_force_final_clamps_to_max_tool_calls() -> None:
    assert (
        agentic_review.resolve_force_final_after_tool_calls(
            max_tool_calls=30,
            requested=None,
        )
        == 30
    )


def test_agentic_cli_respects_explicit_force_final_limit() -> None:
    assert (
        agentic_review.resolve_force_final_after_tool_calls(
            max_tool_calls=30,
            requested=12,
        )
        == 12
    )


def test_agentic_review_retries_unchanged_high_miss_final_payload(
    tmp_path: Path,
) -> None:
    repo = _init_git_repo(tmp_path)
    (repo / "a.txt").write_text("line one\n", encoding="utf-8")
    _git(repo, ["add", "a.txt"])
    _commit(repo, "initial")
    provider = external_chat.ProviderConfig(
        name="deepseek",
        base_url="https://api.deepseek.example",
        api_key_env="DEEPSEEK_API_KEY",
        model="deepseek-test",
    )
    requests: list[dict[str, Any]] = []
    sleeps: list[float] = []
    responses = [
        {
            "id": "resp-1",
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "First final.\n",
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 2,
                "prompt_cache_hit_tokens": 1,
                "prompt_cache_miss_tokens": 9,
            },
        },
        {
            "id": "resp-2",
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "Retried final.\n",
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 2,
                "prompt_cache_hit_tokens": 9,
                "prompt_cache_miss_tokens": 1,
            },
        },
    ]

    class Response:
        def __init__(self, payload: dict[str, Any]) -> None:
            self.payload = payload

        def __enter__(self) -> "Response":
            return self

        def __exit__(self, *_args: Any) -> None:
            return None

        def read(self) -> bytes:
            return json.dumps(self.payload).encode("utf-8")

    def opener(request: Any, timeout: int) -> Response:
        del timeout
        requests.append(json.loads(request.data.decode("utf-8")))
        return Response(responses[len(requests) - 1])

    result = agentic_review.run_agentic_review(
        provider,
        api_key="secret",
        workspace_root=repo,
        task="Review a.txt",
        limits=agentic_review.AgenticReviewLimits(max_iterations=1),
        cache_retry_miss_rate=0.8,
        cache_retry_delay_sec=5,
        sleeper=lambda seconds: sleeps.append(seconds),
        opener=opener,
    )

    assert result.text == "Retried final.\n"
    assert result.meta["cache_retry_used"] is True
    assert sleeps == [5]
    assert requests[0] == requests[1]
    assert result.trace["responses"][0]["cache_retry"] is False
    assert result.trace["responses"][0]["cache_retry_retried"] is True
    assert result.trace["responses"][1]["cache_retry"] is True
    assert (
        result.trace["responses"][0]["payload"]["payload_sha256"]
        == result.trace["responses"][1]["payload"]["payload_sha256"]
    )


def test_agentic_review_can_retry_high_miss_non_final_payload(
    tmp_path: Path,
) -> None:
    repo = _init_git_repo(tmp_path)
    (repo / "a.txt").write_text("line one\n", encoding="utf-8")
    _git(repo, ["add", "a.txt"])
    _commit(repo, "initial")
    provider = external_chat.ProviderConfig(
        name="deepseek",
        base_url="https://api.deepseek.example",
        api_key_env="DEEPSEEK_API_KEY",
        model="deepseek-test",
    )
    requests: list[dict[str, Any]] = []
    sleeps: list[float] = []
    responses = [
        {
            "id": "resp-cold",
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "",
                        "tool_calls": [
                            {
                                "id": "call-cold",
                                "type": "function",
                                "function": {
                                    "name": "read_file",
                                    "arguments": json.dumps({"path": "a.txt"}),
                                },
                            }
                        ],
                    },
                    "finish_reason": "tool_calls",
                }
            ],
            "usage": {
                "prompt_cache_hit_tokens": 0,
                "prompt_cache_miss_tokens": 10,
            },
        },
        {
            "id": "resp-retry",
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "",
                        "tool_calls": [
                            {
                                "id": "call-retry",
                                "type": "function",
                                "function": {
                                    "name": "git_status",
                                    "arguments": "{}",
                                },
                            }
                        ],
                    },
                    "finish_reason": "tool_calls",
                }
            ],
            "usage": {
                "prompt_cache_hit_tokens": 9,
                "prompt_cache_miss_tokens": 1,
            },
        },
        {
            "id": "resp-final",
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "Final review.\n",
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 20, "completion_tokens": 3},
        },
    ]

    class Response:
        def __init__(self, payload: dict[str, Any]) -> None:
            self.payload = payload

        def __enter__(self) -> "Response":
            return self

        def __exit__(self, *_args: Any) -> None:
            return None

        def read(self) -> bytes:
            return json.dumps(self.payload).encode("utf-8")

    def opener(request: Any, timeout: int) -> Response:
        del timeout
        requests.append(json.loads(request.data.decode("utf-8")))
        return Response(responses[len(requests) - 1])

    result = agentic_review.run_agentic_review(
        provider,
        api_key="secret",
        workspace_root=repo,
        task="Review a.txt",
        limits=agentic_review.AgenticReviewLimits(max_iterations=3),
        cache_retry_scope="all",
        cache_retry_miss_rate=0.8,
        cache_retry_delay_sec=5,
        sleeper=lambda seconds: sleeps.append(seconds),
        opener=opener,
    )

    assert result.text == "Final review.\n"
    assert result.meta["cache_retry_scope"] == "all"
    assert result.meta["cache_retry_used"] is True
    assert sleeps == [5]
    assert requests[0] == requests[1]
    assert result.meta["tool_calls"] == 1
    assert result.trace["tool_events"][0]["tool"] == "git_status"
    assert result.trace["responses"][0]["cache_retry_retried"] is True
    assert result.trace["responses"][1]["cache_retry"] is True


def test_agentic_review_incomplete_error_carries_trace(tmp_path: Path) -> None:
    repo = _init_git_repo(tmp_path)
    (repo / "a.txt").write_text("line one\n", encoding="utf-8")
    _git(repo, ["add", "a.txt"])
    _commit(repo, "initial")
    provider = external_chat.ProviderConfig(
        name="deepseek",
        base_url="https://api.deepseek.example",
        api_key_env="DEEPSEEK_API_KEY",
        model="deepseek-test",
    )
    response = {
        "id": "resp-1",
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {
                            "id": "call-1",
                            "type": "function",
                            "function": {
                                "name": "read_file",
                                "arguments": json.dumps({"path": "a.txt"}),
                            },
                        }
                    ],
                },
                "finish_reason": "tool_calls",
            }
        ],
        "usage": {"prompt_tokens": 10, "completion_tokens": 2},
    }

    class Response:
        def __enter__(self) -> "Response":
            return self

        def __exit__(self, *_args: Any) -> None:
            return None

        def read(self) -> bytes:
            return json.dumps(response).encode("utf-8")

    def opener(request: Any, timeout: int) -> Response:
        del request, timeout
        return Response()

    with pytest.raises(agentic_review.AgenticReviewIncompleteError) as exc_info:
        agentic_review.run_agentic_review(
            provider,
            api_key="secret",
            workspace_root=repo,
            task="Review a.txt",
            limits=agentic_review.AgenticReviewLimits(max_iterations=1),
            opener=opener,
        )

    assert exc_info.value.trace["status"] == "final_tool_calls_rejected"
    assert exc_info.value.meta["tool_calls"] == 0
    assert exc_info.value.meta["final_rejected_tool_calls"] == 2


def test_agentic_review_retries_pseudo_tool_call_final_content(
    tmp_path: Path,
) -> None:
    repo = _init_git_repo(tmp_path)
    (repo / "a.txt").write_text("line one\n", encoding="utf-8")
    _git(repo, ["add", "a.txt"])
    _commit(repo, "initial")
    provider = external_chat.ProviderConfig(
        name="deepseek",
        base_url="https://api.deepseek.example",
        api_key_env="DEEPSEEK_API_KEY",
        model="deepseek-test",
    )
    responses = [
        {
            "id": "resp-markup",
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": (
                            "<｜｜DSML｜｜tool_calls>\n"
                            "<｜｜DSML｜｜invoke name=\"read_file\">"
                        ),
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 10, "completion_tokens": 2},
        },
        {
            "id": "resp-final",
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "Final review.\n",
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 12, "completion_tokens": 3},
        },
    ]
    requests: list[dict[str, Any]] = []

    class Response:
        def __init__(self, payload: dict[str, Any]) -> None:
            self.payload = payload

        def __enter__(self) -> "Response":
            return self

        def __exit__(self, *_args: Any) -> None:
            return None

        def read(self) -> bytes:
            return json.dumps(self.payload).encode("utf-8")

    def opener(request: Any, timeout: int) -> Response:
        del timeout
        requests.append(json.loads(request.data.decode("utf-8")))
        return Response(responses[len(requests) - 1])

    result = agentic_review.run_agentic_review(
        provider,
        api_key="secret",
        workspace_root=repo,
        task="Review a.txt",
        limits=agentic_review.AgenticReviewLimits(max_iterations=1),
        opener=opener,
    )

    assert result.text == "Final review.\n"
    assert len(requests) == 2
    assert "tools" not in requests[0]
    assert "tools" not in requests[1]
    assert "tool-call markup" in requests[1]["messages"][-1]["content"]
    assert result.trace["status"] == "completed"
    assert result.trace["responses"][1]["final_retry_after_invalid_content"] is True


def test_agentic_review_rejects_repeated_pseudo_tool_call_final_content(
    tmp_path: Path,
) -> None:
    repo = _init_git_repo(tmp_path)
    (repo / "a.txt").write_text("line one\n", encoding="utf-8")
    _git(repo, ["add", "a.txt"])
    _commit(repo, "initial")
    provider = external_chat.ProviderConfig(
        name="deepseek",
        base_url="https://api.deepseek.example",
        api_key_env="DEEPSEEK_API_KEY",
        model="deepseek-test",
    )
    response = {
        "id": "resp-markup",
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": (
                        "<tool_calls><tool_call name=\"read_file\" />"
                        "</tool_calls>"
                    ),
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 10, "completion_tokens": 2},
    }

    class Response:
        def __enter__(self) -> "Response":
            return self

        def __exit__(self, *_args: Any) -> None:
            return None

        def read(self) -> bytes:
            return json.dumps(response).encode("utf-8")

    def opener(request: Any, timeout: int) -> Response:
        del request, timeout
        return Response()

    with pytest.raises(agentic_review.AgenticReviewIncompleteError) as exc_info:
        agentic_review.run_agentic_review(
            provider,
            api_key="secret",
            workspace_root=repo,
            task="Review a.txt",
            limits=agentic_review.AgenticReviewLimits(max_iterations=1),
            opener=opener,
        )

    assert exc_info.value.trace["status"] == "invalid_final_response"
    assert "tool-call markup" in exc_info.value.meta["failure_reason"]


def test_review_prompt_keeps_head_snapshot_before_dynamic_suffix(
    tmp_path: Path,
) -> None:
    repo = _init_git_repo(tmp_path)
    (repo / "a.txt").write_text("head content\n", encoding="utf-8")
    _git(repo, ["add", "a.txt"])
    _commit(repo, "initial")
    (repo / "a.txt").write_text("working tree content\n", encoding="utf-8")

    prompt = build_review_prompt.build_review_prompt(
        workspace_root=repo,
        task="Review the workflow.",
        scope="full",
    )

    dynamic_index = prompt.index(build_review_prompt.DYNAMIC_MARKER)
    assert prompt.index("head content") < dynamic_index
    assert prompt.index("working tree content") > dynamic_index
    assert prompt.index("## Review Task") > dynamic_index
    assert prompt.index("## Git Snapshot") > dynamic_index


def test_review_prompt_stable_prefix_survives_worktree_changes(
    tmp_path: Path,
) -> None:
    repo = _init_git_repo(tmp_path)
    (repo / "a.txt").write_text("head content\n", encoding="utf-8")
    _git(repo, ["add", "a.txt"])
    _commit(repo, "initial")

    (repo / "a.txt").write_text("first worktree edit\n", encoding="utf-8")
    first_prompt = build_review_prompt.build_review_prompt(
        workspace_root=repo,
        task="First review task.",
        scope="full",
    )
    (repo / "a.txt").write_text("second worktree edit\n", encoding="utf-8")
    second_prompt = build_review_prompt.build_review_prompt(
        workspace_root=repo,
        task="Second review task.",
        scope="full",
    )

    first_prefix = first_prompt.split(
        build_review_prompt.DYNAMIC_MARKER,
        maxsplit=1,
    )[0]
    second_prefix = second_prompt.split(
        build_review_prompt.DYNAMIC_MARKER,
        maxsplit=1,
    )[0]
    assert first_prefix == second_prefix
    assert "first worktree edit" not in first_prefix
    assert "second worktree edit" not in second_prefix


def test_review_prompt_snapshot_ref_survives_later_commits(
    tmp_path: Path,
) -> None:
    repo = _init_git_repo(tmp_path)
    (repo / "a.txt").write_text("base content\n", encoding="utf-8")
    _git(repo, ["add", "a.txt"])
    _commit(repo, "base")
    snapshot_ref = _git_text(repo, ["rev-parse", "HEAD"]).strip()

    (repo / "a.txt").write_text("second commit content\n", encoding="utf-8")
    _git(repo, ["add", "a.txt"])
    _commit(repo, "second")
    first_prompt = build_review_prompt.build_review_prompt(
        workspace_root=repo,
        task="First review task.",
        scope="full",
        snapshot_ref=snapshot_ref,
    )

    (repo / "a.txt").write_text("third commit content\n", encoding="utf-8")
    _git(repo, ["add", "a.txt"])
    _commit(repo, "third")
    second_prompt = build_review_prompt.build_review_prompt(
        workspace_root=repo,
        task="Second review task.",
        scope="full",
        snapshot_ref=snapshot_ref,
    )

    first_prefix = first_prompt.split(
        build_review_prompt.DYNAMIC_MARKER,
        maxsplit=1,
    )[0]
    second_prefix = second_prompt.split(
        build_review_prompt.DYNAMIC_MARKER,
        maxsplit=1,
    )[0]
    second_suffix = second_prompt.split(
        build_review_prompt.DYNAMIC_MARKER,
        maxsplit=1,
    )[1]
    assert first_prefix == second_prefix
    assert "base content" in first_prefix
    assert "second commit content" not in first_prefix
    assert "third commit content" not in second_prefix
    assert "third commit content" in second_suffix


def test_review_prompt_defaults_to_changed_scope(tmp_path: Path) -> None:
    repo = _init_git_repo(tmp_path)
    (repo / "changed.txt").write_text("base changed\n", encoding="utf-8")
    (repo / "unchanged.txt").write_text("expensive unchanged\n", encoding="utf-8")
    _git(repo, ["add", "changed.txt", "unchanged.txt"])
    _commit(repo, "initial")
    (repo / "changed.txt").write_text("current changed\n", encoding="utf-8")

    prompt = build_review_prompt.build_review_prompt(
        workspace_root=repo,
        task="Review changed files only.",
    )

    assert "scope: changed" in prompt
    assert "current changed" in prompt
    assert "base changed" in prompt
    assert "expensive unchanged" not in prompt
    assert "Unchanged repository files are intentionally omitted" in prompt


def test_review_prompt_includes_operator_selected_context_files(
    tmp_path: Path,
) -> None:
    repo = _init_git_repo(tmp_path)
    (repo / "changed.txt").write_text("base changed\n", encoding="utf-8")
    (repo / "context.txt").write_text("selected context\n", encoding="utf-8")
    _git(repo, ["add", "changed.txt", "context.txt"])
    _commit(repo, "initial")
    (repo / "changed.txt").write_text("current changed\n", encoding="utf-8")

    prompt = build_review_prompt.build_review_prompt(
        workspace_root=repo,
        task="Review with context.",
        context_files=("context.txt",),
    )

    assert "source: context-file" in prompt
    assert "selected context" in prompt


def test_review_prompt_include_path_filters_changed_files(tmp_path: Path) -> None:
    repo = _init_git_repo(tmp_path)
    (repo / "a.txt").write_text("base a\n", encoding="utf-8")
    (repo / "b.txt").write_text("base b\n", encoding="utf-8")
    _git(repo, ["add", "a.txt", "b.txt"])
    _commit(repo, "initial")
    (repo / "a.txt").write_text("current a\n", encoding="utf-8")
    (repo / "b.txt").write_text("current b\n", encoding="utf-8")

    prompt = build_review_prompt.build_review_prompt(
        workspace_root=repo,
        task="Review selected changed file.",
        include_paths=("a.txt",),
    )

    assert "current a" in prompt
    assert "current b" not in prompt
    assert "Omitted changed tracked files:" in prompt
    assert "- b.txt" in prompt


def test_review_prompt_exclude_path_filters_changed_files(tmp_path: Path) -> None:
    repo = _init_git_repo(tmp_path)
    (repo / "keep.txt").write_text("base keep\n", encoding="utf-8")
    (repo / "skip.txt").write_text("base skip\n", encoding="utf-8")
    _git(repo, ["add", "keep.txt", "skip.txt"])
    _commit(repo, "initial")
    (repo / "keep.txt").write_text("current keep\n", encoding="utf-8")
    (repo / "skip.txt").write_text("current skip\n", encoding="utf-8")

    prompt = build_review_prompt.build_review_prompt(
        workspace_root=repo,
        task="Review selected changed files.",
        exclude_paths=("skip.txt",),
    )

    assert "current keep" in prompt
    assert "current skip" not in prompt
    assert "- skip.txt" in prompt


def test_review_prompt_truncates_large_file_context(tmp_path: Path) -> None:
    repo = _init_git_repo(tmp_path)
    (repo / "large.txt").write_text("0123456789\n", encoding="utf-8")
    _git(repo, ["add", "large.txt"])
    _commit(repo, "initial")
    (repo / "large.txt").write_text("x" * 40, encoding="utf-8")

    prompt = build_review_prompt.build_review_prompt(
        workspace_root=repo,
        task="Review changed files.",
        max_file_bytes=10,
    )

    assert "[truncated after 10 bytes;" in prompt


def test_review_prompt_redacts_tracked_and_diff_secrets(tmp_path: Path) -> None:
    repo = _init_git_repo(tmp_path)
    (repo / "config.txt").write_text(
        "api_key: sk-abcdefghijklmnopqrstuvwxyz\n",
        encoding="utf-8",
    )
    _git(repo, ["add", "config.txt"])
    _commit(repo, "initial")
    (repo / "config.txt").write_text(
        "api_key: sk-abcdefghijklmnopqrstuvwxyz\n"
        "deepseek_api_key=raw-secret-value\n"
        "Authorization: Bearer raw-token-value\n",
        encoding="utf-8",
    )

    prompt = build_review_prompt.build_review_prompt(
        workspace_root=repo,
        task="Check api_key=raw-secret-value and Authorization: Bearer task-token.",
    )

    assert "sk-abcdefghijklmnopqrstuvwxyz" not in prompt
    assert "raw-secret-value" not in prompt
    assert "raw-token-value" not in prompt
    assert "task-token" not in prompt
    assert "<redacted>" in prompt


def test_review_prompt_includes_staged_only_diff(tmp_path: Path) -> None:
    repo = _init_git_repo(tmp_path)
    (repo / "a.txt").write_text("base\n", encoding="utf-8")
    _git(repo, ["add", "a.txt"])
    _commit(repo, "initial")
    (repo / "a.txt").write_text("staged\n", encoding="utf-8")
    _git(repo, ["add", "a.txt"])
    (repo / "a.txt").write_text("base\n", encoding="utf-8")

    state = build_review_prompt.collect_git_review_state(repo)
    prompt = build_review_prompt.build_review_prompt(
        workspace_root=repo,
        task="Review staged changes.",
    )

    assert state.status_short.strip() == "MM a.txt"
    assert state.changed_files == ("a.txt",)
    assert "snapshot_ref" in prompt
    assert "index (staged)" in prompt
    assert "staged" in prompt


def test_review_prompt_omits_denied_changed_file_content(tmp_path: Path) -> None:
    repo = _init_git_repo(tmp_path)
    (repo / "safe.txt").write_text("safe base\n", encoding="utf-8")
    (repo / ".env.production").write_text(
        "LOCAL_PASSWORD=base-secret\n",
        encoding="utf-8",
    )
    _git(repo, ["add", "safe.txt", ".env.production"])
    _commit(repo, "initial")
    (repo / "safe.txt").write_text("safe current\n", encoding="utf-8")
    (repo / ".env.production").write_text(
        "LOCAL_PASSWORD=changed-secret\n",
        encoding="utf-8",
    )

    prompt = build_review_prompt.build_review_prompt(
        workspace_root=repo,
        task="Review changed files.",
    )

    assert "safe current" in prompt
    assert "changed-secret" not in prompt
    assert "- .env.production" in prompt


def test_review_prompt_full_scope_omits_denied_snapshot_content(
    tmp_path: Path,
) -> None:
    repo = _init_git_repo(tmp_path)
    (repo / "safe.txt").write_text("safe snapshot\n", encoding="utf-8")
    (repo / "providers.local.yaml").write_text(
        "local_password: snapshot-secret\n",
        encoding="utf-8",
    )
    _git(repo, ["add", "safe.txt", "providers.local.yaml"])
    _commit(repo, "initial")

    prompt = build_review_prompt.build_review_prompt(
        workspace_root=repo,
        task="Review full snapshot.",
        scope="full",
    )

    assert "safe snapshot" in prompt
    assert "snapshot-secret" not in prompt
    assert "### FILE: providers.local.yaml" not in prompt


def test_review_prompt_refuses_denied_context_file(tmp_path: Path) -> None:
    repo = _init_git_repo(tmp_path)
    (repo / ".env.production").write_text(
        "LOCAL_PASSWORD=context-secret\n",
        encoding="utf-8",
    )
    _git(repo, ["add", ".env.production"])
    _commit(repo, "initial")

    with pytest.raises(
        build_review_prompt.ReviewPromptError,
        match="context file is not safe",
    ):
        build_review_prompt.build_review_prompt(
            workspace_root=repo,
            task="Review with unsafe context.",
            context_files=(".env.production",),
        )


def test_review_prompt_omits_untracked_content_by_default(tmp_path: Path) -> None:
    repo = _init_git_repo(tmp_path)
    (repo / "tracked.txt").write_text("tracked\n", encoding="utf-8")
    _git(repo, ["add", "tracked.txt"])
    _commit(repo, "initial")
    (repo / "local_secret.txt").write_text("local-only-secret\n", encoding="utf-8")

    prompt = build_review_prompt.build_review_prompt(
        workspace_root=repo,
        task="Review.",
    )

    assert "local_secret.txt" not in prompt
    assert "local-only-secret" not in prompt
    assert "omitted_count: 1" in prompt


def test_review_prompt_requires_selected_untracked_paths(tmp_path: Path) -> None:
    repo = _init_git_repo(tmp_path)
    (repo / "tracked.txt").write_text("tracked\n", encoding="utf-8")
    _git(repo, ["add", "tracked.txt"])
    _commit(repo, "initial")
    (repo / "review_note.txt").write_text("local-only-context\n", encoding="utf-8")

    with pytest.raises(
        build_review_prompt.ReviewPromptError,
        match="requires at least one --include-untracked-path",
    ):
        build_review_prompt.build_review_prompt(
            workspace_root=repo,
            task="Review.",
            include_untracked_content=True,
        )


def test_review_prompt_includes_selected_untracked_content(tmp_path: Path) -> None:
    repo = _init_git_repo(tmp_path)
    (repo / "tracked.txt").write_text("tracked\n", encoding="utf-8")
    _git(repo, ["add", "tracked.txt"])
    _commit(repo, "initial")
    (repo / "review_note.txt").write_text("local-only-context\n", encoding="utf-8")
    (repo / "local_secret.txt").write_text("local-only-secret\n", encoding="utf-8")

    prompt = build_review_prompt.build_review_prompt(
        workspace_root=repo,
        task="Review.",
        include_untracked_content=True,
        include_untracked_paths=("review_note.txt",),
    )

    assert "### FILE: review_note.txt" in prompt
    assert "local-only-context" in prompt
    assert "local_secret.txt" not in prompt
    assert "local-only-secret" not in prompt


def test_review_prompt_refuses_selected_untracked_secret_path(tmp_path: Path) -> None:
    repo = _init_git_repo(tmp_path)
    (repo / "tracked.txt").write_text("tracked\n", encoding="utf-8")
    _git(repo, ["add", "tracked.txt"])
    _commit(repo, "initial")
    (repo / ".env.production").write_text(
        "Authorization: Bearer raw-token-value\n",
        encoding="utf-8",
    )

    with pytest.raises(
        build_review_prompt.ReviewPromptError,
        match="not safe for bulk inclusion",
    ):
        build_review_prompt.build_review_prompt(
            workspace_root=repo,
            task="Review.",
            include_untracked_content=True,
            include_untracked_paths=(".env.production",),
        )


def _init_git_repo(path: Path) -> Path:
    _git(path, ["init"])
    return path


def _commit(repo: Path, message: str) -> None:
    _git(
        repo,
        [
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.com",
            "commit",
            "-m",
            message,
        ],
    )


def _git(repo: Path, args: list[str]) -> None:
    _git_text(repo, args)


def _git_text(repo: Path, args: list[str]) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=True,
    )
    return result.stdout
