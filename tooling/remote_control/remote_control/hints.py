from __future__ import annotations

from typing import Any


def _action(label: str, kind: str, value: str, reason: str) -> dict[str, str]:
    return {"label": label, "kind": kind, "value": value, "reason": reason}


def recommended_actions(summary: dict[str, Any]) -> list[dict[str, str]]:
    ai = summary.get("auto_iterate", {})
    status = ai.get("status")

    if status == "running":
        return [
            _action("查看状态", "command", "/ai status", "确认当前 loop 状态。"),
            _action("查看事件", "command", "/ai tail", "快速看最近一轮发生了什么。"),
            _action("暂停", "command", "/ai pause", "在下一安全边界暂停 loop。"),
            _action("停止", "command", "/ai stop", "在下一安全边界停止 loop。"),
        ]
    if status == "paused":
        return [
            _action("查看事件", "command", "/ai tail", "确认暂停前最后一个事件。"),
            _action("继续", "command", "/ai resume", "从当前 state 恢复 loop。"),
            _action("停止", "command", "/ai stop", "不再继续当前 loop。"),
            _action("修改项目", "prompt", "请检查当前 workspace 并按我的要求修改，然后我再决定是否 resume。", "在恢复前让 agent 先改项目。"),
        ]
    if status == "blocked":
        return [
            _action("查看状态", "command", "/ai status", "看清当前阻塞原因。"),
            _action("查看日志", "command", "/ai logs --stream stderr", "定位失败原因。"),
            _action("查看事件", "command", "/ai tail", "看阻塞前最近的 controller 事件。"),
            _action("修改项目", "prompt", "请先检查当前失败原因并修改项目。", "人工介入后再决定继续。"),
        ]
    return [
        _action("新会话", "command", "/new", "开始一个新的工作会话。"),
        _action("查看工作区", "command", "/workspace", "确认当前绑定的 workspace。"),
        _action("查看状态", "command", "/ai status", "确认 auto-iterate 是否已运行。"),
        _action("帮助", "command", "/help", "查看完整命令分组。"),
    ]


def build_hint(context_name: str, summary: dict[str, Any]) -> dict[str, Any]:
    context_name = context_name.strip().lower()

    if context_name == "workspace-switched":
        title = "Workspace 已切换"
        actions = [
            _action("新会话", "command", "/new", "在新 workspace 中开始新上下文。"),
            _action("当前会话", "command", "/current", "确认当前 active session。"),
            _action("查看状态", "command", "/ai status", "看该 workspace 的 loop 状态。"),
            _action("工作区帮助", "command", "/help workspace", "查看 workspace 相关命令。"),
        ]
    elif context_name == "session-switched":
        title = "Session 已切换"
        actions = [
            _action("直接开始", "prompt", "请基于当前 session 和 workspace 继续工作。", "直接进入正常工作流。"),
            _action("Provider", "command", "/provider", "确认当前 provider。"),
            _action("查看状态", "command", "/ai status", "确认 loop 状态。"),
            _action("会话帮助", "command", "/help session", "查看 session 相关命令。"),
        ]
    elif context_name == "ai-paused":
        title = "Auto-iterate 已暂停"
        actions = [
            _action("查看事件", "command", "/ai tail", "看 pause 前最后事件。"),
            _action("查看日志", "command", "/ai logs", "看最近 stdout。"),
            _action("继续", "command", "/ai resume", "从当前 state 恢复。"),
            _action("停止", "command", "/ai stop", "不再继续当前 loop。"),
            _action("修改项目", "prompt", "请先检查当前 workspace 并按我的要求修改。", "恢复前先人工/agent 干预。"),
        ]
    elif context_name == "provider-switched":
        title = "Provider 已切换"
        actions = [
            _action("查看 Provider", "command", "/provider", "确认当前 active provider。"),
            _action("新会话", "command", "/new", "用新 provider 开一个干净会话。"),
            _action("继续对话", "prompt", "请继续当前研究工作。", "直接继续正常工作。"),
            _action("帮助", "command", "/help", "查看可用命令。"),
        ]
    else:
        title = "推荐操作"
        actions = recommended_actions(summary)

    return {
        "context": context_name,
        "title": title,
        "recommended_actions": actions,
    }
