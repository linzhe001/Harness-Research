#!/usr/bin/env python3
"""Run an agentic DeepSeek review with local read-only repository tools.

This script keeps external model calls OpenAI-compatible while giving the
reviewer a narrow local tool loop. The model can request repository reads, grep,
and git inspection, but every tool is executed locally with path, size, ignore,
and secret-redaction guardrails.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from external_chat import (
    ModelApiError,
    ProviderConfig,
    cache_usage_summary,
    default_config_path,
    invoke_chat_completion,
    load_provider_config,
)
from redaction import (
    DENIED_FILENAME_PATTERNS,
    DENIED_PATH_PARTS,
    DENIED_SUFFIXES,
    denied_review_path_reason,
    redact_secrets,
)


class AgenticReviewError(ModelApiError):
    """Agentic review configuration or execution failed."""


class AgenticReviewIncompleteError(AgenticReviewError):
    """Agentic review stopped before a final reviewer message was produced."""

    def __init__(
        self,
        message: str,
        *,
        trace: dict[str, Any],
        meta: dict[str, Any],
    ) -> None:
        super().__init__(message)
        self.trace = trace
        self.meta = meta


DEFAULT_MAX_ITERATIONS = 12
DEFAULT_MAX_TOOL_CALLS = 40
DEFAULT_FORCE_FINAL_AFTER_TOOL_CALLS = 40
DEFAULT_MAX_TOOL_RESULT_BYTES = 80_000
DEFAULT_MAX_TOTAL_TOOL_BYTES = 800_000
DEFAULT_MAX_SEARCH_RESULTS = 80
DEFAULT_TOOL_TIMEOUT_SEC = 30
DEFAULT_MAX_OUTPUT_TOKENS = 4096
DEFAULT_THINKING_SCOPE = "all"
DEFAULT_CACHE_RETRY_MISS_RATE = 0.8
DEFAULT_CACHE_RETRY_DELAY_SEC = 5.0
DEFAULT_CACHE_RETRY_SCOPE = "final"
DEFAULT_API_RETRY_ATTEMPTS = 3
DEFAULT_API_RETRY_DELAY_SEC = 2.0
THINKING_EXTRA_BODY_KEYS = {"thinking", "reasoning_effort"}
THINKING_SCOPES = {"all", "final", "none"}
CACHE_RETRY_SCOPES = {"all", "final"}
SEARCH_LINE_RE = re.compile(r"^(.+):\d+:")
PSEUDO_TOOL_CALL_MARKERS = (
    "<｜｜DSML｜｜tool_calls>",
    "<｜｜DSML｜｜invoke",
    "<|tool_calls|>",
    "<tool_calls>",
    "<tool_call>",
)


@dataclass
class AgenticReviewLimits:
    """Resource limits for a single local tool-loop review."""

    max_iterations: int = DEFAULT_MAX_ITERATIONS
    max_tool_calls: int = DEFAULT_MAX_TOOL_CALLS
    force_final_after_tool_calls: int = DEFAULT_FORCE_FINAL_AFTER_TOOL_CALLS
    max_tool_result_bytes: int = DEFAULT_MAX_TOOL_RESULT_BYTES
    max_total_tool_bytes: int = DEFAULT_MAX_TOTAL_TOOL_BYTES
    max_search_results: int = DEFAULT_MAX_SEARCH_RESULTS
    tool_timeout_sec: int = DEFAULT_TOOL_TIMEOUT_SEC


@dataclass
class ToolRuntime:
    """Mutable accounting for local tool execution."""

    root: Path
    limits: AgenticReviewLimits
    allow_untracked_paths: tuple[str, ...] = ()
    tool_calls: int = 0
    final_rejected_tool_calls: int = 0
    total_tool_bytes: int = 0
    events: list[dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True)
class AgenticReviewResult:
    """Final result and trace from an agentic reviewer run."""

    text: str
    messages: list[dict[str, Any]]
    trace: dict[str, Any]
    meta: dict[str, Any]


def run_agentic_review(
    provider: ProviderConfig,
    *,
    api_key: str,
    workspace_root: Path,
    task: str,
    system_prompt: str | None = None,
    limits: AgenticReviewLimits | None = None,
    max_tokens: int | None = DEFAULT_MAX_OUTPUT_TOKENS,
    temperature: float | None = None,
    thinking_scope: str = DEFAULT_THINKING_SCOPE,
    cache_retry_miss_rate: float | None = DEFAULT_CACHE_RETRY_MISS_RATE,
    cache_retry_delay_sec: float = DEFAULT_CACHE_RETRY_DELAY_SEC,
    cache_retry_scope: str = DEFAULT_CACHE_RETRY_SCOPE,
    api_retry_attempts: int = DEFAULT_API_RETRY_ATTEMPTS,
    api_retry_delay_sec: float = DEFAULT_API_RETRY_DELAY_SEC,
    allow_untracked_paths: tuple[str, ...] = (),
    sleeper: Any = time.sleep,
    opener: Any = urllib.request.urlopen,
) -> AgenticReviewResult:
    """Run DeepSeek/OpenAI-compatible tool-calling review until final text."""
    root = _resolve_workspace_root(workspace_root)
    selected_thinking_scope = _validate_thinking_scope(thinking_scope)
    selected_cache_retry_scope = _validate_cache_retry_scope(cache_retry_scope)
    selected_limits = _validate_limits(limits or AgenticReviewLimits())
    allowed_untracked = _normalize_allow_untracked_paths(allow_untracked_paths)
    runtime = ToolRuntime(
        root=root,
        limits=selected_limits,
        allow_untracked_paths=allowed_untracked,
    )
    messages: list[dict[str, Any]] = [
        {
            "role": "system",
            "content": (
                system_prompt
                or build_agentic_system_prompt(provider_name=provider.name)
            ),
        },
        {
            "role": "user",
            "content": build_initial_user_prompt(
                root,
                task,
                allow_untracked_paths=allowed_untracked,
            ),
        },
    ]
    response_summaries: list[dict[str, Any]] = []
    final_notice_added = False
    final_retry_after_rejected_tools_used = False
    final_retry_after_invalid_content_used = False
    cache_retry_used = False

    for iteration in range(1, selected_limits.max_iterations + 1):
        force_final = (
            iteration == selected_limits.max_iterations
            or runtime.tool_calls >= selected_limits.force_final_after_tool_calls
        )
        if force_final and not final_notice_added:
            messages.append({
                "role": "user",
                "content": (
                    "Stop using tools now. Produce the final review from the "
                    "evidence already gathered. If evidence is insufficient, "
                    "state that as an open question. Do not emit XML, DSML, "
                    "or tool-call markup; the final answer must be Markdown "
                    "review text."
                ),
            })
            final_notice_added = True
        payload = build_agentic_payload(
            provider,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            tool_choice="none" if force_final else "auto",
            thinking_scope=selected_thinking_scope,
            final_request=force_final,
        )
        payload_fingerprint = fingerprint_payload(payload)
        response = invoke_chat_completion(
            provider,
            api_key=api_key,
            payload=payload,
            opener=opener,
            max_attempts=api_retry_attempts,
            retry_delay_sec=api_retry_delay_sec,
            sleeper=sleeper,
        )
        summary = _response_summary(
            response,
            iteration,
            payload_fingerprint=payload_fingerprint,
            cache_retry=False,
            force_final=force_final,
        )
        if (
            _cache_retry_allowed(selected_cache_retry_scope, force_final)
            and not cache_retry_used
            and cache_retry_delay_sec > 0
            and _should_retry_cache_miss(summary, cache_retry_miss_rate)
        ):
            cache_retry_used = True
            summary["cache_retry_retried"] = True
            response_summaries.append(summary)
            sleeper(cache_retry_delay_sec)
            response = invoke_chat_completion(
                provider,
                api_key=api_key,
                payload=payload,
                opener=opener,
                max_attempts=api_retry_attempts,
                retry_delay_sec=api_retry_delay_sec,
                sleeper=sleeper,
            )
            summary = _response_summary(
                response,
                iteration,
                payload_fingerprint=payload_fingerprint,
                cache_retry=True,
                force_final=force_final,
            )
        response_summaries.append(summary)
        message = _extract_response_message(response)
        messages.append(message)
        tool_calls = _message_tool_calls(message)
        if not tool_calls:
            text = _message_content(message)
            if not text:
                raise AgenticReviewError("Final reviewer message content is empty")
            invalid_reason = _invalid_final_response_reason(text)
            if invalid_reason:
                if not final_retry_after_invalid_content_used:
                    final_retry_after_invalid_content_used = True
                    return _retry_after_invalid_final_content(
                        provider=provider,
                        api_key=api_key,
                        messages=messages,
                        runtime=runtime,
                        response_summaries=response_summaries,
                        invalid_reason=invalid_reason,
                        iteration=iteration,
                        max_tokens=max_tokens,
                        temperature=temperature,
                        thinking_scope=selected_thinking_scope,
                        cache_retry_scope=selected_cache_retry_scope,
                        cache_retry_used=cache_retry_used,
                        api_retry_attempts=api_retry_attempts,
                        api_retry_delay_sec=api_retry_delay_sec,
                        sleeper=sleeper,
                        opener=opener,
                    )
                _raise_invalid_final_response(
                    provider=provider,
                    messages=messages,
                    runtime=runtime,
                    response_summaries=response_summaries,
                    reason=invalid_reason,
                    thinking_scope=selected_thinking_scope,
                    cache_retry_scope=selected_cache_retry_scope,
                    cache_retry_used=cache_retry_used,
                )
            return _completed_review_result(
                provider=provider,
                messages=messages,
                runtime=runtime,
                response_summaries=response_summaries,
                text=text,
                thinking_scope=selected_thinking_scope,
                cache_retry_scope=selected_cache_retry_scope,
                cache_retry_used=cache_retry_used,
            )

        if force_final:
            for tool_call in tool_calls:
                tool_message = reject_final_tool_call(runtime, tool_call)
                messages.append(tool_message)
            if not final_retry_after_rejected_tools_used:
                final_retry_after_rejected_tools_used = True
                messages.append({
                    "role": "user",
                    "content": (
                        "The requested tools were rejected. Produce the final "
                        "review now with no tool calls."
                    ),
                })
                payload = build_agentic_payload(
                    provider,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    tool_choice="none",
                    thinking_scope=selected_thinking_scope,
                    final_request=True,
                )
                payload_fingerprint = fingerprint_payload(payload)
                response = invoke_chat_completion(
                    provider,
                    api_key=api_key,
                    payload=payload,
                    opener=opener,
                    max_attempts=api_retry_attempts,
                    retry_delay_sec=api_retry_delay_sec,
                    sleeper=sleeper,
                )
                summary = _response_summary(
                    response,
                    iteration + 1,
                    payload_fingerprint=payload_fingerprint,
                    cache_retry=False,
                    force_final=True,
                )
                summary["final_retry_after_rejected_tools"] = True
                response_summaries.append(summary)
                message = _extract_response_message(response)
                messages.append(message)
                tool_calls = _message_tool_calls(message)
                if not tool_calls:
                    text = _message_content(message)
                    if not text:
                        raise AgenticReviewError(
                            "Final reviewer message content is empty"
                        )
                    invalid_reason = _invalid_final_response_reason(text)
                    if invalid_reason:
                        _raise_invalid_final_response(
                            provider=provider,
                            messages=messages,
                            runtime=runtime,
                            response_summaries=response_summaries,
                            reason=invalid_reason,
                            thinking_scope=selected_thinking_scope,
                            cache_retry_scope=selected_cache_retry_scope,
                            cache_retry_used=cache_retry_used,
                        )
                    return _completed_review_result(
                        provider=provider,
                        messages=messages,
                        runtime=runtime,
                        response_summaries=response_summaries,
                        text=text,
                        thinking_scope=selected_thinking_scope,
                        cache_retry_scope=selected_cache_retry_scope,
                        cache_retry_used=cache_retry_used,
                    )
                for tool_call in tool_calls:
                    tool_message = reject_final_tool_call(runtime, tool_call)
                    messages.append(tool_message)
                _raise_rejected_final_tool_calls(
                    provider=provider,
                    messages=messages,
                    runtime=runtime,
                    response_summaries=response_summaries,
                    thinking_scope=selected_thinking_scope,
                    cache_retry_scope=selected_cache_retry_scope,
                    cache_retry_used=cache_retry_used,
                )
            _raise_rejected_final_tool_calls(
                provider=provider,
                messages=messages,
                runtime=runtime,
                response_summaries=response_summaries,
                thinking_scope=selected_thinking_scope,
                cache_retry_scope=selected_cache_retry_scope,
                cache_retry_used=cache_retry_used,
            )
            continue

        for tool_call in tool_calls:
            tool_message = execute_tool_call(runtime, tool_call)
            messages.append(tool_message)

    trace = build_trace(
        provider=provider,
        messages=messages,
        runtime=runtime,
        response_summaries=response_summaries,
        status="max_iterations_exceeded",
        thinking_scope=selected_thinking_scope,
        cache_retry_scope=selected_cache_retry_scope,
    )
    raise AgenticReviewIncompleteError(
        "Agentic review exceeded max iterations; "
        f"trace has {len(trace['tool_events'])} tool events",
        trace=trace,
        meta=build_meta(
            provider,
            runtime,
            response_summaries,
            thinking_scope=selected_thinking_scope,
            cache_retry_scope=selected_cache_retry_scope,
            cache_retry_used=cache_retry_used,
        ),
    )


def _completed_review_result(
    *,
    provider: ProviderConfig,
    messages: list[dict[str, Any]],
    runtime: ToolRuntime,
    response_summaries: list[dict[str, Any]],
    text: str,
    thinking_scope: str,
    cache_retry_scope: str,
    cache_retry_used: bool,
) -> AgenticReviewResult:
    trace = build_trace(
        provider=provider,
        messages=messages,
        runtime=runtime,
        response_summaries=response_summaries,
        status="completed",
        thinking_scope=thinking_scope,
        cache_retry_scope=cache_retry_scope,
    )
    return AgenticReviewResult(
        text=text.rstrip() + "\n",
        messages=messages,
        trace=trace,
        meta=build_meta(
            provider,
            runtime,
            response_summaries,
            thinking_scope=thinking_scope,
            cache_retry_scope=cache_retry_scope,
            cache_retry_used=cache_retry_used,
        ),
    )


def _retry_after_invalid_final_content(
    *,
    provider: ProviderConfig,
    api_key: str,
    messages: list[dict[str, Any]],
    runtime: ToolRuntime,
    response_summaries: list[dict[str, Any]],
    invalid_reason: str,
    iteration: int,
    max_tokens: int | None,
    temperature: float | None,
    thinking_scope: str,
    cache_retry_scope: str,
    cache_retry_used: bool,
    api_retry_attempts: int,
    api_retry_delay_sec: float,
    sleeper: Any,
    opener: Any,
) -> AgenticReviewResult:
    messages.append({
        "role": "user",
        "content": (
            "The previous answer was not a usable final review because "
            f"{invalid_reason}. Produce the final review now as Markdown text "
            "only. Do not include XML, DSML, JSON tool calls, or tool-call "
            "tags. If the evidence is insufficient, state that plainly."
        ),
    })
    payload = build_agentic_payload(
        provider,
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
        tool_choice="none",
        thinking_scope=thinking_scope,
        final_request=True,
    )
    payload_fingerprint = fingerprint_payload(payload)
    response = invoke_chat_completion(
        provider,
        api_key=api_key,
        payload=payload,
        opener=opener,
        max_attempts=api_retry_attempts,
        retry_delay_sec=api_retry_delay_sec,
        sleeper=sleeper,
    )
    summary = _response_summary(
        response,
        iteration + 1,
        payload_fingerprint=payload_fingerprint,
        cache_retry=False,
        force_final=True,
    )
    summary["final_retry_after_invalid_content"] = True
    response_summaries.append(summary)
    message = _extract_response_message(response)
    messages.append(message)
    tool_calls = _message_tool_calls(message)
    if tool_calls:
        for tool_call in tool_calls:
            tool_message = reject_final_tool_call(runtime, tool_call)
            messages.append(tool_message)
        _raise_rejected_final_tool_calls(
            provider=provider,
            messages=messages,
            runtime=runtime,
            response_summaries=response_summaries,
            thinking_scope=thinking_scope,
            cache_retry_scope=cache_retry_scope,
            cache_retry_used=cache_retry_used,
        )

    text = _message_content(message)
    if not text:
        raise AgenticReviewError("Final reviewer message content is empty")
    retry_invalid_reason = _invalid_final_response_reason(text)
    if retry_invalid_reason:
        _raise_invalid_final_response(
            provider=provider,
            messages=messages,
            runtime=runtime,
            response_summaries=response_summaries,
            reason=retry_invalid_reason,
            thinking_scope=thinking_scope,
            cache_retry_scope=cache_retry_scope,
            cache_retry_used=cache_retry_used,
        )
    return _completed_review_result(
        provider=provider,
        messages=messages,
        runtime=runtime,
        response_summaries=response_summaries,
        text=text,
        thinking_scope=thinking_scope,
        cache_retry_scope=cache_retry_scope,
        cache_retry_used=cache_retry_used,
    )


def _raise_invalid_final_response(
    *,
    provider: ProviderConfig,
    messages: list[dict[str, Any]],
    runtime: ToolRuntime,
    response_summaries: list[dict[str, Any]],
    reason: str,
    thinking_scope: str,
    cache_retry_scope: str,
    cache_retry_used: bool,
) -> None:
    trace = build_trace(
        provider=provider,
        messages=messages,
        runtime=runtime,
        response_summaries=response_summaries,
        status="invalid_final_response",
        thinking_scope=thinking_scope,
        cache_retry_scope=cache_retry_scope,
    )
    meta = build_meta(
        provider,
        runtime,
        response_summaries,
        thinking_scope=thinking_scope,
        cache_retry_scope=cache_retry_scope,
        cache_retry_used=cache_retry_used,
    )
    meta["failure_reason"] = reason
    raise AgenticReviewIncompleteError(
        f"Agentic review final response was invalid: {reason}",
        trace=trace,
        meta=meta,
    )


def _raise_rejected_final_tool_calls(
    *,
    provider: ProviderConfig,
    messages: list[dict[str, Any]],
    runtime: ToolRuntime,
    response_summaries: list[dict[str, Any]],
    thinking_scope: str,
    cache_retry_scope: str,
    cache_retry_used: bool,
) -> None:
    trace = build_trace(
        provider=provider,
        messages=messages,
        runtime=runtime,
        response_summaries=response_summaries,
        status="final_tool_calls_rejected",
        thinking_scope=thinking_scope,
        cache_retry_scope=cache_retry_scope,
    )
    raise AgenticReviewIncompleteError(
        "Agentic review requested tools after final synthesis was forced",
        trace=trace,
        meta=build_meta(
            provider,
            runtime,
            response_summaries,
            thinking_scope=thinking_scope,
            cache_retry_scope=cache_retry_scope,
            cache_retry_used=cache_retry_used,
        ),
    )


def build_agentic_payload(
    provider: ProviderConfig,
    *,
    messages: list[dict[str, Any]],
    max_tokens: int | None,
    temperature: float | None,
    tool_choice: str = "auto",
    thinking_scope: str = DEFAULT_THINKING_SCOPE,
    final_request: bool = False,
) -> dict[str, Any]:
    """Build an OpenAI-compatible tool-calling payload."""
    selected_thinking_scope = _validate_thinking_scope(thinking_scope)
    payload: dict[str, Any] = {
        "model": provider.model,
        "messages": messages,
        "stream": False,
    }
    if tool_choice != "none":
        payload["tools"] = AGENTIC_TOOLS
        payload["tool_choice"] = tool_choice
    if max_tokens is not None:
        payload["max_tokens"] = max_tokens
    if temperature is not None:
        payload["temperature"] = temperature
    payload.update(_scoped_extra_body(
        provider.extra_body,
        thinking_scope=selected_thinking_scope,
        final_request=final_request,
    ))
    return payload


def _scoped_extra_body(
    extra_body: dict[str, Any],
    *,
    thinking_scope: str,
    final_request: bool,
) -> dict[str, Any]:
    """Return provider extra_body with thinking keys scoped for cost control."""
    selected_thinking_scope = _validate_thinking_scope(thinking_scope)
    if selected_thinking_scope == "all":
        return dict(extra_body)
    include_thinking = selected_thinking_scope == "final" and final_request
    if include_thinking:
        return dict(extra_body)
    return {
        key: value
        for key, value in extra_body.items()
        if key not in THINKING_EXTRA_BODY_KEYS
    }


def _validate_thinking_scope(value: str) -> str:
    selected = value.strip().lower()
    if selected not in THINKING_SCOPES:
        raise AgenticReviewError(
            "thinking_scope must be one of: " + ", ".join(sorted(THINKING_SCOPES))
        )
    return selected


def _validate_cache_retry_scope(value: str) -> str:
    selected = value.strip().lower()
    if selected not in CACHE_RETRY_SCOPES:
        raise AgenticReviewError(
            "cache_retry_scope must be one of: "
            + ", ".join(sorted(CACHE_RETRY_SCOPES))
        )
    return selected


def _validate_limits(limits: AgenticReviewLimits) -> AgenticReviewLimits:
    if limits.max_iterations <= 0:
        raise AgenticReviewError("max_iterations must be positive")
    if limits.max_tool_calls <= 0:
        raise AgenticReviewError("max_tool_calls must be positive")
    if limits.force_final_after_tool_calls <= 0:
        raise AgenticReviewError("force_final_after_tool_calls must be positive")
    if limits.force_final_after_tool_calls > limits.max_tool_calls:
        raise AgenticReviewError(
            "force_final_after_tool_calls must be <= max_tool_calls"
        )
    return limits


def resolve_force_final_after_tool_calls(
    *,
    max_tool_calls: int,
    requested: int | None,
) -> int:
    if requested is not None:
        return requested
    return min(DEFAULT_FORCE_FINAL_AFTER_TOOL_CALLS, max_tool_calls)


def _cache_retry_allowed(cache_retry_scope: str, force_final: bool) -> bool:
    return cache_retry_scope == "all" or force_final


def fingerprint_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Return non-secret hashes for cache-prefix diagnostics."""
    redacted = redact_json(payload)
    messages = redacted.get("messages") if isinstance(redacted, dict) else []
    tools = redacted.get("tools") if isinstance(redacted, dict) else []
    message_count = len(messages) if isinstance(messages, list) else 0
    last_role = None
    if isinstance(messages, list) and messages:
        last_message = messages[-1]
        if isinstance(last_message, dict):
            last_role = last_message.get("role")
    thinking_keys = sorted(
        key for key in THINKING_EXTRA_BODY_KEYS if key in payload
    )
    return {
        "payload_sha256": _hash_json(redacted),
        "messages_sha256": _hash_json(messages),
        "tools_sha256": _hash_json(tools),
        "tool_choice": payload.get("tool_choice"),
        "message_count": message_count,
        "last_message_role": last_role,
        "thinking_keys": thinking_keys,
    }


