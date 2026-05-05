from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

CONTRACTS_PATH = Path(".agents/skill-contracts/contracts.json")
RUNTIME_DIR = Path(".harness_hooks")
SESSION_PATH = RUNTIME_DIR / "session.json"
READ_LEDGER_PATH = RUNTIME_DIR / "read_ledger.json"
PENDING_PATH = RUNTIME_DIR / "pending_actions.json"

IGNORE_GIT_ADD_PATTERNS = [
    "ref/",
    "plan.markdown",
    "跨项目共享上下文解析.txt",
    "Harness_Update_Guide.md",
]

DIRECT_TOOL_OWNED_PATHS = [
    ".evidence/",
    ".auto_iterate/",
]

KNOWN_REQUIRED_ACTIONS = {
    "approval_tool_only_after_explicit_human_approval",
    "build_review_packet_or_NOT_RUN",
    "changed_line_map",
    "check_docchain_gates_or_NOT_RUN",
    "check_dynamic_context_or_NOT_RUN",
    "check_dynamic_context_wf12_or_NOT_RUN",
    "check_protocol_drift_or_NOT_RUN",
    "claim_boundary_check",
    "codex_review_or_NOT_RUN",
    "collect_review_scope",
    "compile_doc_or_NOT_RUN",
    "compile_protocol_or_NOT_RUN",
    "context_gate_or_NOT_RUN",
    "decision_vocabulary",
    "docchain_gate_when_current_docs_change",
    "explicit_user_approval_for_transition",
    "external_model_review_or_NOT_RUN",
    "gate_ledger",
    "git_metadata_snapshot",
    "goal_validate_or_init",
    "iteration_log_update",
    "lesson_quality_check_or_NOT_RUN",
    "protocol_review_or_NOT_RUN",
    "py_compile_or_NOT_RUN",
    "read_project_map_before_stable_code",
    "release_manifest_validation",
    "respect_claim_boundary",
    "respect_evaluation_contract",
    "reconcile_review_findings",
    "ruff_or_NOT_RUN",
    "semantic_commit_or_NOT_RUN",
    "semantic_review",
    "smoke_test_or_NOT_RUN",
    "update_project_map",
    "workflow_state_gate_or_NOT_RUN",
    "write_implementation_roadmap",
    "write_review_report_or_NOT_RUN",
    "write_validate_report",
}

KNOWN_FORBIDDEN_ACTIONS = {
    "WF11_without_approved_contracts",
    "WF9_PASS_without_semantic_review",
    "WF9_PASS_without_smoke_evidence",
    "approve_without_explicit_human_approval",
    "architecture_decision_in_build_plan",
    "auto_observation_direct_to_MEMORY",
    "current_doc_without_docchain",
    "direct_edit_auto_iterate",
    "direct_edit_evidence",
    "final_exp_outside_claim_boundary",
    "heavy_review_without_trace",
    "ignore_unresolved_protocol_drift",
    "manual_edit_auto_iterate",
    "manual_edit_evidence_chain",
    "modify_subject_files_during_code_review",
    "overwrite_package_without_confirmation",
    "packet_as_approval",
    "project_map_stale",
    "protocol_as_approved_contract",
    "release_claim_outside_claim_boundary",
    "review_without_line_references",
    "stable_code_without_project_map_read",
    "stage_transition_from_iterate",
    "stage_transition_without_user_approval",
    "start_auto_iterate_without_goal_validation",
    "submit_without_explicit_user_request",
    "training_without_semantic_commit",
    "unverified_model_finding_as_fact",
}

