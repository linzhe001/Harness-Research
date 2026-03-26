from __future__ import annotations

from typing import Any

from .result import CommandResult, default_message_for_category


def _metric_text(raw: Any) -> str:
    if raw is None:
        return "n/a"
    if isinstance(raw, dict):
        pieces = [f"{k}={v}" for k, v in raw.items()]
        return ", ".join(pieces) if pieces else "n/a"
    return str(raw)


def render_status_text(status: dict[str, Any]) -> str:
    if status.get("error"):
        return str(status["error"])

    lines = [
        f"Status: {status.get('status', 'unknown')}",
        f"Round: {status.get('current_round_index', 'n/a')} / {status.get('budget', {}).get('max_rounds', 'n/a')}",
        f"Phase: {status.get('current_phase_key', 'n/a')}",
        f"Account: {status.get('accounts', {}).get('selected_account_id') or 'n/a'}",
        f"Metric: {status.get('objective', {}).get('primary_metric', {}).get('name') or 'n/a'}",
        f"Best: {_metric_text(status.get('best', {}).get('primary_metric'))}",
    ]
    halt_reason = status.get("halt_reason")
    if halt_reason:
        lines.append(f"Halt: {halt_reason}")
    last_failure = status.get("last_failure")
    if last_failure:
        lines.append(f"Failure: {last_failure}")
    return "\n".join(lines)


def render_tail_text(events: list[dict[str, Any]]) -> str:
    if not events:
        return "No recent auto-iterate events."

    rendered = []
    for event in events:
        ts = event.get("ts", "")
        round_idx = event.get("round_index", "")
        name = event.get("event", "")
        phase = event.get("phase_key", "")
        rendered.append(f"{ts}  R{round_idx}  {name}  {phase}".rstrip())
    return "\n".join(rendered)


def render_logs_text(log_info: dict[str, Any]) -> str:
    header = f"Log: {log_info.get('path')} [{log_info.get('stream')}]"
    content = log_info.get("content", "")
    return f"{header}\n{content}".rstrip()


def render_exit_message(result: CommandResult) -> str:
    if result.message:
        return result.message
    return default_message_for_category(result.category)


def render_summary_text(summary: dict[str, Any]) -> str:
    workspace = summary.get("workspace", {})
    ai = summary.get("auto_iterate", {})
    latest_event = summary.get("latest_event") or {}

    lines = [
        f"Workspace: {workspace.get('name', 'n/a')}",
        f"Root: {workspace.get('root', 'n/a')}",
        f"AI Loop: {ai.get('status') or 'n/a'}",
        f"Round: {ai.get('current_round_index') if ai.get('current_round_index') is not None else 'n/a'}",
        f"Phase: {ai.get('current_phase_key') or 'n/a'}",
        f"Account: {ai.get('selected_account_id') or 'n/a'}",
        f"Metric: {ai.get('metric_name') or 'n/a'}",
        f"Staged Goal: {'yes' if summary.get('staged_goal_present') else 'no'}",
    ]

    event_name = latest_event.get("event")
    if event_name:
        lines.append(
            f"Latest Event: {event_name} (R{latest_event.get('round_index', 'n/a')} {latest_event.get('phase_key', '')})".rstrip()
        )
    actions = summary.get("recommended_actions") or []
    if actions:
        lines.append("Recommended:")
        for action in actions[:4]:
            lines.append(f"- {action.get('label')}: {action.get('value')}")
    return "\n".join(lines)


def render_hint_text(hint: dict[str, Any]) -> str:
    lines = [hint.get("title", "推荐操作")]
    for action in hint.get("recommended_actions", []):
        lines.append(f"- {action.get('label')}: {action.get('value')}")
    return "\n".join(lines)