def build_agentic_system_prompt(provider_name: str = "external model") -> str:
    """Return durable reviewer instructions and workflow hints."""
    reviewer_name = provider_name.strip() or "external model"
    return f"""You are {reviewer_name}, an external agentic repository reviewer.

You do not have direct filesystem access. Use the provided local read-only tools
to inspect this workspace. Prefer evidence from tool outputs over assumptions.
Do not request edits; this is review-only.

Harness Research workflow rules to respect:
- Framework facts come from repository files, tests, schemas, commands, and
  review/gate artifacts, not from memory alone.
- For code review, prioritize concrete bugs, regressions, unsafe workflow
  assumptions, and missing tests. Use file/line evidence when possible.
- Simple review should stay targeted. For deeper review, inspect files yourself
  with tools instead of asking for a full repository prompt.
- Skill routing: code-review is read-only; fixes route through code-debug.
- Hook model:
  UserPromptSubmit -> detect active skill -> write .harness_hooks/session.json
  PreToolUse       -> block missing reads or forbidden writes
  PostToolUse      -> record read/write markers and pending Gate ledger state
  Stop             -> block missing read set or missing Gate ledger
- Core workflow:
  WF1 survey -> WF2 idea-debate -> WF3 refine-idea -> WF4 data
  -> WF5 baseline -> WF6 arch -> WF7 plan -> WF8 code
  -> WF9 validate -> WF10 iterate -> WF11 final-exp -> WF12 release
- WF10 loop:
  iterate plan -> iterate code -> iterate run -> iterate eval
  -> NEXT_ROUND | DEBUG | CONTINUE | PIVOT | ABORT

Recommended review behavior:
1. Start with git_status and workflow_hints when workflow, hooks, or skills are
   in scope.
2. Use list_files/search_text to locate relevant code, tests, skills, and docs.
3. Use read_file/git_diff/git_show for line-level evidence.
4. Keep tool calls purposeful; do not bulk-read the repository.
5. If context is missing or access is denied, report an open question instead of
   inventing a fact.
6. If the caller says to stop using tools, produce the final review immediately.

Final answer format:
- Findings first, ordered by severity.
- Each finding should include path/line evidence or a clear reason it remains an
  open question.
- Include rejected or uncertain suspicions separately.
- Include a concise workflow impact summary and suggested next checks.
"""