READ_COMMAND_RE = re.compile(
    r"\b(cat|sed|nl|rg|grep|head|tail|less|more|find|ls|git\s+diff|git\s+show|git\s+status)\b"
)
MUTATING_COMMAND_RE = re.compile(
    r"(^|\s)(rm|mv|cp|touch|mkdir|chmod|chown|git\s+add|git\s+commit|git\s+rm|python\s+.*approve_contract\.py)\b|>|>>"
)
MUTATING_TOOL_NAMES = {"apply_patch", "Edit", "Write", "Bash", "shell", "local_shell"}
READ_TOOL_NAMES = {"Read", "View", "Open"}
REVIEW_WRITE_ALLOWED_PATHS = [".agents/state/review_traces/code-review/"]
DAILY_CONTEXT_FILES = ("AGENTS.md", "CLAUDE.md")
PATH_TOKEN_RE = re.compile(
    r"(?<![\w.-])(?:[A-Za-z0-9_.-]+[/\\])+[A-Za-z0-9_.@%+=:,~-]+|"
    r"(?<![\w.-])[A-Za-z0-9_.@%+=:,~-]+\."
    r"(?:md|py|json|toml|ya?ml|txt|sh|bash|ts|tsx|js|jsx|css|html|lock|cfg|ini)\b",
    re.IGNORECASE,
)
EXPLICIT_TRIGGER_RE = re.compile(r"^[$/][A-Za-z0-9_-]+$")
WORKFLOW_TRIGGER_RE = re.compile(r"^wf\d+[a-z-]*$", re.IGNORECASE)
CODE_WRITE_RE = re.compile(
    r"\b(implement|create|add|write|generate|scaffold|fix|debug|modify|edit|change|update|"
    r"refactor|adjust|improve|remove|delete|patch)\b|"
    r"(实现|创建|新增|添加|写|生成|修复|修改|调整|完善|优化|更新|重构|删除|改一下|改成)",
    re.IGNORECASE,
)
CODE_CREATE_RE = re.compile(
    r"\b(implement|create|add|write|generate|scaffold|build)\b|"
    r"(实现|创建|新增|添加|写一个|生成)",
    re.IGNORECASE,
)
CODE_MODIFY_RE = re.compile(
    r"\b(fix|debug|modify|edit|change|update|refactor|adjust|improve|remove|delete|patch)\b|"
    r"(修复|修改|调整|完善|优化|更新|重构|删除|改一下|改成)",
    re.IGNORECASE,
)
CODE_TARGET_RE = re.compile(
    r"\b(src|scripts|tests|tooling|configs?|hook|hooks|skill detection|"
    r"function|class|method|module|pytest|ruff|py_compile|python|"
    r"typescript|javascript)\b|"
    r"(代码|函数|类|模块|脚本|测试|钩子|修改代码|写代码)",
    re.IGNORECASE,
)
CODE_SEARCH_RE = re.compile(
    r"\b(where|find|search|locate|grep|rg|show|list|inspect|explain|read|look up)\b|"
    r"(在哪|在哪里|位置|找一下|找到|查找|检索|搜索|看一下|查看|解释|说明|是什么|有哪些|列出)",
    re.IGNORECASE,
)
CODE_REVIEW_RE = re.compile(
    r"\b(code[- ]?review|review\s+code|codex\s+review|deepseek\s+review|"
    r"cross[- ]?review|review\s+diff|audit\s+diff)\b|"
    r"(代码\s*review|代码审查|代码检查|交叉验证|交叉\s*review)",
    re.IGNORECASE,
)
REVIEW_TARGET_RE = re.compile(
    r"\b(diff|git|pr|pull request|changed|changes|staged|unstaged|docs?|"
    r"evidence|gate|release|review report|line references?)\b|"
    r"(修改|改动|差异|文档|证据链|报告|阶段|闸门|关卡|行号)",
    re.IGNORECASE,
)
REVIEW_HEAVY_RE = re.compile(
    r"\b(heavy|deep|stage|gate|evidence|release|final|docs?|docchain|"
    r"cross[- ]?validation|cross[- ]?review)\b|"
    r"(重型|重度|深入|阶段|闸门|关卡|证据链|文档|发布|交叉验证)",
    re.IGNORECASE,
)
REVIEW_MEDIUM_RE = re.compile(
    r"\b(medium|post[- ]?change|after\s+changes?|diff|git|staged|unstaged|"
    r"working\s+tree|pr|pull request)\b|"
    r"(中型|修改完|改完|改动|差异|当前修改|工作区)",
    re.IGNORECASE,
)


def repo_root(cwd: str | Path | None = None) -> Path:
    start = Path(cwd or os.getcwd()).resolve()
    for path in [start, *start.parents]:
        if (path / ".git").exists():
            return path
    return start


def rel_path(path: str | Path, root: Path) -> str:
    p = Path(path)
    if not p.is_absolute():
        p = root / p
    try:
        return p.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return p.as_posix()


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_contracts(root: Path) -> list[dict[str, Any]]:
    data = load_json(root / CONTRACTS_PATH, {"contracts": []})
    return list(data.get("contracts", []))


