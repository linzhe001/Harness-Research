"""Tests for external OpenAI-compatible model API tooling."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
MODULE_PATH = REPO_ROOT / "tooling" / "model_api" / "external_chat.py"

spec = importlib.util.spec_from_file_location("external_chat", MODULE_PATH)
assert spec is not None
external_chat = importlib.util.module_from_spec(spec)
sys.modules["external_chat"] = external_chat
assert spec.loader is not None
spec.loader.exec_module(external_chat)


def test_deepseek_provider_defaults_to_v4_pro() -> None:
    provider = external_chat.load_provider_config("deepseek", env={})

    assert provider.name == "deepseek"
    assert provider.base_url == "https://api.deepseek.com"
    assert provider.api_key_env == "DEEPSEEK_API_KEY"
    assert provider.model == "deepseek-v4-pro"
    assert provider.extra_body["reasoning_effort"] == "high"


def test_custom_openai_compatible_provider_from_json(tmp_path: Path) -> None:
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


def test_unknown_provider_fails() -> None:
    with pytest.raises(external_chat.ModelApiError, match="Unknown provider"):
        external_chat.load_provider_config("missing", env={})