def build_initial_user_prompt(
    root: Path,
    task: str,
    *,
    allow_untracked_paths: tuple[str, ...] = (),
) -> str:
    """Build small initial task context without packaging repository content."""
    status, untracked_omitted = _filter_status_short_for_external(
        _git_text(root, ["status", "--short"]),
        allow_untracked_paths=allow_untracked_paths,
    )
    status = status or "[clean]"
    branch = _git_text(root, ["branch", "--show-current"]).strip() or "[detached]"
    head = _git_text(root, ["rev-parse", "--short", "HEAD"]).strip()
    changed = "\n".join(_changed_paths_from_ref(root, "HEAD")) or "[none]"
    return "\n".join([
        "Run an agentic external review of this Harness Research workspace.",
        "",
        "Use local tools to inspect files as needed. Do not assume omitted files.",
        "",
        f"workspace_root: {root}",
        f"branch: {branch}",
        f"head_short: {head}",
        "",
        "git_status_short:",
        "```text",
        redact_secrets(status.rstrip()),
        "```",
        f"untracked_omitted: {untracked_omitted}",
        "",
        "changed_tracked_files_from_HEAD:",
        "```text",
        redact_secrets(changed.rstrip()),
        "```",
        "",
        "operator_task:",
        redact_secrets(
            task.strip() or "Review the current workflow and changed files."
        ),
    ])