def is_harness_workspace(root: Path) -> bool:
    return (root / CONTRACTS_PATH).exists()


def contract_by_skill(root: Path, skill: str) -> dict[str, Any] | None:
    for contract in load_contracts(root):
        if contract.get("skill") == skill:
            return contract
    return None


def _looks_path_like(value: str) -> bool:
    return bool(PATH_TOKEN_RE.search(value) or "/" in value or "\\" in value)


def detection_text(prompt: str) -> str:
    def replace_inline(match: re.Match[str]) -> str:
        value = match.group(1)
        if EXPLICIT_TRIGGER_RE.match(value):
            return value
        if _looks_path_like(value):
            return " "
        return value

    text = re.sub(r"`([^`]+)`", replace_inline, prompt)
    return PATH_TOKEN_RE.sub(" ", text)


def classify_prompt_intent(prompt: str) -> str:
    text = detection_text(prompt)
    if CODE_REVIEW_RE.search(text) and (
        CODE_TARGET_RE.search(text) or REVIEW_TARGET_RE.search(text)
    ):
        return f"code_review_{classify_review_mode(prompt)}"
    if CODE_WRITE_RE.search(text) and CODE_TARGET_RE.search(text):
        return "code_write"
    if CODE_SEARCH_RE.search(text):
        return "code_search"
    return "unknown"


def classify_review_mode(prompt: str) -> str:
    text = detection_text(prompt)
    if REVIEW_HEAVY_RE.search(text):
        return "heavy"
    if REVIEW_MEDIUM_RE.search(text):
        return "medium"
    if CODE_SEARCH_RE.search(text) and not CODE_WRITE_RE.search(text):
        return "light"
    return "medium"


def _trigger_match(text: str, trigger: str) -> re.Match[str] | None:
    trigger = trigger.strip()
    if not trigger:
        return None
    escaped = re.escape(trigger)
    if EXPLICIT_TRIGGER_RE.match(trigger):
        return re.search(rf"(?<![\w-]){escaped}(?![\w-])", text, flags=re.IGNORECASE)
    if WORKFLOW_TRIGGER_RE.match(trigger):
        return re.search(rf"(?<![\w-]){escaped}(?![\w-])", text, flags=re.IGNORECASE)
    if " " in trigger:
        return re.search(
            rf"(?<![\w/.-]){escaped}(?![\w/.-])", text, flags=re.IGNORECASE
        )
    return re.search(rf"(?<![\w-]){escaped}(?![\w-])", text, flags=re.IGNORECASE)


def _trigger_score(trigger: str, explicit: bool) -> int:
    if explicit:
        return 10_000 + len(trigger)
    if WORKFLOW_TRIGGER_RE.match(trigger):
        return 8_000 + len(trigger)
    if " " in trigger:
        return 1_000 + len(trigger)
    return 100 + len(trigger)


def detect_skill_match(root: Path, prompt: str) -> dict[str, Any] | None:
    prompt_l = prompt.lower()
    cleaned_l = detection_text(prompt).lower()
    best: tuple[int, dict[str, Any], str, str] | None = None
    for contract in load_contracts(root):
        for trigger_value in contract.get("triggers", []):
            trigger = str(trigger_value).lower()
            explicit = bool(
                EXPLICIT_TRIGGER_RE.match(trigger) or WORKFLOW_TRIGGER_RE.match(trigger)
            )
            text = prompt_l if explicit else cleaned_l
            if not _trigger_match(text, trigger):
                continue
            trigger_type = "explicit" if explicit else "implicit"
            score = _trigger_score(trigger, explicit)
            if best is None or score > best[0]:
                best = (score, contract, trigger, trigger_type)
    if best:
        _, contract, trigger, trigger_type = best
        intent = classify_prompt_intent(prompt)
        read_required = (
            trigger_type == "explicit" or contract.get("skill") == "code-review"
        )
        return {
            "contract": contract,
            "skill": contract.get("skill"),
            "trigger": trigger,
            "trigger_type": trigger_type,
            "intent_class": intent,
            "read_contract_stop_required": read_required,
        }

    intent = classify_prompt_intent(prompt)
    if intent.startswith("code_review_"):
        contract = contract_by_skill(root, "code-review")
        if contract:
            return {
                "contract": contract,
                "skill": "code-review",
                "trigger": "inferred_code_review",
                "trigger_type": "inferred",
                "intent_class": intent,
                "read_contract_stop_required": True,
            }
    if intent == "code_write":
        create_score = bool(CODE_CREATE_RE.search(detection_text(prompt)))
        modify_score = bool(CODE_MODIFY_RE.search(detection_text(prompt)))
        skill = "code-expert" if create_score and not modify_score else "code-debug"
        contract = contract_by_skill(root, skill)
        if contract:
            return {
                "contract": contract,
                "skill": skill,
                "trigger": "inferred_code_write",
                "trigger_type": "inferred",
                "intent_class": intent,
                "read_contract_stop_required": False,
            }
    return None


