#!/usr/bin/env python3
"""Invoke OpenAI-compatible chat-completions providers for review tasks.

This tool is intentionally small and dependency-light so code-review can call
external reviewers such as DeepSeek without adding an SDK dependency. API keys
are read from environment variables or local provider config files and are
never written to request artifacts.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from redaction import redact_json

try:
    import yaml  # type: ignore[import-untyped]
except ImportError:
    yaml = None  # type: ignore[assignment]


class ModelApiError(RuntimeError):
    """External model API configuration or invocation failed."""


RETRYABLE_HTTP_STATUS_CODES = {429, 500, 502, 503, 504}


@dataclass(frozen=True)
class ProviderConfig:
    """Resolved OpenAI-compatible provider configuration."""

    name: str
    base_url: str
    api_key_env: str | None
    model: str
    api_key: str | None = field(default=None, repr=False)
    endpoint_path: str = "/chat/completions"
    timeout_sec: int = 120
    extra_body: dict[str, Any] = field(default_factory=dict)


BUILTIN_PROVIDERS: dict[str, dict[str, Any]] = {
    "deepseek": {
        "base_url": "https://api.deepseek.com",
        "api_key_env": "DEEPSEEK_API_KEY",
        "model_env": "DEEPSEEK_MODEL",
        "model": "deepseek-v4-pro",
        "endpoint_path": "/chat/completions",
        "timeout_sec": 120,
        "extra_body": {
            "thinking": {"type": "enabled"},
            "reasoning_effort": "max",
        },
    },
    "openai_compatible": {
        "base_url_env": "OPENAI_BASE_URL",
        "api_key_env": "OPENAI_API_KEY",
        "model_env": "OPENAI_MODEL",
        "model": "",
        "endpoint_path": "/chat/completions",
        "timeout_sec": 120,
    },
}

DEFAULT_CONFIG_CANDIDATES = (
    Path(__file__).resolve().with_name("providers.local.yaml"),
    Path(__file__).resolve().with_name("providers.example.yaml"),
)


def load_provider_config(
    provider: str,
    *,
    config_path: str | Path | None = None,
    env: dict[str, str] | None = None,
    model_override: str | None = None,
    base_url_override: str | None = None,
) -> ProviderConfig:
    """Resolve a provider from builtins, optional config file, and env."""
    environ = env if env is not None else os.environ
    configs = _load_config_file(config_path)
    merged = dict(BUILTIN_PROVIDERS.get(provider, {}))
    file_provider = configs.get(provider, {})
    if file_provider:
        merged.update(file_provider)
    if not merged:
        raise ModelApiError(f"Unknown provider {provider!r}")

    api_key = _optional_str(merged.get("api_key"))
    api_key_env = _optional_str(merged.get("api_key_env"))
    if not api_key and not api_key_env:
        raise ModelApiError(f"Provider {provider!r} needs api_key or api_key_env")

    base_url = _first_nonempty(
        base_url_override,
        file_provider.get("base_url"),
        _env_value(environ, file_provider.get("base_url_env")),
        _env_value(environ, merged.get("base_url_env")),
        merged.get("base_url"),
    )
    if not base_url:
        raise ModelApiError(
            f"Provider {provider!r} needs base_url or base_url_env"
        )

    model = _first_nonempty(
        model_override,
        file_provider.get("model"),
        _env_value(environ, file_provider.get("model_env")),
        _env_value(environ, merged.get("model_env")),
        merged.get("model"),
    )
    if not model:
        raise ModelApiError(
            f"Provider {provider!r} needs model, model_env, or --model"
        )

    endpoint_path = str(merged.get("endpoint_path") or "/chat/completions")
    timeout_sec = _positive_int(merged.get("timeout_sec"), default=120)
    extra_body = merged.get("extra_body") or {}
    if not isinstance(extra_body, dict):
        raise ModelApiError(f"Provider {provider!r} extra_body must be a mapping")

    return ProviderConfig(
        name=provider,
        base_url=str(base_url),
        api_key_env=api_key_env,
        model=str(model),
        api_key=api_key,
        endpoint_path=endpoint_path,
        timeout_sec=timeout_sec,
        extra_body=dict(extra_body),
    )


def build_chat_payload(
    provider: ProviderConfig,
    *,
    prompt: str,
    system_prompt: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
) -> dict[str, Any]:
    """Build an OpenAI-compatible chat-completions request body."""
    messages: list[dict[str, str]] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    payload: dict[str, Any] = {
        "model": provider.model,
        "messages": messages,
        "stream": False,
    }
    if temperature is not None:
        payload["temperature"] = temperature
    if max_tokens is not None:
        payload["max_tokens"] = max_tokens
    payload.update(provider.extra_body)
    return payload


def invoke_chat_completion(
    provider: ProviderConfig,
    *,
    api_key: str,
    payload: dict[str, Any],
    opener: Any = urllib.request.urlopen,
    max_attempts: int = 1,
    retry_delay_sec: float = 1.0,
    sleeper: Any = time.sleep,
) -> dict[str, Any]:
    """POST a chat-completions request and return decoded JSON."""
    if not api_key.strip():
        source = (
            f"environment variable {provider.api_key_env}"
            if provider.api_key_env
            else "provider config api_key"
        )
        raise ModelApiError(f"API key from {source} is empty")

    url = _join_url(provider.base_url, provider.endpoint_path)
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    attempts = _positive_int(max_attempts, default=1)
    used_attempts = 1
    for attempt in range(1, attempts + 1):
        used_attempts = attempt
        try:
            with opener(request, timeout=provider.timeout_sec) as response:
                raw = response.read().decode("utf-8", errors="replace")
            break
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            error = ModelApiError(f"HTTP {exc.code} from {provider.name}: {body}")
            retryable = exc.code in RETRYABLE_HTTP_STATUS_CODES
            cause: BaseException = exc
        except urllib.error.URLError as exc:
            error = ModelApiError(f"Request to {provider.name} failed: {exc}")
            retryable = True
            cause = exc
        if not retryable or attempt == attempts:
            raise error from cause
        if retry_delay_sec > 0:
            sleeper(retry_delay_sec)

    try:
        decoded = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ModelApiError(f"Provider {provider.name} returned invalid JSON") from exc
    if not isinstance(decoded, dict):
        raise ModelApiError(f"Provider {provider.name} returned non-object JSON")
    decoded["_harness_api_attempts"] = used_attempts
    return decoded


def extract_message_text(response: dict[str, Any]) -> str:
    """Extract assistant text from an OpenAI-compatible response."""
    choices = response.get("choices")
    if not isinstance(choices, list) or not choices:
        raise ModelApiError("Response does not contain choices")
    first = choices[0]
    if not isinstance(first, dict):
        raise ModelApiError("Response choice is not an object")
    message = first.get("message")
    if not isinstance(message, dict):
        raise ModelApiError("Response choice does not contain message")
    content = message.get("content")
    if isinstance(content, str) and content.strip():
        return content
    raise ModelApiError("Response message content is empty")


def write_request_artifact(
    path: Path,
    *,
    provider: ProviderConfig,
    payload: dict[str, Any],
) -> None:
    """Write a request artifact with secrets redacted."""
    artifact = {
        "provider": provider.name,
        "base_url": provider.base_url,
        "endpoint_path": provider.endpoint_path,
        "api_key_env": provider.api_key_env,
        "api_key_configured": provider.api_key is not None,
        "headers": {"Authorization": "Bearer <redacted>"},
        "body": redact_json(payload),
    }
    _atomic_write_json(path, artifact)


def write_meta_artifact(
    path: Path,
    *,
    provider: ProviderConfig,
    response: dict[str, Any],
) -> None:
    """Write non-secret response metadata."""
    meta = {
        "provider": provider.name,
        "model": provider.model,
        "base_url": provider.base_url,
        "id": response.get("id"),
        "created": response.get("created"),
        "api_attempts": response.get("_harness_api_attempts"),
        "usage": response.get("usage"),
        "cache": cache_usage_summary(response.get("usage")),
    }
    _atomic_write_json(path, meta)


def cache_usage_summary(usage: Any) -> dict[str, Any]:
    """Return derived DeepSeek/OpenAI-compatible input cache metrics."""
    if not isinstance(usage, dict):
        return {}
    hit = _nonnegative_int(usage.get("prompt_cache_hit_tokens"))
    miss = _nonnegative_int(usage.get("prompt_cache_miss_tokens"))
    if hit is None and miss is None:
        return {}

    hit_tokens = hit or 0
    miss_tokens = miss or 0
    total = hit_tokens + miss_tokens
    summary: dict[str, Any] = {
        "prompt_cache_hit_tokens": hit_tokens,
        "prompt_cache_miss_tokens": miss_tokens,
        "prompt_cache_total_tokens": total,
    }
    if total > 0:
        summary["prompt_cache_hit_rate"] = hit_tokens / total
        summary["prompt_cache_miss_rate"] = miss_tokens / total
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Call an external chat model")
    parser.add_argument("--provider", required=True, help="Provider name")
    parser.add_argument("--config", help="Provider config YAML/JSON")
    parser.add_argument("--prompt-file", required=True, help="User prompt file")
    parser.add_argument("--system-file", help="Optional system prompt file")
    parser.add_argument("--output", required=True, help="Write assistant text here")
    parser.add_argument("--request-json", help="Optional redacted request artifact")
    parser.add_argument("--meta-json", help="Optional response metadata artifact")
    parser.add_argument("--model", help="Override provider model")
    parser.add_argument("--base-url", help="Override provider base_url")
    parser.add_argument("--temperature", type=float)
    parser.add_argument("--max-tokens", type=int)
    parser.add_argument(
        "--api-retry-attempts",
        type=int,
        default=1,
        help="Maximum attempts for retryable provider HTTP/network failures.",
    )
    parser.add_argument(
        "--api-retry-delay-sec",
        type=float,
        default=1.0,
        help="Seconds to wait between retryable provider API attempts.",
    )
    args = parser.parse_args(argv)

    try:
        config_path = args.config or default_config_path()
        provider = load_provider_config(
            args.provider,
            config_path=config_path,
            model_override=args.model,
            base_url_override=args.base_url,
        )
        api_key = provider.api_key or os.environ.get(provider.api_key_env or "", "")
        prompt = Path(args.prompt_file).read_text(encoding="utf-8")
        system_prompt = (
            Path(args.system_file).read_text(encoding="utf-8")
            if args.system_file
            else None
        )
        payload = build_chat_payload(
            provider,
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=args.temperature,
            max_tokens=args.max_tokens,
        )
        if args.request_json:
            write_request_artifact(
                Path(args.request_json),
                provider=provider,
                payload=payload,
            )

        response = invoke_chat_completion(
            provider,
            api_key=api_key,
            payload=payload,
            max_attempts=args.api_retry_attempts,
            retry_delay_sec=args.api_retry_delay_sec,
        )
        text = extract_message_text(response)
        _atomic_write_text(Path(args.output), text.rstrip() + "\n")
        if args.meta_json:
            write_meta_artifact(
                Path(args.meta_json),
                provider=provider,
                response=response,
            )
    except ModelApiError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


def default_config_path() -> Path | None:
    for path in DEFAULT_CONFIG_CANDIDATES:
        if path.exists():
            if path.suffix.lower() in {".yaml", ".yml"} and yaml is None:
                continue
            return path
    return None


def _default_config_path() -> Path | None:
    return default_config_path()


def _load_config_file(config_path: str | Path | None) -> dict[str, dict[str, Any]]:
    if config_path is None:
        return {}
    path = Path(config_path)
    if not path.exists():
        raise ModelApiError(f"Provider config not found: {path}")
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        raw = json.loads(text)
    else:
        if yaml is None:
            raise ModelApiError("PyYAML is required to load YAML provider config")
        raw = yaml.safe_load(text)
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise ModelApiError("Provider config must be a mapping")
    providers = raw.get("providers", raw)
    if not isinstance(providers, dict):
        raise ModelApiError("Provider config providers must be a mapping")

    result: dict[str, dict[str, Any]] = {}
    for name, value in providers.items():
        if not isinstance(value, dict):
            raise ModelApiError(f"Provider {name!r} config must be a mapping")
        result[str(name)] = dict(value)
    return result


def _optional_str(value: Any) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    return value.strip()


def _env_value(environ: dict[str, str], key: Any) -> str | None:
    if not isinstance(key, str) or not key.strip():
        return None
    value = environ.get(key.strip())
    return value if value and value.strip() else None


def _first_nonempty(*values: Any) -> str | None:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _positive_int(value: Any, *, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default


def _nonnegative_int(value: Any) -> int | None:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed >= 0 else None


def _join_url(base_url: str, endpoint_path: str) -> str:
    return base_url.rstrip("/") + "/" + endpoint_path.lstrip("/")


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def _atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    tmp.replace(path)


if __name__ == "__main__":
    raise SystemExit(main())