AGENTIC_TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "workflow_hints",
            "description": "Return Harness workflow, skill-routing, and review hints.",
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "enum": [
                            "all",
                            "code_review",
                            "hooks",
                            "auto_iterate",
                            "workflow",
                        ],
                        "description": "Hint subset to return.",
                    }
                },
                "required": ["topic"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "git_status",
            "description": (
                "Return git status, current branch, HEAD, and changed files."
            ),
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": (
                "List tracked repository files and optional untracked files."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path_prefix": {
                        "type": "string",
                        "description": "Optional relative file or directory prefix.",
                    },
                    "include_untracked": {
                        "type": "boolean",
                        "description": "Include untracked non-ignored files.",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum paths to return.",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_text",
            "description": "Search repository text with ripgrep.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "Regex pattern."},
                    "path_prefix": {
                        "type": "string",
                        "description": "Optional relative file or directory prefix.",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum matching lines to return.",
                    },
                },
                "required": ["pattern"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a text file with line numbers and byte limits.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative file path."},
                    "start_line": {
                        "type": "integer",
                        "description": "1-based start line. Defaults to 1.",
                    },
                    "max_lines": {
                        "type": "integer",
                        "description": "Maximum lines. Defaults to 200.",
                    },
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "git_diff",
            "description": "Return git diff for all or selected paths.",
            "parameters": {
                "type": "object",
                "properties": {
                    "base_ref": {
                        "type": "string",
                        "description": "Base ref. Defaults to HEAD.",
                    },
                    "path_prefix": {
                        "type": "string",
                        "description": "Optional relative file or directory prefix.",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "git_show",
            "description": "Read a file from a git ref, such as HEAD:path.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ref": {
                        "type": "string",
                        "description": "Git ref. Defaults to HEAD.",
                    },
                    "path": {"type": "string", "description": "Relative file path."},
                },
                "required": ["path"],
            },
        },
    },
]


def execute_tool_call(
    runtime: ToolRuntime,
    tool_call: dict[str, Any],
) -> dict[str, Any]:
    """Execute one model-requested tool call and return a tool message."""
    if runtime.tool_calls >= runtime.limits.max_tool_calls:
        result = _tool_error("tool call limit exceeded")
    else:
        runtime.tool_calls += 1
        try:
            name, arguments = _parse_tool_call(tool_call)
            result = run_local_tool(runtime, name, arguments)
        except AgenticReviewError as exc:
            result = _tool_error(str(exc))
        except Exception as exc:  # Defensive boundary: report tool failure to model.
            result = _tool_error(f"unexpected local tool error: {exc}")
    content = json.dumps(result, ensure_ascii=False)
    tool_call_id = str(tool_call.get("id") or f"tool_{runtime.tool_calls}")
    return {"role": "tool", "tool_call_id": tool_call_id, "content": content}


def reject_final_tool_call(
    runtime: ToolRuntime,
    tool_call: dict[str, Any],
) -> dict[str, Any]:
    """Reject model-requested tools after final synthesis has been requested."""
    runtime.final_rejected_tool_calls += 1
    try:
        name, arguments = _parse_tool_call(tool_call)
    except AgenticReviewError:
        name, arguments = "unknown", {}
    result = _tool_error(
        "tool call rejected: final synthesis was requested; produce the "
        "review from already gathered evidence without more tools"
    )
    content = json.dumps(result, ensure_ascii=False)
    runtime.events.append({
        "tool": name,
        "arguments": redact_json(arguments),
        "ok": False,
        "rejected": "force_final",
        "bytes": len(content.encode()),
    })
    tool_call_id = str(
        tool_call.get("id") or f"final_rejected_{runtime.final_rejected_tool_calls}"
    )
    return {"role": "tool", "tool_call_id": tool_call_id, "content": content}