def detect_skill(root: Path, prompt: str) -> dict[str, Any] | None:
    match = detect_skill_match(root, prompt)
    return match["contract"] if match else None


def hook_event_name(event: dict[str, Any]) -> str | None:
    value = event.get("hook_event_name") or event.get("hookEventName")
    return str(value) if value is not None else None


def tool_name(event: dict[str, Any]) -> str:
    value = event.get("tool_name") or event.get("toolName") or event.get("tool")
    if isinstance(value, dict):
        value = value.get("name")
    return str(value or "")


def tool_input(event: dict[str, Any]) -> dict[str, Any]:
    for key in ("tool_input", "toolInput", "input", "arguments", "args"):
        value = event.get(key)
        if isinstance(value, dict):
            return value
    return {}


def tool_text(event: dict[str, Any]) -> str:
    payload = tool_input(event)
    parts: list[str] = []
    for key in ("command", "cmd", "script", "patch", "text", "content"):
        value = payload.get(key)
        if isinstance(value, str):
            parts.append(value)
    return "\n".join(parts)


def normalize_tool_name(name: str) -> str:
    if name in {"shell", "local_shell"}:
        return "Bash"
    return name


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def required_existing_files(root: Path, contract: dict[str, Any]) -> list[str]:
    read_set = contract.get("required_read_set", {})
    paths: list[str] = []
    for section in ("harness", "skill"):
        paths.extend(str(p) for p in read_set.get(section, []))
    for path in read_set.get("project_when_present", []):
        if (root / path).exists():
            paths.append(str(path))
    return sorted(dict.fromkeys(paths))


def daily_context_for_workspace(root: Path) -> str:
    if not is_harness_workspace(root):
        return ""
    files = [path for path in DAILY_CONTEXT_FILES if (root / path).is_file()]
    if not files:
        return ""
    return (
        "Harness daily workspace context:\n"
        "Repository guidance files are present. Read these before "
        "repository-specific answers or tool use:\n"
        + "\n".join(f"- {path}" for path in files)
        + "\nThis is ordinary workspace context, not a workflow skill contract."
    )


def validate_contract_files(root: Path) -> list[str]:
    errors: list[str] = []
    seen_skills: set[str] = set()
    for contract in load_contracts(root):
        skill = contract.get("skill", "<unknown>")
        read_set = contract.get("required_read_set", {})
        if skill in seen_skills:
            errors.append(f"{skill}: duplicate skill contract")
        seen_skills.add(str(skill))
        expected_skill_path = f".agents/skills/{skill}/SKILL.md"
        if expected_skill_path not in read_set.get("skill", []):
            errors.append(
                f"{skill}: required_read_set.skill must include {expected_skill_path}"
            )
        if "AGENTS.md" not in read_set.get("project_when_present", []):
            errors.append(
                f"{skill}: required_read_set.project_when_present must "
                "include AGENTS.md"
            )
        for action in contract.get("required_actions", []):
            if action not in KNOWN_REQUIRED_ACTIONS:
                errors.append(f"{skill}: unknown required action: {action}")
        for action in contract.get("forbidden_actions", []):
            if action not in KNOWN_FORBIDDEN_ACTIONS:
                errors.append(f"{skill}: unknown forbidden action: {action}")
        for section in ("harness", "skill"):
            for path in read_set.get(section, []):
                if not (root / path).exists():
                    errors.append(
                        f"{skill}: missing required {section} read file: {path}"
                    )
        skill_file = root / ".agents" / "skills" / str(skill) / "SKILL.md"
        if not skill_file.exists():
            errors.append(
                f"{skill}: missing skill file: {skill_file.relative_to(root)}"
            )
    return errors