def run_local_tool(
    runtime: ToolRuntime,
    name: str,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    """Run a named local read-only tool."""
    if name == "workflow_hints":
        result = workflow_hints(str(arguments.get("topic") or "all"))
    elif name == "git_status":
        result = tool_git_status(runtime.root, runtime.allow_untracked_paths)
    elif name == "list_files":
        result = tool_list_files(
            runtime.root,
            runtime.limits,
            runtime.allow_untracked_paths,
            arguments,
        )
    elif name == "search_text":
        result = tool_search_text(runtime.root, runtime.limits, arguments)
    elif name == "read_file":
        result = tool_read_file(
            runtime.root,
            runtime.limits,
            runtime.allow_untracked_paths,
            arguments,
        )
    elif name == "git_diff":
        result = tool_git_diff(runtime.root, runtime.limits, arguments)
    elif name == "git_show":
        result = tool_git_show(runtime.root, runtime.limits, arguments)
    else:
        result = _tool_error(f"unknown tool: {name}")

    limited = _limit_tool_result(result, runtime.limits.max_tool_result_bytes)
    runtime.total_tool_bytes += len(json.dumps(limited, ensure_ascii=False).encode())
    if runtime.total_tool_bytes > runtime.limits.max_total_tool_bytes:
        raise AgenticReviewError("total tool result byte limit exceeded")
    runtime.events.append({
        "tool": name,
        "arguments": redact_json(arguments),
        "ok": bool(limited.get("ok")),
        "bytes": len(json.dumps(limited, ensure_ascii=False).encode()),
    })
    return limited


def workflow_hints(topic: str) -> dict[str, Any]:
    """Return compact Harness workflow hints for DeepSeek."""
    hints = {
        "code_review": [
            "Use code-review for read-only checks; do not edit subject files.",
            "Findings require file/line evidence and verification against disk.",
            "Route fixes through code-debug after review.",
            "For medium/heavy review, save traces under "
            ".agents/state/review_traces/code-review/.",
        ],
        "hooks": [
            "Hook files are runtime guardrails, not proof that a gate passed.",
            "Hook model: UserPromptSubmit, PreToolUse, PostToolUse, Stop.",
            "When changing hooks/contracts, inspect tooling/codex_hooks/README.md, "
            "schemas/skill_contracts.json, and "
            "tooling/.tests/test_codex_hooks_contracts.py.",
            "Gate ledger is required for sensitive workflow files before finalizing.",
        ],
        "auto_iterate": [
            "WF10 controller assists repeatable iterate loops without replacing "
            "human approval.",
            "Read .agents/skills/iterate/SKILL.md, auto-iterate-goal, and "
            "auto_iterate docs for controller changes.",
            "Failed phases recover from state/logs; never invent a successful "
            "phase result.",
        ],
        "workflow": [
            "Canonical workflow: WF1 survey through WF12 release.",
            "Human approval is required for claim boundaries, contract acceptance, "
            "high-risk transitions, and release decisions.",
            "Evidence comes from commands, tests, review packets, gate ledgers, "
            "and approval artifacts.",
        ],
    }
    selected = hints if topic == "all" else {topic: hints.get(topic, [])}
    return {"ok": True, "topic": topic, "hints": selected}


def tool_git_status(
    root: Path,
    allow_untracked_paths: tuple[str, ...] = (),
) -> dict[str, Any]:
    """Return compact git state."""
    head = _git_text(root, ["rev-parse", "HEAD"]).strip()
    status_short, untracked_omitted = _filter_status_short_for_external(
        _git_text(root, ["status", "--short"]),
        allow_untracked_paths=allow_untracked_paths,
    )
    return {
        "ok": True,
        "branch": _git_text(root, ["branch", "--show-current"]).strip(),
        "head": head,
        "status_short": redact_secrets(status_short),
        "changed_files": _changed_paths_from_ref(root, head),
        "staged_changed_files": _split_lines(
            _git_text(root, ["diff", "--cached", "--name-only", head, "--"])
        ),
        "unstaged_changed_files": _split_lines(
            _git_text(root, ["diff", "--name-only", "--"])
        ),
        "untracked_files": _allowed_existing_untracked_paths(
            root,
            allow_untracked_paths,
        ),
        "untracked_omitted": untracked_omitted,
    }


def tool_list_files(
    root: Path,
    limits: AgenticReviewLimits,
    allow_untracked_paths: tuple[str, ...],
    arguments: dict[str, Any],
) -> dict[str, Any]:
    """List tracked and optional untracked files."""
    path_prefix = _optional_path_filter(arguments.get("path_prefix"))
    max_results = _positive_int(
        arguments.get("max_results"),
        default=limits.max_search_results,
        upper=limits.max_search_results,
    )
    files = _git_z(root, ["ls-files", "-z"])
    if bool(arguments.get("include_untracked")):
        files.extend(_allowed_existing_untracked_paths(root, allow_untracked_paths))
    selected = sorted(
        path
        for path in files
        if not path_prefix or _path_matches_filter(path, path_prefix)
    )
    return {
        "ok": True,
        "path_prefix": path_prefix,
        "count": len(selected),
        "truncated": len(selected) > max_results,
        "files": selected[:max_results],
    }


def denied_rg_glob_args() -> list[str]:
    """Return rg glob arguments derived from the shared deny lists."""
    globs = [f"!{part}/**" for part in sorted(DENIED_PATH_PARTS)]
    globs.extend(f"!{pattern}" for pattern in DENIED_FILENAME_PATTERNS)
    globs.extend(f"!*{suffix}" for suffix in DENIED_SUFFIXES)
    args: list[str] = []
    for glob in globs:
        args.extend(["--glob", glob])
    return args


def denied_git_grep_pathspecs() -> list[str]:
    """Return git grep pathspec exclusions derived from the shared deny lists."""
    pathspecs = [f":(exclude){part}/**" for part in sorted(DENIED_PATH_PARTS)]
    pathspecs.extend(f":(exclude){pattern}" for pattern in DENIED_FILENAME_PATTERNS)
    pathspecs.extend(f":(exclude)*{suffix}" for suffix in DENIED_SUFFIXES)
    return pathspecs


def tool_search_text(
    root: Path,
    limits: AgenticReviewLimits,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    """Search tracked repository text with git grep."""
    pattern = _required_str(arguments.get("pattern"), "pattern")
    path_prefix = _optional_path_filter(arguments.get("path_prefix"))
    max_results = _positive_int(
        arguments.get("max_results"),
        default=limits.max_search_results,
        upper=limits.max_search_results,
    )
    search_engine = "git grep"
    command = ["git", "grep", "--line-number", "-I", "--", pattern]
    if path_prefix:
        command.append(path_prefix)
    else:
        command.append(".")
    command.extend(denied_git_grep_pathspecs())
    result = run_search_command(
        command,
        cwd=root,
        timeout_sec=limits.tool_timeout_sec,
        search_engine=search_engine,
    )
    if result.returncode not in {0, 1}:
        raise AgenticReviewError(
            result.stderr.strip() or f"{search_engine} search failed"
        )
    lines, omitted_denied = _filter_search_result_lines(result.stdout.splitlines())
    return {
        "ok": True,
        "search_engine": search_engine,
        "pattern": pattern,
        "path_prefix": path_prefix,
        "count": len(lines),
        "omitted_denied": omitted_denied,
        "truncated": len(lines) > max_results,
        "matches": lines[:max_results],
    }


def _filter_search_result_lines(lines: list[str]) -> tuple[list[str], int]:
    """Redact search results and omit matches from denied paths."""
    filtered: list[str] = []
    omitted_denied = 0
    for line in lines:
        match = SEARCH_LINE_RE.match(line)
        if match:
            rel_path = match.group(1)
            try:
                _validate_git_rel_path(rel_path)
                _assert_not_denied_rel_path(rel_path)
            except AgenticReviewError:
                omitted_denied += 1
                continue
        filtered.append(redact_secrets(line))
    return filtered, omitted_denied


def run_search_command(
    command: list[str],
    *,
    cwd: Path,
    timeout_sec: int,
    search_engine: str,
) -> subprocess.CompletedProcess[str]:
    """Run a local search command with a bounded execution time."""
    try:
        return subprocess.run(
            command,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
            timeout=timeout_sec,
        )
    except subprocess.TimeoutExpired as exc:
        raise AgenticReviewError(
            f"{search_engine} search timed out after {timeout_sec}s"
        ) from exc


def tool_read_file(
    root: Path,
    limits: AgenticReviewLimits,
    allow_untracked_paths: tuple[str, ...],
    arguments: dict[str, Any],
) -> dict[str, Any]:
    """Read a text file with line numbers."""
    rel_path = _required_rel_file(root, arguments.get("path"))
    _assert_reviewable_path(
        root,
        rel_path,
        allow_untracked_paths=allow_untracked_paths,
    )
    start_line = _positive_int(arguments.get("start_line"), default=1, upper=1_000_000)
    max_lines = _positive_int(arguments.get("max_lines"), default=200, upper=800)
    path = root / rel_path
    content = path.read_bytes()
    digest = hashlib.sha256(content).hexdigest()
    if b"\0" in content:
        return {
            "ok": True,
            "path": rel_path,
            "binary": True,
            "bytes": len(content),
            "sha256": digest,
            "content": "[binary content omitted]",
        }
    text = redact_secrets(content.decode("utf-8", errors="replace"))
    lines = text.splitlines()
    selected = lines[start_line - 1 : start_line - 1 + max_lines]
    numbered = [
        f"{line_no}: {line}"
        for line_no, line in enumerate(selected, start=start_line)
    ]
    joined = "\n".join(numbered)
    limited, truncated_bytes = _truncate_text(joined, limits.max_tool_result_bytes)
    return {
        "ok": True,
        "path": rel_path,
        "start_line": start_line,
        "line_count": len(lines),
        "returned_lines": len(selected),
        "truncated": truncated_bytes,
        "bytes": len(content),
        "sha256": digest,
        "content": limited,
    }


def tool_git_diff(
    root: Path,
    limits: AgenticReviewLimits,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    """Return selected git diff."""
    base_ref = str(arguments.get("base_ref") or "HEAD").strip()
    _validate_git_ref(base_ref)
    path_prefix = _optional_path_filter(arguments.get("path_prefix"))
    changed_paths = _changed_paths_from_ref(root, base_ref, path_prefix=path_prefix)
    reviewable_paths, denied_paths = _filter_reviewable_paths(changed_paths)
    diff = ""
    if reviewable_paths:
        diff = redact_secrets(_selected_diff_text(root, base_ref, reviewable_paths))
    limited, truncated = _truncate_text(diff, limits.max_tool_result_bytes)
    return {
        "ok": True,
        "base_ref": base_ref,
        "path_prefix": path_prefix,
        "omitted_denied_paths": list(denied_paths),
        "truncated": truncated,
        "content": limited or "[no diff]",
    }


def tool_git_show(
    root: Path,
    limits: AgenticReviewLimits,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    """Show a tracked file from a git ref."""
    ref = str(arguments.get("ref") or "HEAD").strip()
    _validate_git_ref(ref)
    rel_path = _required_str(arguments.get("path"), "path")
    _validate_git_rel_path(rel_path)
    _assert_not_denied_rel_path(rel_path)
    content = _git_bytes(root, ["show", f"{ref}:{rel_path}"])
    digest = hashlib.sha256(content).hexdigest()
    if b"\0" in content:
        return {
            "ok": True,
            "ref": ref,
            "path": rel_path,
            "binary": True,
            "bytes": len(content),
            "sha256": digest,
            "content": "[binary content omitted]",
        }
    text = redact_secrets(content.decode("utf-8", errors="replace"))
    limited, truncated = _truncate_text(text, limits.max_tool_result_bytes)
    return {
        "ok": True,
        "ref": ref,
        "path": rel_path,
        "truncated": truncated,
        "bytes": len(content),
        "sha256": digest,
        "content": limited,
    }


def build_trace(
    *,
    provider: ProviderConfig,
    messages: list[dict[str, Any]],
    runtime: ToolRuntime,
    response_summaries: list[dict[str, Any]],
    status: str,
    thinking_scope: str,
    cache_retry_scope: str,
) -> dict[str, Any]:
    """Build a redacted trace artifact."""
    return {
        "status": status,
        "provider": provider.name,
        "model": provider.model,
        "base_url": provider.base_url,
        "thinking_scope": thinking_scope,
        "cache_retry_scope": cache_retry_scope,
        "workspace_root": str(runtime.root),
        "tool_events": runtime.events,
        "responses": response_summaries,
        "messages": redact_json(messages),
    }


def build_meta(
    provider: ProviderConfig,
    runtime: ToolRuntime,
    response_summaries: list[dict[str, Any]],
    *,
    thinking_scope: str,
    cache_retry_scope: str,
    cache_retry_used: bool,
) -> dict[str, Any]:
    """Build compact non-secret run metadata."""
    usage_totals: dict[str, int] = {}
    for item in response_summaries:
        usage = item.get("usage")
        if not isinstance(usage, dict):
            continue
        for key, value in usage.items():
            if isinstance(value, int):
                usage_totals[key] = usage_totals.get(key, 0) + value
    return {
        "provider": provider.name,
        "model": provider.model,
        "base_url": provider.base_url,
        "thinking_scope": thinking_scope,
        "cache_retry_scope": cache_retry_scope,
        "cache_retry_used": cache_retry_used,
        "tool_calls": runtime.tool_calls,
        "final_rejected_tool_calls": runtime.final_rejected_tool_calls,
        "tool_result_bytes": runtime.total_tool_bytes,
        "responses": len(response_summaries),
        "usage": usage_totals,
        "cache": cache_usage_summary(usage_totals),
    }


def write_text(path: Path, text: str) -> None:
    """Atomically write text."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    """Atomically write JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    tmp.replace(path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run DeepSeek agentic review")
    parser.add_argument("--provider", default="deepseek", help="Provider name")
    parser.add_argument("--config", help="Provider config YAML/JSON")
    parser.add_argument("--workspace-root", default=".", help="Repository root")
    parser.add_argument("--task", help="Review task text")
    parser.add_argument("--task-file", help="Read review task text from a file")
    parser.add_argument("--system-file", help="Optional system prompt override")
    parser.add_argument("--output", required=True, help="Write final review text")
    parser.add_argument("--trace-json", help="Write redacted message/tool trace")
    parser.add_argument("--meta-json", help="Write run metadata")
    parser.add_argument("--model", help="Override provider model")
    parser.add_argument("--base-url", help="Override provider base_url")
    parser.add_argument(
        "--allow-untracked-file",
        action="append",
        default=[],
        help=(
            "Allow the external reviewer to inspect this exact untracked "
            "workspace file. May be passed multiple times."
        ),
    )
    parser.add_argument("--temperature", type=float)
    parser.add_argument(
        "--max-output-tokens",
        type=int,
        default=DEFAULT_MAX_OUTPUT_TOKENS,
    )
    parser.add_argument("--max-iterations", type=int, default=DEFAULT_MAX_ITERATIONS)
    parser.add_argument("--max-tool-calls", type=int, default=DEFAULT_MAX_TOOL_CALLS)
    parser.add_argument(
        "--force-final-after-tool-calls",
        type=int,
        default=None,
        help="Force final answer after this many local tool calls.",
    )
    parser.add_argument(
        "--max-tool-result-bytes",
        type=int,
        default=DEFAULT_MAX_TOOL_RESULT_BYTES,
    )
    parser.add_argument(
        "--max-total-tool-bytes",
        type=int,
        default=DEFAULT_MAX_TOTAL_TOOL_BYTES,
    )
    parser.add_argument(
        "--tool-timeout-sec",
        type=int,
        default=DEFAULT_TOOL_TIMEOUT_SEC,
        help="Per local search-tool subprocess timeout in seconds.",
    )
    parser.add_argument(
        "--thinking-scope",
        choices=sorted(THINKING_SCOPES),
        default=DEFAULT_THINKING_SCOPE,
        help=(
            "Apply provider thinking/reasoning extra_body on all requests, "
            "only the final synthesis request, or no requests."
        ),
    )
    parser.add_argument(
        "--cache-retry-miss-rate",
        type=float,
        default=DEFAULT_CACHE_RETRY_MISS_RATE,
        help=(
            "Retry an unchanged payload once when prompt cache miss rate is "
            "above this threshold. Use 0 to disable."
        ),
    )
    parser.add_argument(
        "--cache-retry-delay-sec",
        type=float,
        default=DEFAULT_CACHE_RETRY_DELAY_SEC,
        help="Seconds to wait before retrying an unchanged high-miss payload.",
    )
    parser.add_argument(
        "--cache-retry-scope",
        choices=sorted(CACHE_RETRY_SCOPES),
        default=DEFAULT_CACHE_RETRY_SCOPE,
        help=(
            "Retry only final synthesis requests or the first high-miss request "
            "of any tool-loop phase."
        ),
    )
    parser.add_argument(
        "--api-retry-attempts",
        type=int,
        default=DEFAULT_API_RETRY_ATTEMPTS,
        help="Maximum attempts for retryable provider HTTP/network failures.",
    )
    parser.add_argument(
        "--api-retry-delay-sec",
        type=float,
        default=DEFAULT_API_RETRY_DELAY_SEC,
        help="Seconds to wait between retryable provider API attempts.",
    )
    args = parser.parse_args(argv)

    try:
        provider = load_provider_config(
            args.provider,
            config_path=args.config or default_config_path(),
            model_override=args.model,
            base_url_override=args.base_url,
        )
        api_key = provider.api_key or os.environ.get(provider.api_key_env or "", "")
        task = _resolve_task(args.task, args.task_file)
        system_prompt = (
            Path(args.system_file).read_text(encoding="utf-8")
            if args.system_file
            else None
        )
        result = run_agentic_review(
            provider,
            api_key=api_key,
            workspace_root=Path(args.workspace_root),
            task=task,
            system_prompt=system_prompt,
            limits=AgenticReviewLimits(
                max_iterations=args.max_iterations,
                max_tool_calls=args.max_tool_calls,
                force_final_after_tool_calls=resolve_force_final_after_tool_calls(
                    max_tool_calls=args.max_tool_calls,
                    requested=args.force_final_after_tool_calls,
                ),
                max_tool_result_bytes=args.max_tool_result_bytes,
                max_total_tool_bytes=args.max_total_tool_bytes,
                tool_timeout_sec=args.tool_timeout_sec,
            ),
            max_tokens=args.max_output_tokens,
            temperature=args.temperature,
            thinking_scope=args.thinking_scope,
            cache_retry_miss_rate=args.cache_retry_miss_rate,
            cache_retry_delay_sec=args.cache_retry_delay_sec,
            cache_retry_scope=args.cache_retry_scope,
            api_retry_attempts=args.api_retry_attempts,
            api_retry_delay_sec=args.api_retry_delay_sec,
            allow_untracked_paths=tuple(args.allow_untracked_file),
        )
        write_text(Path(args.output), result.text)
        if args.trace_json:
            write_json(Path(args.trace_json), result.trace)
        if args.meta_json:
            write_json(Path(args.meta_json), result.meta)
    except AgenticReviewIncompleteError as exc:
        if args.output:
            write_text(
                Path(args.output),
                "INCOMPLETE: agentic review did not produce a final answer.\n"
                f"{exc}\n",
            )
        if args.trace_json:
            write_json(Path(args.trace_json), exc.trace)
        if args.meta_json:
            write_json(Path(args.meta_json), exc.meta)
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except ModelApiError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


def _resolve_task(task: str | None, task_file: str | None) -> str:
    if task and task_file:
        raise AgenticReviewError("Use either --task or --task-file, not both")
    if task_file:
        return Path(task_file).read_text(encoding="utf-8")
    return task or "Review this repository using local tools."


def _extract_response_message(response: dict[str, Any]) -> dict[str, Any]:
    choices = response.get("choices")
    if not isinstance(choices, list) or not choices:
        raise AgenticReviewError("Response does not contain choices")
    first = choices[0]
    if not isinstance(first, dict):
        raise AgenticReviewError("Response choice is not an object")
    message = first.get("message")
    if not isinstance(message, dict):
        raise AgenticReviewError("Response choice does not contain message")
    return dict(message)


def _message_tool_calls(message: dict[str, Any]) -> list[dict[str, Any]]:
    tool_calls = message.get("tool_calls")
    if not isinstance(tool_calls, list):
        return []
    return [item for item in tool_calls if isinstance(item, dict)]


def _message_content(message: dict[str, Any]) -> str:
    content = message.get("content")
    return content.strip() if isinstance(content, str) else ""


def _invalid_final_response_reason(text: str) -> str | None:
    lowered = text.lower()
    for marker in PSEUDO_TOOL_CALL_MARKERS:
        if marker.lower() in lowered:
            return "it contained tool-call markup instead of review text"
    return None


def _parse_tool_call(tool_call: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    function = tool_call.get("function")
    if not isinstance(function, dict):
        raise AgenticReviewError("tool_call.function is missing")
    name = function.get("name")
    if not isinstance(name, str) or not name.strip():
        raise AgenticReviewError("tool_call.function.name is missing")
    raw_arguments = function.get("arguments") or "{}"
    if isinstance(raw_arguments, dict):
        return name, raw_arguments
    if not isinstance(raw_arguments, str):
        raise AgenticReviewError("tool_call.function.arguments must be JSON")
    try:
        parsed = json.loads(raw_arguments or "{}")
    except json.JSONDecodeError as exc:
        raise AgenticReviewError(f"invalid tool arguments JSON: {exc}") from exc
    if not isinstance(parsed, dict):
        raise AgenticReviewError("tool arguments JSON must be an object")
    return name, parsed


def _response_summary(
    response: dict[str, Any],
    iteration: int,
    *,
    payload_fingerprint: dict[str, Any] | None = None,
    cache_retry: bool = False,
    force_final: bool = False,
) -> dict[str, Any]:
    choice = (response.get("choices") or [{}])[0]
    message = choice.get("message") if isinstance(choice, dict) else {}
    tool_calls = []
    if isinstance(message, dict):
        for call in _message_tool_calls(message):
            function = call.get("function")
            name = function.get("name") if isinstance(function, dict) else None
            tool_calls.append(name)
    usage = response.get("usage")
    return {
        "iteration": iteration,
        "id": response.get("id"),
        "created": response.get("created"),
        "api_attempts": response.get("_harness_api_attempts"),
        "usage": usage,
        "cache": cache_usage_summary(usage),
        "cache_retry": cache_retry,
        "force_final": force_final,
        "payload": payload_fingerprint or {},
        "finish_reason": (
            choice.get("finish_reason") if isinstance(choice, dict) else None
        ),
        "tool_calls": tool_calls,
    }


def _should_retry_cache_miss(
    response_summary: dict[str, Any],
    miss_rate_threshold: float | None,
) -> bool:
    if miss_rate_threshold is None or miss_rate_threshold <= 0:
        return False
    cache = response_summary.get("cache")
    if not isinstance(cache, dict):
        return False
    miss_rate = cache.get("prompt_cache_miss_rate")
    return isinstance(miss_rate, float) and miss_rate > miss_rate_threshold


def _tool_error(message: str) -> dict[str, Any]:
    return {"ok": False, "error": redact_secrets(message)}


def _limit_tool_result(result: dict[str, Any], max_bytes: int) -> dict[str, Any]:
    text = json.dumps(result, ensure_ascii=False)
    encoded = text.encode("utf-8")
    if len(encoded) <= max_bytes:
        return result
    limited = _truncate_text_at_utf8_boundary(text, max_bytes)
    return {
        "ok": bool(result.get("ok")),
        "truncated": True,
        "content": limited,
        "note": f"tool result truncated to {max_bytes} bytes",
    }


def _truncate_text(text: str, max_bytes: int) -> tuple[str, bool]:
    encoded = text.encode("utf-8")
    if len(encoded) <= max_bytes:
        return text, False
    return _truncate_text_at_utf8_boundary(text, max_bytes), True


def _truncate_text_at_utf8_boundary(text: str, max_bytes: int) -> str:
    used = 0
    result: list[str] = []
    for char in text:
        char_size = len(char.encode("utf-8"))
        if used + char_size > max_bytes:
            break
        result.append(char)
        used += char_size
    return "".join(result)


def redact_json(value: Any) -> Any:
    if isinstance(value, str):
        return redact_secrets(value)
    if isinstance(value, list):
        return [redact_json(item) for item in value]
    if isinstance(value, dict):
        return {str(key): redact_json(item) for key, item in value.items()}
    return value


def _hash_json(value: Any) -> str:
    canonical = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode()).hexdigest()


def _resolve_workspace_root(path: Path) -> Path:
    root = path.resolve()
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise AgenticReviewError(f"Not a Git workspace: {root}")
    return Path(result.stdout.strip()).resolve()


def _git_text(root: Path, args: list[str]) -> str:
    return _git_bytes(root, args).decode("utf-8", errors="replace")


def _git_z(root: Path, args: list[str]) -> list[str]:
    raw = _git_bytes(root, args)
    return [
        item.decode("utf-8", errors="surrogateescape")
        for item in raw.split(b"\0")
        if item
    ]


def _changed_paths_from_ref(
    root: Path,
    base_ref: str,
    *,
    path_prefix: str | None = None,
) -> list[str]:
    paths: set[str] = set()
    path_args = [path_prefix] if path_prefix else []
    commands = [
        ["diff", "--name-only", "-z", base_ref, "--", *path_args],
        ["diff", "--cached", "--name-only", "-z", base_ref, "--", *path_args],
        ["diff", "--name-only", "-z", "--", *path_args],
    ]
    for command in commands:
        paths.update(_git_z(root, command))
    return sorted(paths)


def _selected_diff_text(
    root: Path,
    base_ref: str,
    changed_paths: tuple[str, ...],
) -> str:
    sections: list[str] = []
    commands = [
        (
            f"base {base_ref} -> worktree",
            ["diff", "--no-ext-diff", "--no-color", base_ref, "--", *changed_paths],
        ),
        (
            f"base {base_ref} -> index (staged)",
            [
                "diff",
                "--cached",
                "--no-ext-diff",
                "--no-color",
                base_ref,
                "--",
                *changed_paths,
            ],
        ),
        (
            "index -> worktree (unstaged)",
            ["diff", "--no-ext-diff", "--no-color", "--", *changed_paths],
        ),
    ]
    for label, command in commands:
        diff = _git_text(root, command).rstrip()
        if diff:
            sections.extend([f"### {label}", diff])
    return "\n\n".join(sections)


def _git_bytes(root: Path, args: list[str]) -> bytes:
    result = subprocess.run(
        ["git", *args],
        cwd=root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        stderr = result.stderr.decode("utf-8", errors="replace").strip()
        raise AgenticReviewError(f"git {' '.join(args)} failed: {stderr}")
    return result.stdout


def _required_str(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise AgenticReviewError(f"{field} is required")
    return value.strip()


def _positive_int(value: Any, *, default: int, upper: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    if parsed <= 0:
        return default
    return min(parsed, upper)


def _optional_path_filter(value: Any) -> str | None:
    if value is None:
        return None
    candidate = _required_str(value, "path_prefix").strip("/")
    _validate_git_rel_path(candidate)
    _assert_not_denied_rel_path(candidate)
    return candidate


def _required_rel_file(root: Path, value: Any) -> str:
    rel_path = _required_str(value, "path").strip("/")
    _validate_git_rel_path(rel_path)
    path = (root / rel_path).resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise AgenticReviewError(f"path escapes workspace: {rel_path}") from exc
    if not path.is_file():
        raise AgenticReviewError(f"file not found: {rel_path}")
    return rel_path


def _validate_git_rel_path(path: str) -> None:
    parts = Path(path).parts
    if path.startswith("/") or ".." in parts:
        raise AgenticReviewError(f"path escapes workspace: {path}")
    if not path or path == ".":
        raise AgenticReviewError("path must not be empty")


def _validate_git_ref(ref: str) -> None:
    if not ref:
        raise AgenticReviewError("git ref must not be empty")
    if len(ref) > 200 or ref.startswith("-") or ":" in ref:
        raise AgenticReviewError(f"git ref is not reviewable: {ref}")
    if re.search(r"[\s\x00-\x1f\x7f]", ref):
        raise AgenticReviewError(f"git ref is not reviewable: {ref}")


def _assert_not_denied_rel_path(rel_path: str) -> None:
    reason = denied_review_path_reason(rel_path)
    if reason:
        raise AgenticReviewError(f"{reason}: {rel_path}")


def _normalize_allow_untracked_paths(paths: tuple[str, ...]) -> tuple[str, ...]:
    normalized: list[str] = []
    for value in paths:
        rel_path = _required_str(value, "allow_untracked_file").strip("/")
        _validate_git_rel_path(rel_path)
        _assert_not_denied_rel_path(rel_path)
        normalized.append(rel_path)
    return tuple(dict.fromkeys(normalized))


def _filter_reviewable_paths(
    paths: tuple[str, ...],
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    reviewable: list[str] = []
    denied: list[str] = []
    for path in paths:
        try:
            _validate_git_rel_path(path)
            _assert_not_denied_rel_path(path)
        except AgenticReviewError:
            denied.append(path)
        else:
            reviewable.append(path)
    return tuple(reviewable), tuple(denied)


def _assert_reviewable_path(
    root: Path,
    rel_path: str,
    *,
    allow_untracked_paths: tuple[str, ...] = (),
) -> None:
    _assert_not_denied_rel_path(rel_path)
    ignored = subprocess.run(
        ["git", "check-ignore", "-q", "--", rel_path],
        cwd=root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if ignored.returncode == 0:
        raise AgenticReviewError(f"ignored file is not reviewable: {rel_path}")
    tracked = subprocess.run(
        ["git", "ls-files", "--error-unmatch", "--", rel_path],
        cwd=root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if tracked.returncode != 0 and rel_path not in allow_untracked_paths:
        raise AgenticReviewError(
            "untracked file is not reviewable without explicit "
            f"--allow-untracked-file: {rel_path}"
        )


def _allowed_existing_untracked_paths(
    root: Path,
    allow_untracked_paths: tuple[str, ...],
) -> list[str]:
    if not allow_untracked_paths:
        return []
    untracked = set(_git_z(root, ["ls-files", "--others", "--exclude-standard", "-z"]))
    return sorted(path for path in allow_untracked_paths if path in untracked)


def _filter_status_short_for_external(
    status: str,
    *,
    allow_untracked_paths: tuple[str, ...],
) -> tuple[str, int]:
    lines: list[str] = []
    omitted = 0
    omitted_marker_added = False
    for line in status.splitlines():
        if line.startswith("?? "):
            rel_path = line[3:].strip()
            if rel_path not in allow_untracked_paths:
                omitted += 1
                if not omitted_marker_added:
                    lines.append("?? [untracked files omitted unless allowlisted]")
                    omitted_marker_added = True
                continue
        lines.append(line)
    return "\n".join(lines), omitted


def _path_matches_filter(path: str, path_filter: str) -> bool:
    return path == path_filter or path.startswith(path_filter.rstrip("/") + "/")


def _split_lines(text: str) -> list[str]:
    return [line for line in text.splitlines() if line]


if __name__ == "__main__":
    raise SystemExit(main())