def load_session(root: Path) -> dict[str, Any]:
    return load_json(root / SESSION_PATH, {})


def save_session(root: Path, session: dict[str, Any]) -> None:
    write_json(root / SESSION_PATH, session)


def load_read_ledger(root: Path) -> dict[str, Any]:
    return load_json(root / READ_LEDGER_PATH, {"reads": {}})


def save_read_ledger(root: Path, ledger: dict[str, Any]) -> None:
    write_json(root / READ_LEDGER_PATH, ledger)


def reset_read_ledger(root: Path) -> None:
    save_read_ledger(root, {"reads": {}})


def load_pending(root: Path) -> dict[str, Any]:
    pending = load_json(
        root / PENDING_PATH,
        {
            "requires_gate_ledger": False,
            "reasons": [],
            "changed_paths": [],
            "gate_ledger_notice_emitted": False,
        },
    )
    pending.setdefault("requires_gate_ledger", False)
    pending.setdefault("reasons", [])
    pending.setdefault("changed_paths", [])
    pending.setdefault("gate_ledger_notice_emitted", False)
    return pending


def save_pending(root: Path, pending: dict[str, Any]) -> None:
    pending["reasons"] = sorted(set(str(x) for x in pending.get("reasons", [])))
    pending["changed_paths"] = sorted(
        set(str(x) for x in pending.get("changed_paths", []))
    )
    if not pending.get("requires_gate_ledger"):
        pending["gate_ledger_notice_emitted"] = False
    write_json(root / PENDING_PATH, pending)


def read_tracking_candidates(
    root: Path, contract: dict[str, Any] | None = None
) -> list[str]:
    candidates: list[str] = []
    if contract:
        candidates.extend(required_existing_files(root, contract))
        candidates.extend(
            str(p)
            for p in contract.get("required_read_set", {}).get("project_optional", [])
        )
    candidates.extend(
        [
            "AGENTS.md",
            "PROJECT_STATE.json",
            "project_map.json",
            "iteration_log.json",
            "CLAUDE.md",
        ]
    )
    existing = [path for path in candidates if path and (root / path).is_file()]
    return sorted(dict.fromkeys(existing))


def record_read(
    root: Path, path: str, event: dict[str, Any], source: str = "tool"
) -> bool:
    full = root / path
    if not full.exists() or not full.is_file():
        return False
    ledger = load_read_ledger(root)
    reads = ledger.setdefault("reads", {})
    rel = rel_path(full, root)
    is_new_read = rel not in reads
    entry = reads.setdefault(rel, {"events": []})
    entry["sha256"] = file_hash(full)
    entry["events"].append(
        {
            "hook_event_name": event.get("hook_event_name"),
            "hookEventName": event.get("hookEventName"),
            "turn_id": event.get("turn_id"),
            "tool_name": tool_name(event),
            "source": source,
        }
    )
    save_read_ledger(root, ledger)
    return is_new_read


def record_command_reads(root: Path, command: str, event: dict[str, Any]) -> list[str]:
    if not READ_COMMAND_RE.search(command):
        return []
    session = load_session(root)
    skill = session.get("active_skill")
    contract = None
    if skill:
        contract = contract_by_skill(root, skill)
    recorded: list[str] = []
    for path in sorted(read_tracking_candidates(root, contract), key=len, reverse=True):
        if path in command:
            if record_read(root, path, event, source="command"):
                recorded.append(path)
    return recorded


def record_direct_tool_read(root: Path, event: dict[str, Any]) -> list[str]:
    name = normalize_tool_name(tool_name(event))
    if name not in READ_TOOL_NAMES:
        return []
    payload = tool_input(event)
    candidates = []
    for key in ("path", "file_path", "filePath", "uri"):
        value = payload.get(key)
        if isinstance(value, str):
            candidates.append(value)
    allowed = set(read_tracking_candidates(root, active_contract(root)))
    recorded: list[str] = []
    for candidate in candidates:
        rel = rel_path(candidate, root)
        if rel in allowed:
            if record_read(root, rel, event, source=name):
                recorded.append(rel)
    return recorded


def missing_reads(root: Path, contract: dict[str, Any]) -> list[str]:
    ledger = load_read_ledger(root)
    read_paths = set(ledger.get("reads", {}).keys())
    return [
        path
        for path in required_existing_files(root, contract)
        if path not in read_paths
    ]


def active_contract(root: Path) -> dict[str, Any] | None:
    session = load_session(root)
    skill = session.get("active_skill")
    if not skill:
        return None
    return contract_by_skill(root, skill)


def looks_mutating_bash(command: str) -> bool:
    return bool(MUTATING_COMMAND_RE.search(command))


def is_mutating_tool_event(event: dict[str, Any]) -> bool:
    name = normalize_tool_name(tool_name(event))
    command = tool_text(event)
    return name in {"apply_patch", "Edit", "Write"} or (
        name == "Bash" and looks_mutating_bash(command)
    )


def mutating_event_paths(root: Path, event: dict[str, Any]) -> list[str]:
    name = normalize_tool_name(tool_name(event))
    command = tool_text(event)
    payload = tool_input(event)
    paths: list[str] = []
    if name == "apply_patch":
        for match in re.finditer(
            r"^\*\*\* (?:Add|Update|Delete) File: (.+)$", command, flags=re.MULTILINE
        ):
            paths.append(rel_path(match.group(1).strip(), root))
    elif name in {"Edit", "Write"}:
        for key in ("path", "file_path", "filePath"):
            value = payload.get(key)
            if isinstance(value, str):
                paths.append(rel_path(value, root))
    elif name == "Bash" and looks_mutating_bash(command):
        if any(path in command for path in REVIEW_WRITE_ALLOWED_PATHS):
            paths.extend(REVIEW_WRITE_ALLOWED_PATHS)
        else:
            paths.append("<bash mutation>")
    return paths


def mark_tool_activity(root: Path, event: dict[str, Any]) -> dict[str, Any]:
    session = load_session(root)
    if not is_harness_workspace(root):
        return session
    if is_mutating_tool_event(event):
        session["mutating_tool_seen"] = True
        session["last_mutating_tool"] = normalize_tool_name(tool_name(event))
        session["last_mutating_turn_id"] = event.get("turn_id")
        save_session(root, session)
    return session


def changed_paths(root: Path) -> list[str]:
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only"],
            cwd=root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    except OSError:
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def path_matches_any(path: str, patterns: list[str]) -> bool:
    for pattern in patterns:
        if pattern.endswith("/"):
            if path == pattern[:-1] or path.startswith(pattern):
                return True
        elif path == pattern:
            return True
    return False


def mark_pending_for_changes(root: Path, event: dict[str, Any]) -> dict[str, Any]:
    pending = load_pending(root)
    if not is_harness_workspace(root):
        return pending

    contract = active_contract(root)
    paths = changed_paths(root)
    if contract:
        sensitive = list(contract.get("sensitive_paths", []))
    else:
        sensitive = [
            "PROJECT_STATE.json",
            "iteration_log.json",
            "project_map.json",
            "docs/",
            "src/",
            "scripts/",
            "configs/",
        ]
    touched = [p for p in paths if path_matches_any(p, sensitive)]
    if touched:
        already_pending = bool(pending.get("requires_gate_ledger"))
        pending["requires_gate_ledger"] = True
        if not already_pending:
            pending["gate_ledger_notice_emitted"] = False
        pending.setdefault("reasons", []).append("sensitive workflow files changed")
        pending.setdefault("changed_paths", []).extend(touched)
        pending["last_turn_id"] = event.get("turn_id")
    save_pending(root, pending)
    return pending


def consume_gate_ledger_notice(root: Path, pending: dict[str, Any]) -> bool:
    if not pending.get("requires_gate_ledger"):
        return False
    if pending.get("gate_ledger_notice_emitted"):
        return False
    pending["gate_ledger_notice_emitted"] = True
    save_pending(root, pending)
    return True


def block_pre_tool(root: Path, event: dict[str, Any]) -> str | None:
    if not is_harness_workspace(root):
        return None

    name = normalize_tool_name(tool_name(event))
    command = tool_text(event)

    if name == "Bash":
        for pattern in IGNORE_GIT_ADD_PATTERNS:
            if re.search(r"\bgit\s+add\b", command) and pattern in command:
                return (
                    "Blocked by Harness policy: do not add local/reference "
                    f"artifact `{pattern}` to git."
                )
        if any(
            path in command for path in DIRECT_TOOL_OWNED_PATHS
        ) and looks_mutating_bash(command):
            if (
                "tooling/evidence/" not in command
                and "tooling/auto_iterate/" not in command
            ):
                return (
                    "Blocked by Harness policy: .evidence/** and "
                    ".auto_iterate/** are tool/controller-owned paths."
                )

    if name == "apply_patch":
        patch_text = command
        if any(
            f"*** Update File: {p}" in patch_text or f"*** Add File: {p}" in patch_text
            for p in DIRECT_TOOL_OWNED_PATHS
        ):
            return (
                "Blocked by Harness policy: do not manually patch "
                ".evidence/** or .auto_iterate/**."
            )

    contract = active_contract(root)
    is_mutating_tool = is_mutating_tool_event(event)
    if contract and is_mutating_tool:
        missing = missing_reads(root, contract)
        if missing:
            shown = "\n".join(f"- {p}" for p in missing[:12])
            return (
                "Required read set is incomplete before write actions for "
                f"`{contract['skill']}`:\n{shown}"
            )
        if contract.get("skill") == "code-review":
            paths = mutating_event_paths(root, event)
            disallowed = [
                p for p in paths if not path_matches_any(p, REVIEW_WRITE_ALLOWED_PATHS)
            ]
            if disallowed:
                shown = "\n".join(f"- {p}" for p in disallowed[:12])
                return (
                    "Blocked by Harness policy: `code-review` is review-only. "
                    "Write review artifacts only under "
                    "`.agents/state/review_traces/code-review/` and route fixes "
                    f"through `$code-debug`.\n{shown}"
                )
    return None


def hook_block(event_name: str, reason: str) -> dict[str, Any]:
    if event_name == "PreToolUse":
        return {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": reason,
            }
        }
    if event_name == "PermissionRequest":
        return {
            "hookSpecificOutput": {
                "hookEventName": "PermissionRequest",
                "decision": {"behavior": "deny", "message": reason},
            }
        }
    return {"decision": "block", "reason": reason}


def stop_decision(root: Path, event: dict[str, Any]) -> dict[str, Any] | None:
    if event.get("stop_hook_active"):
        return None
    if not is_harness_workspace(root):
        return None

    session = load_session(root)
    pending = load_pending(root)
    contract = active_contract(root)
    enforce_read_set = bool(
        contract
        and (
            session.get("read_contract_stop_required")
            or session.get("mutating_tool_seen")
            or pending.get("requires_gate_ledger")
        )
    )
    if contract and enforce_read_set:
        missing = missing_reads(root, contract)
        if missing:
            shown = "\n".join(f"- {p}" for p in missing[:12])
            return {
                "decision": "block",
                "reason": (
                    "Read the required files before finalizing "
                    f"`{contract['skill']}`:\n{shown}"
                ),
            }
    if pending.get("requires_gate_ledger"):
        message = str(event.get("last_assistant_message") or "")
        if "Gate ledger" not in message and "NOT_RUN" not in message:
            changed = "\n".join(f"- {p}" for p in pending.get("changed_paths", [])[:12])
            return {
                "decision": "block",
                "reason": (
                    "Sensitive workflow files changed. Add a Gate ledger with "
                    "command, result, reason, and artifacts before finalizing.\n"
                    + changed
                ),
            }
    return None


def additional_context_for_contract(
    contract: dict[str, Any], root: Path, match: dict[str, Any] | None = None
) -> str:
    required = required_existing_files(root, contract)
    actions = contract.get("required_actions", [])
    forbidden = contract.get("forbidden_actions", [])
    detection = ""
    if match:
        detection = (
            f"Detection: {match.get('trigger_type')} trigger `{match.get('trigger')}`; "
            f"intent={match.get('intent_class')}.\n"
        )
    return (
        f"Harness active skill contract: {contract['skill']}\n"
        + detection
        + "Required read set before write actions:\n"
        + "\n".join(f"- {p}" for p in required)
        + "\nRequired actions:\n"
        + "\n".join(f"- {a}" for a in actions)
        + "\nForbidden actions:\n"
        + "\n".join(f"- {a}" for a in forbidden)
        + "\nReport a Gate ledger when contract conditions require one."
    )


def read_hook_event() -> dict[str, Any]:
    try:
        raw = sys.stdin.read()
        return json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        return {}


def emit(data: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(data, ensure_ascii=False))
