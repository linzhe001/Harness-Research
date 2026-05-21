from __future__ import annotations

import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any

CONTRACTS_PATH = Path("schemas/skill_contracts.json")
SLICED_COMMIT_RULE_PATH = ".agents/references/sliced-commit-rule.md"
COMMIT_GUIDANCE_FILES = (SLICED_COMMIT_RULE_PATH,)
RUNTIME_DIR = Path(".harness_hooks")
SESSION_PATH = RUNTIME_DIR / "session.json"
SESSIONS_DIR = RUNTIME_DIR / "sessions"
READ_LEDGER_PATH = RUNTIME_DIR / "read_ledger.json"
READ_LEDGERS_DIR = RUNTIME_DIR / "read_ledgers"
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
    "docs/_views/",
    "docs/_site/",
]
GUARDRAIL_PATH_OWNERS = {
    "harness-maintenance": [
        "tooling/codex_hooks/",
        "schemas/skill_contracts.json",
        "schemas/skill_contracts.schema.json",
        ".agents/skills/",
        ".agents/references/",
        ".claude/Workflow_Guide.md",
        ".claude/skills/",
        ".claude/rules/",
        ".claude/shared/",
        "templates/",
        "workflow_handbook/",
        "tooling/.tests/",
        "tooling/model_api/",
        "AGENTS.md",
        "CLAUDE.md",
        "README.md",
        "AI_AGENT_SETUP.md",
        "docs/Hook_Intent_Detection_Improvement_Plan.md",
        "tooling/codex_hooks/Stage_Permission_Elevation_Guide.md",
    ]
}

ENFORCEMENT_NONE = "none"
ENFORCEMENT_CONTEXT_ONLY = "context_only"
ENFORCEMENT_ACTIVE_READ = "active_read"
ENFORCEMENT_ACTIVE_WRITE = "active_write"

KNOWN_REQUIRED_ACTIONS = {
    "approval_tool_only_after_explicit_human_approval",
    "build_review_packet_or_NOT_RUN",
    "build_docs_site_or_NOT_RUN",
    "build_evidence_preview_index_or_NOT_RUN",
    "changed_line_map",
    "check_docchain_gates_or_NOT_RUN",
    "check_dynamic_context_or_NOT_RUN",
    "check_dynamic_context_wf12_or_NOT_RUN",
    "codebase_map_sync_when_baseline_layout_changes",
    "check_protocol_drift_or_NOT_RUN",
    "claim_boundary_check",
    "codex_review_or_NOT_RUN",
    "collect_review_scope",
    "compile_doc_or_NOT_RUN",
    "compile_protocol_or_NOT_RUN",
    "context_gate_or_NOT_RUN",
    "decision_vocabulary",
    "docchain_gate_when_current_docs_change",
    "docs_site_render_or_NOT_RUN",
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
    "validate_docs_site_or_NOT_RUN",
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
    "edit_source_markdown_during_render",
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
    "html_as_source_of_truth",
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

KNOWN_ARTIFACT_OUTPUT_KINDS = {
    "approved_contract",
    "canonical_state",
    "conclusion_evidence",
    "current_doc",
    "fact_doc",
    "generated_view",
    "guidance",
    "implementation",
    "legacy_compat",
    "operational_scope",
    "release_package",
    "review_trace",
    "tool_trace",
}

READ_COMMAND_RE = re.compile(
    r"\b(cat|sed|nl|rg|grep|head|tail|less|more|git\s+diff|git\s+show)\b"
)
MUTATING_COMMAND_RE = re.compile(
    r"(^|\s)(rm|mv|cp|touch|mkdir|chmod|chown|git\s+add|git\s+commit|git\s+rm)\b|"
    r"(^|\s)(?:\S*/)?(?:python|python\d+(?:\.\d+)*|py)\s+\S*approve_contract\.py\b"
)
MUTATING_TOOL_NAMES = {"apply_patch", "Edit", "Write", "Bash", "shell", "local_shell"}
READ_TOOL_NAMES = {"Read", "View", "Open"}
REVIEW_WRITE_ALLOWED_PATHS = [".agents/state/review_traces/code-review/"]
TOOL_OWNED_WRITE_TOOL_PREFIXES = ("tooling/evidence/", "tooling/auto_iterate/")
TOOL_OWNED_OUTPUT_PATHS_BY_SCRIPT = {
    "tooling/evidence/build_docs_site.py": ["docs/_views/", "docs/_site/"],
    "tooling/evidence/build_evidence_preview_index.py": [
        "docs/_views/evidence_preview_index.json",
    ],
}
EXTERNAL_MODEL_REVIEW_SCRIPTS = {
    "tooling/model_api/agentic_review.py",
    "tooling/model_api/external_chat.py",
}
EXTERNAL_MODEL_REVIEW_WRAPPER = "tooling/model_api/harness_external_review.py"
EXTERNAL_MODEL_REVIEW_OUTPUT_FLAGS = {
    "--meta-json",
    "--output",
    "--request-json",
    "--trace-json",
}
DAILY_CONTEXT_FILES = ("AGENTS.md", "CLAUDE.md")
PATH_TOKEN_RE = re.compile(
    r"(?<![\w.-])(?:[A-Za-z0-9_.-]+[/\\])+[A-Za-z0-9_.@%+=:,~-]+|"
    r"(?<![\w.-])[A-Za-z0-9_.@%+=:,~-]+\."
    r"(?:md|py|json|toml|ya?ml|txt|sh|bash|ts|tsx|js|jsx|css|html|lock|cfg|ini)\b",
    re.IGNORECASE,
)
EXPLICIT_TRIGGER_RE = re.compile(r"^[$/][A-Za-z0-9_-]+$")
WORKFLOW_TRIGGER_RE = re.compile(r"^wf\d+[a-z-]*$", re.IGNORECASE)
WORKFLOW_STAGE_RE = re.compile(r"\bWF\d+[a-z-]*\b", re.IGNORECASE)
WF10_LOOP_ACTION_RE = re.compile(
    r"(?<![A-Za-z0-9_])(?:"
    r"\$iterate|/iterate|iterate|"
    r"plan|code|run|eval|next_round|debug|continue|pivot|abort"
    r")(?![A-Za-z0-9_])|"
    r"(本轮决策|记录为|迭代|运行|评估|计划)",
    re.IGNORECASE,
)
STAGE_LIFECYCLE_RE = re.compile(
    r"\b(?:advance|rollback|enter|transition|stage\s+status|workflow\s+status)\b|"
    r"(进入|推进|回滚|切换|阶段状态|工作流状态|执行)",
    re.IGNORECASE,
)
WORKFLOW_ACTION_RE = re.compile(
    r"\b(?:run|execute|advance|rollback|enter|transition|status|check)\b|"
    r"(运行|执行|进入|推进|回滚|切换|状态|检查)",
    re.IGNORECASE,
)
DECISION_WORDS = {"next_round", "debug", "continue", "pivot", "abort"}
DECISION_WORD_RE = re.compile(
    r"(?<![A-Za-z0-9_-])(?:NEXT_ROUND|DEBUG|CONTINUE|PIVOT|ABORT)"
    r"(?![A-Za-z0-9_-])",
    re.IGNORECASE,
)
DECISION_ACTION_RE = re.compile(
    r"(?:本轮)?决策.{0,12}(?:记录为|设为|改为|写成)|"
    r"(?:记录为|设为|改为|写成).{0,12}(?:NEXT_ROUND|DEBUG|CONTINUE|PIVOT|ABORT)",
    re.IGNORECASE,
)
CONTINUATION_PROMPT_RE = re.compile(
    r"^\s*(?:"
    r"继续(?:吧|执行|处理|修复|审查|检查|review)?|"
    r"接着(?:来|做|执行|处理|修复|审查|检查)?|"
    r"continue|go on|resume|proceed|keep going"
    r")\s*[。.!！?？]*\s*$",
    re.IGNORECASE,
)
QUESTION_OR_DISCUSSION_RE = re.compile(
    r"[?？]|"
    r"(怎么|如何|是否|为什么|为啥|正确吗|合适吗|是什么|作用是什么|区别|关系|"
    r"有没有|应该怎么|能不能|可以吗|可不可以|你觉得|怎么看)|"
    r"\b(?:what|why|how|should|could|can|is\s+this|would\s+it)\b",
    re.IGNORECASE,
)
DESIGN_DISCUSSION_RE = re.compile(
    r"(怎么|如何|是否|为什么|有没有|应该怎么|能不能|可以吗|你觉得|方案).{0,24}"
    r"(完善|优化|修改|改造|设计|实现|选择|判断|路由|触发)|"
    r"(完善|优化|修改|改造|设计|实现|选择|判断|路由|触发).{0,24}"
    r"(怎么|如何|是否|为什么|有没有|应该怎么|能不能|可以吗|你觉得)|"
    r"\b(?:how\s+should|should\s+we|can\s+we|could\s+we|why\s+does)\b",
    re.IGNORECASE,
)
WORKFLOW_QUESTION_RE = re.compile(
    r"(?:WF\d+[a-z-]*|workflow|stage).{0,40}"
    r"(?:正确吗|合适吗|为什么|是什么|关系|区别|是否|怎么|如何|这个|这里)|"
    r"(?:正确吗|合适吗|为什么|是什么|关系|区别|是否|怎么|如何|这个|这里)"
    r".{0,40}(?:WF\d+[a-z-]*|workflow|stage)|"
    r"\bWF\d+[a-z-]*\b\s*(?:->|→|-?>)\s*\bWF\d+[a-z-]*\b|"
    r"\b(?:why|what|how|should|is\s+this)\b.{0,40}\b(?:WF\d+[a-z-]*|workflow|stage)\b",
    re.IGNORECASE,
)
DECISION_QUESTION_RE = re.compile(
    r"(?<![A-Za-z0-9_-])(?:NEXT_ROUND|DEBUG|CONTINUE|PIVOT|ABORT)"
    r"(?![A-Za-z0-9_-]).{0,40}"
    r"(?:区别|是什么|是否|只能|合适|为什么|怎么|如何|关系)|"
    r"(?:区别|是什么|是否|只能|合适|为什么|怎么|如何|关系).{0,40}"
    r"(?<![A-Za-z0-9_-])(?:NEXT_ROUND|DEBUG|CONTINUE|PIVOT|ABORT)"
    r"(?![A-Za-z0-9_-])|"
    r"\b(?:what|why|how|should|is)\b.{0,40}"
    r"(?<![A-Za-z0-9_-])(?:NEXT_ROUND|DEBUG|CONTINUE|PIVOT|ABORT)"
    r"(?![A-Za-z0-9_-])",
    re.IGNORECASE,
)
STRONG_WRITE_REQUEST_RE = re.compile(
    r"(?:帮我|请|直接|开始|继续|现在|按.*方案|根据).{0,32}"
    r"(?:实施|落地|实现|修改|改造|完善|优化|修复|更新|重构|删除|迁移|补|添加|创建|写)|"
    r"(?:apply|implement|modify|edit|patch|write|create|add|fix|refactor|delete|"
    r"migrate|update)\s+(?:the\s+)?(?:file|module|code|hook|contract|schema|"
    r"test|docs?|logic|implementation)|"
    r"\b(?:help\s+me|please|go\s+ahead|directly)\b.{0,40}"
    r"\b(?:implement|modify|edit|patch|write|create|add|fix|refactor|delete|"
    r"migrate|update|improve)\b",
    re.IGNORECASE,
)
WEAK_WRITE_VERB_RE = re.compile(
    r"\b(?:modify|improve|adjust|fix|debug|update|change)\b|"
    r"(完善|优化|调整|修改|改造|改|修复)",
    re.IGNORECASE,
)
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
    r"(?<![A-Za-z0-9_])(?:src|scripts|tests|tooling|configs?|hooks?|"
    r"skill detection|workflow|skills?|function|class|method|module|pytest|"
    r"ruff|py_compile|python|typescript|javascript)(?![A-Za-z0-9_])|"
    r"(代码|函数|类|模块|脚本|测试|钩子|修改代码|写代码)",
    re.IGNORECASE,
)
HARNESS_MAINTENANCE_RE = re.compile(
    r"(?<![A-Za-z0-9_])(?:harness[- ]?maintenance|codex[- ]?hooks?|hooks?|"
    r"hook[- ]?(?:maintenance|detection|trigger|routing|status|trust)|"
    r"skill[- ]?(?:maintenance|contract|detection|routing|trigger|permission)|"
    r"prompt[- ]?(?:routing|trigger|detection|classification)|"
    r"(?:ubiquitous[- ]?language|operator[- ]?handbook|stage[- ]?cards?|"
    r"stage[- ]?card[- ]?generator|workflow[- ]?(?:vocabulary|terms|language)|"
    r"project_glossary)|"
    r"permission[- ]?(?:policy|boundary|elevation|scope|model)|"
    r"tooling/codex_hooks|schemas/skill_contracts(?:\.schema)?\.json|\.agents/skills|"
    r"hook_intent_detection_improvement_plan|hook_intent_detection|intent_detection|"
    r"\.claude/skills)(?![A-Za-z0-9_])|"
    r"hook\s*的?\s*(?:判断|触发|路由|信任|状态)|"
    r"(?:判断|触发|路由|信任|状态).{0,12}hook|"
    r"workflow\s*(?:语言|词汇|术语|路由|触发|维护|阶段|权限)|"
    r"(?:prompt|skill|hook).{0,16}(?:误归|误判|错归|归到|路由|触发)|"
    r"(?:误归|误判|错归|归到).{0,16}(?:code-debug|code-expert|harness-maintenance)|"
    r"(?:权限|提权).{0,8}(?:策略|模型|边界|范围|细化)|"
    r"(?:维护类任务|维护任务|写入面|错误写入面)|"
    r"(?:通用语言|统一语言|术语|关键概念|命名规则|认知负担|阶段卡片|"
    r"工作流语言|工作流词汇)|"
    r"skill\s*(?:触发|路由|权限|限制|合约)|"
    r"技能(?:触发|路由|权限|限制|合约)|钩子",
    re.IGNORECASE,
)
CODE_SEARCH_RE = re.compile(
    r"\b(where|find|search|locate|grep|rg|show|list|inspect|explain|read|look up)\b|"
    r"(在哪|在哪里|位置|找一下|找到|查找|检索|搜索|看一下|查看|解释|说明|是什么|有哪些|列出)",
    re.IGNORECASE,
)
CODE_REVIEW_RE = re.compile(
    r"(?<![A-Za-z0-9_])(?:code[- ]?review|review\s+code|codex\s+review|"
    r"deepseek\s+review|cross[- ]?review|review\s+diff|audit\s+diff)"
    r"(?![A-Za-z0-9_])|"
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
SHELL_CONTROL_RE = re.compile(r"&&|\|\||;|\n|\|")
SHELL_CONTROL_TOKENS = {"&&", "||", ";", "|"}
INLINE_INTERPRETER_FLAGS = {"-c", "-e", "--eval"}
SCRIPTING_EXECUTABLES = {
    "bash",
    "node",
    "nodejs",
    "perl",
    "ruby",
    "sh",
    "zsh",
}


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


def is_question_or_discussion(prompt: str) -> bool:
    return bool(QUESTION_OR_DISCUSSION_RE.search(detection_text(prompt)))


def is_workflow_question(prompt: str) -> bool:
    text = detection_text(prompt)
    return bool(WORKFLOW_STAGE_RE.search(text) and WORKFLOW_QUESTION_RE.search(text))


def is_decision_question(prompt: str) -> bool:
    text = detection_text(prompt)
    return bool(DECISION_WORD_RE.search(text) and DECISION_QUESTION_RE.search(text))


def is_design_discussion(prompt: str) -> bool:
    text = detection_text(prompt)
    if not is_question_or_discussion(prompt):
        return False
    return bool(DESIGN_DISCUSSION_RE.search(text) or WEAK_WRITE_VERB_RE.search(text))


def is_strong_write_request(prompt: str) -> bool:
    text = detection_text(prompt)
    if is_question_or_discussion(prompt) and not STRONG_WRITE_REQUEST_RE.search(text):
        return False
    if STRONG_WRITE_REQUEST_RE.search(text):
        return True
    return bool(CODE_WRITE_RE.search(text) and CODE_TARGET_RE.search(text))


def is_workflow_action(prompt: str) -> bool:
    text = detection_text(prompt)
    if DECISION_ACTION_RE.search(text):
        return True
    if WORKFLOW_STAGE_RE.search(text) and WORKFLOW_ACTION_RE.search(text):
        return True
    return bool(re.search(r"[$/]iterate\b", text, flags=re.IGNORECASE))


def classify_prompt_intent(prompt: str) -> str:
    text = detection_text(prompt)
    if CODE_REVIEW_RE.search(text) and (
        CODE_TARGET_RE.search(text) or REVIEW_TARGET_RE.search(text)
    ):
        return f"code_review_{classify_review_mode(prompt)}"
    if is_decision_question(prompt):
        return "decision_question"
    if is_workflow_question(prompt):
        return "workflow_question"
    if is_design_discussion(prompt):
        return "design_discussion"
    if is_workflow_action(prompt):
        return "workflow_action"
    if is_strong_write_request(prompt):
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


def is_harness_maintenance_prompt(prompt: str) -> bool:
    return bool(
        HARNESS_MAINTENANCE_RE.search(prompt)
        or HARNESS_MAINTENANCE_RE.search(detection_text(prompt))
    )


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
    if "-" in trigger:
        return 2_000 + len(trigger)
    if " " in trigger:
        return 1_000 + len(trigger)
    return 100 + len(trigger)


def _is_explicit_skill_trigger(trigger: str) -> bool:
    return bool(EXPLICIT_TRIGGER_RE.match(trigger))


def _is_decision_trigger(trigger: str) -> bool:
    return trigger.strip().lower() in DECISION_WORDS


def _is_question_safe_intent(intent: str) -> bool:
    return intent in {
        "workflow_question",
        "decision_question",
        "design_discussion",
        "code_search",
    }


def _trigger_is_action_gated(trigger: str) -> bool:
    return bool(WORKFLOW_TRIGGER_RE.match(trigger) or _is_decision_trigger(trigger))


def _trigger_blocked_by_intent(trigger: str, intent: str) -> bool:
    if _is_explicit_skill_trigger(trigger):
        return False
    if _trigger_is_action_gated(trigger) and _is_question_safe_intent(intent):
        return True
    if _is_decision_trigger(trigger) and intent != "workflow_action":
        return True
    if trigger in {"debug", "fix"} and intent == "decision_question":
        return True
    return False


def _is_read_only_prompt(prompt: str) -> bool:
    text = detection_text(prompt)
    return bool(
        re.search(
            r"\b(status|show|explain|read|inspect|check|list)\b|"
            r"(状态|查看|看一下|解释|说明|检查|只读)",
            text,
            flags=re.IGNORECASE,
        )
    )


def _is_iterate_write_action(prompt: str) -> bool:
    text = detection_text(prompt)
    if DECISION_ACTION_RE.search(text):
        return True
    if re.search(r"\biterate\b", text, re.I) and re.search(
        r"\b(?:run|execute)\b|(?:运行|执行)",
        text,
        re.I,
    ):
        return True
    return bool(
        re.search(
            r"(?<![A-Za-z0-9_])(?:plan|code|run|eval)(?![A-Za-z0-9_])|"
            r"(计划|编码|运行|评估|记录为)",
            text,
            flags=re.IGNORECASE,
        )
    )


def _active_match(
    contract: dict[str, Any],
    skill: str,
    trigger: str,
    trigger_type: str,
    intent: str,
    enforcement_mode: str,
    read_contract_stop_required: bool,
) -> dict[str, Any]:
    return {
        "contract": contract,
        "skill": skill,
        "candidate_contract": None,
        "candidate_skill": None,
        "trigger": trigger,
        "trigger_type": trigger_type,
        "intent_class": intent,
        "enforcement_mode": enforcement_mode,
        "read_contract_stop_required": read_contract_stop_required,
    }


def _candidate_match(
    contract: dict[str, Any] | None,
    skill: str | None,
    trigger: str | None,
    trigger_type: str | None,
    intent: str,
    reason: str,
    pending_candidate_activation: bool = False,
) -> dict[str, Any]:
    return {
        "contract": None,
        "skill": None,
        "candidate_contract": contract,
        "candidate_skill": skill,
        "candidate_trigger": trigger,
        "candidate_trigger_type": trigger_type,
        "candidate_reason": reason,
        "trigger": trigger,
        "trigger_type": trigger_type,
        "intent_class": intent,
        "enforcement_mode": ENFORCEMENT_CONTEXT_ONLY
        if skill
        else ENFORCEMENT_NONE,
        "read_contract_stop_required": False,
        "pending_candidate_activation": pending_candidate_activation,
    }


def _enforcement_for_hard_match(skill: str, intent: str, prompt: str) -> str:
    if intent == "code_write":
        return ENFORCEMENT_ACTIVE_WRITE
    if intent == "workflow_action":
        if skill == "iterate":
            return (
                ENFORCEMENT_ACTIVE_WRITE
                if _is_iterate_write_action(prompt)
                else ENFORCEMENT_ACTIVE_READ
            )
        if skill == "orchestrator":
            return ENFORCEMENT_ACTIVE_READ
        return ENFORCEMENT_ACTIVE_WRITE
    if intent.startswith("code_review_"):
        return ENFORCEMENT_ACTIVE_READ
    if _is_read_only_prompt(prompt):
        return ENFORCEMENT_ACTIVE_READ
    return ENFORCEMENT_ACTIVE_READ


def _read_stop_required(
    contract: dict[str, Any],
    trigger_type: str,
    enforcement_mode: str,
) -> bool:
    if enforcement_mode == ENFORCEMENT_ACTIVE_READ:
        return True
    return trigger_type == "explicit" or contract.get("skill") == "code-review"


def _workflow_action_match(
    root: Path,
    prompt: str,
    intent: str,
) -> dict[str, Any] | None:
    if intent != "workflow_action":
        return None
    text = detection_text(prompt)
    if DECISION_ACTION_RE.search(text):
        contract = contract_by_skill(root, "iterate")
        if contract:
            return _active_match(
                contract,
                "iterate",
                "decision_action",
                "action_gated",
                intent,
                ENFORCEMENT_ACTIVE_WRITE,
                False,
            )
    if re.search(r"\bWF0\b|bootstrap\s+init|operator\s+context\s+init", text, re.I):
        contract = contract_by_skill(root, "init-project")
        if contract:
            return _active_match(
                contract,
                "init-project",
                "wf0",
                "explicit",
                intent,
                ENFORCEMENT_ACTIVE_WRITE,
                True,
            )
    if re.search(r"[$/]iterate\b", text, re.I) or (
        re.search(r"\bWF10\b", text, re.I) and WF10_LOOP_ACTION_RE.search(text)
    ):
        contract = contract_by_skill(root, "iterate")
        if contract:
            mode = (
                ENFORCEMENT_ACTIVE_WRITE
                if _is_iterate_write_action(prompt)
                else ENFORCEMENT_ACTIVE_READ
            )
            return _active_match(
                contract,
                "iterate",
                "iterate_action",
                "action_gated",
                intent,
                mode,
                mode == ENFORCEMENT_ACTIVE_READ,
            )
    if WORKFLOW_STAGE_RE.search(text):
        contract = contract_by_skill(root, "orchestrator")
        if contract:
            return _active_match(
                contract,
                "orchestrator",
                "stage_lifecycle",
                "action_gated",
                intent,
                ENFORCEMENT_ACTIVE_READ,
                True,
            )
    return None


def detect_skill_match(root: Path, prompt: str) -> dict[str, Any] | None:
    prompt_l = prompt.lower()
    cleaned_l = detection_text(prompt).lower()
    intent = classify_prompt_intent(prompt)
    explicit_best: tuple[int, dict[str, Any], str] | None = None
    for contract in load_contracts(root):
        for trigger_value in contract.get("triggers", []):
            trigger = str(trigger_value).lower()
            if not _is_explicit_skill_trigger(trigger):
                continue
            if not _trigger_match(prompt_l, trigger):
                continue
            score = _trigger_score(trigger, True)
            if explicit_best is None or score > explicit_best[0]:
                explicit_best = (score, contract, trigger)
    if explicit_best:
        _, contract, trigger = explicit_best
        skill = str(contract.get("skill"))
        mode = _enforcement_for_hard_match(skill, intent, prompt)
        return _active_match(
            contract,
            skill,
            trigger,
            "explicit",
            intent,
            mode,
            _read_stop_required(contract, "explicit", mode),
        )

    workflow_match = _workflow_action_match(root, prompt, intent)
    if workflow_match:
        return workflow_match

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
            if _trigger_blocked_by_intent(trigger, intent):
                continue
            trigger_type = "explicit" if explicit else "implicit"
            score = _trigger_score(trigger, explicit)
            if best is None or score > best[0]:
                best = (score, contract, trigger, trigger_type)
    maintenance_contract = (
        contract_by_skill(root, "harness-maintenance")
        if is_harness_maintenance_prompt(prompt)
        else None
    )
    if best:
        _, contract, trigger, trigger_type = best
        if _is_question_safe_intent(intent) and trigger_type != "explicit":
            candidate_contract = maintenance_contract or contract
            candidate_skill = (
                str(candidate_contract.get("skill")) if candidate_contract else None
            )
            return _candidate_match(
                candidate_contract,
                candidate_skill,
                "inferred_harness_maintenance"
                if maintenance_contract
                else trigger,
                "inferred" if maintenance_contract else trigger_type,
                intent,
                "question or discussion prompt; no hard Skill Contract selected",
            )
        if (
            trigger_type != "explicit"
            and contract.get("skill") in {"code-debug", "code-expert"}
            and maintenance_contract is not None
        ):
            mode = _enforcement_for_hard_match("harness-maintenance", intent, prompt)
            return _active_match(
                maintenance_contract,
                "harness-maintenance",
                "inferred_harness_maintenance",
                "inferred",
                intent,
                mode,
                _read_stop_required(maintenance_contract, "inferred", mode),
            )
        skill = str(contract.get("skill"))
        if (
            trigger_type != "explicit"
            and skill == "harness-maintenance"
            and intent == "code_write"
        ):
            mode = ENFORCEMENT_ACTIVE_WRITE
            return _active_match(
                contract,
                skill,
                "inferred_harness_maintenance",
                "inferred",
                intent,
                mode,
                _read_stop_required(contract, "inferred", mode),
            )
        if trigger_type != "explicit" and intent not in {
            "code_write",
            "workflow_action",
        } and not intent.startswith("code_review_"):
            return None
        mode = _enforcement_for_hard_match(skill, intent, prompt)
        return _active_match(
            contract,
            skill,
            trigger,
            trigger_type,
            intent,
            mode,
            _read_stop_required(contract, trigger_type, mode),
        )

    if intent.startswith("code_review_"):
        contract = contract_by_skill(root, "code-review")
        if contract:
            return _active_match(
                contract,
                "code-review",
                "inferred_code_review",
                "inferred",
                intent,
                ENFORCEMENT_ACTIVE_READ,
                True,
            )
    if intent == "code_write":
        if is_harness_maintenance_prompt(prompt):
            contract = contract_by_skill(root, "harness-maintenance")
            if contract:
                return _active_match(
                    contract,
                    "harness-maintenance",
                    "inferred_harness_maintenance",
                    "inferred",
                    intent,
                    ENFORCEMENT_ACTIVE_WRITE,
                    False,
                )
        create_score = bool(CODE_CREATE_RE.search(detection_text(prompt)))
        modify_score = bool(CODE_MODIFY_RE.search(detection_text(prompt)))
        skill = "code-expert" if create_score and not modify_score else "code-debug"
        contract = contract_by_skill(root, skill)
        if contract:
            return _active_match(
                contract,
                skill,
                "inferred_code_write",
                "inferred",
                intent,
                ENFORCEMENT_ACTIVE_WRITE,
                False,
            )
    if intent == "design_discussion" and maintenance_contract:
        return _candidate_match(
            maintenance_contract,
            "harness-maintenance",
            "inferred_harness_maintenance",
            "inferred",
            intent,
            "question about Harness guardrails; no edit request",
        )
    if intent == "decision_question":
        contract = contract_by_skill(root, "iterate")
        return _candidate_match(
            contract,
            "iterate" if contract else None,
            "decision_vocabulary",
            "action_gated",
            intent,
            "Decision vocabulary question; no WF10 state write requested",
        )
    if intent == "workflow_question":
        contract = contract_by_skill(root, "orchestrator")
        return _candidate_match(
            contract,
            "orchestrator" if contract else None,
            "workflow_question",
            "action_gated",
            intent,
            "workflow stage question; no stage transition requested",
        )
    return None


def detect_skill(root: Path, prompt: str) -> dict[str, Any] | None:
    match = detect_skill_match(root, prompt)
    if not match:
        return None
    contract = match.get("contract")
    return contract if isinstance(contract, dict) else None


def is_continuation_prompt(prompt: str) -> bool:
    if prompt.strip().strip("。.!！?？") == "CONTINUE":
        return False
    return bool(CONTINUATION_PROMPT_RE.match(prompt))


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
        write_scope = contract.get("write_scope")
        if write_scope is None:
            errors.append(f"{skill}: write_scope.allowed_paths is required")
        elif not isinstance(write_scope, dict):
            errors.append(f"{skill}: write_scope must be an object")
        else:
            allowed_paths = write_scope.get("allowed_paths")
            if not isinstance(allowed_paths, list) or not all(
                isinstance(path, str) for path in allowed_paths
            ):
                errors.append(
                    f"{skill}: write_scope.allowed_paths must be a string list"
                )
        artifact_outputs = contract.get("artifact_outputs")
        if not isinstance(artifact_outputs, list) or not artifact_outputs:
            errors.append(f"{skill}: artifact_outputs must be a non-empty list")
        else:
            for index, output in enumerate(artifact_outputs):
                if not isinstance(output, dict):
                    errors.append(f"{skill}: artifact_outputs[{index}] must be object")
                    continue
                kind = output.get("kind")
                if kind not in KNOWN_ARTIFACT_OUTPUT_KINDS:
                    errors.append(
                        f"{skill}: artifact_outputs[{index}].kind is unknown: {kind}"
                    )
                paths = output.get("paths")
                if not isinstance(paths, list) or not all(
                    isinstance(path, str) for path in paths
                ):
                    errors.append(
                        f"{skill}: artifact_outputs[{index}].paths "
                        "must be a string list"
                    )
                    continue
                requires_tool = bool(output.get("requires_tool"))
                if kind == "legacy_compat" and not output.get("replacement"):
                    errors.append(
                        f"{skill}: legacy_compat output must declare replacement"
                    )
                for output_path in paths:
                    if output_path.startswith(".evidence/") and not requires_tool:
                        errors.append(
                            f"{skill}: .evidence output {output_path} "
                            "must set requires_tool=true"
                        )
                    if output_path.startswith(".auto_iterate/") and not requires_tool:
                        errors.append(
                            f"{skill}: .auto_iterate output {output_path} "
                            "must set requires_tool=true"
                        )
                    if (
                        not requires_tool
                        and write_scope is not None
                        and isinstance(write_scope, dict)
                        and not path_pattern_covered_by(
                            output_path,
                            contract_write_scope_paths(contract),
                        )
                    ):
                        errors.append(
                            f"{skill}: artifact output path {output_path} "
                            "is not covered by write_scope.allowed_paths"
                        )
        broad_docs = "docs/" in contract_write_scope_paths(contract)
        if broad_docs and isinstance(artifact_outputs, list):
            has_docs_explanation = any(
                isinstance(output, dict)
                and (
                    output.get("kind") == "operational_scope"
                    or any(
                        isinstance(path, str) and path.startswith("docs/")
                        for path in output.get("paths", [])
                    )
                )
                for output in artifact_outputs
            )
            if not has_docs_explanation:
                errors.append(
                    f"{skill}: broad docs/ write scope needs artifact_outputs "
                    "or operational_scope metadata"
                )
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
    contracts_by_skill = {
        str(contract.get("skill")): contract for contract in load_contracts(root)
    }
    for owner, patterns in GUARDRAIL_PATH_OWNERS.items():
        contract = contracts_by_skill.get(owner)
        if contract is None:
            errors.append(f"{owner}: guardrail owner contract is missing")
            continue
        allowed_paths = contract_write_scope_paths(contract)
        for pattern in patterns:
            if not path_pattern_covered_by(pattern, allowed_paths):
                errors.append(
                    f"{owner}: guardrail path {pattern} is not covered by "
                    "write_scope.allowed_paths"
                )
    return errors


def load_session(root: Path) -> dict[str, Any]:
    return load_json(root / SESSION_PATH, {})


def save_session(root: Path, session: dict[str, Any]) -> None:
    write_json(root / SESSION_PATH, session)
    session_id = session.get("session_id")
    if isinstance(session_id, str) and session_id.strip():
        write_json(root / SESSIONS_DIR / f"{runtime_key(session_id)}.json", session)


def runtime_key(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value.strip()) or "unknown"


def load_session_for_event(root: Path, event: dict[str, Any]) -> dict[str, Any]:
    session_id = event.get("session_id")
    if isinstance(session_id, str) and session_id.strip():
        session = load_json(
            root / SESSIONS_DIR / f"{runtime_key(session_id)}.json",
            None,
        )
        if isinstance(session, dict):
            return session
    return load_session(root)


def load_read_ledger(root: Path) -> dict[str, Any]:
    return load_json(root / READ_LEDGER_PATH, {"reads": {}})


def save_read_ledger(root: Path, ledger: dict[str, Any]) -> None:
    write_json(root / READ_LEDGER_PATH, ledger)


def load_read_ledger_for_event(root: Path, event: dict[str, Any]) -> dict[str, Any]:
    session_id = event.get("session_id")
    if isinstance(session_id, str) and session_id.strip():
        ledger = load_json(
            root / READ_LEDGERS_DIR / f"{runtime_key(session_id)}.json",
            None,
        )
        if isinstance(ledger, dict):
            return ledger
    return load_read_ledger(root)


def save_read_ledger_for_event(
    root: Path,
    event: dict[str, Any],
    ledger: dict[str, Any],
) -> None:
    save_read_ledger(root, ledger)
    session_id = event.get("session_id")
    if isinstance(session_id, str) and session_id.strip():
        write_json(
            root / READ_LEDGERS_DIR / f"{runtime_key(session_id)}.json",
            ledger,
        )


def reset_read_ledger(root: Path, event: dict[str, Any] | None = None) -> None:
    if event is None:
        event = {}
    save_read_ledger(root, {"reads": {}})
    session_id = event.get("session_id")
    if isinstance(session_id, str) and session_id.strip():
        write_json(
            root / READ_LEDGERS_DIR / f"{runtime_key(session_id)}.json",
            {"reads": {}},
        )


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


def clear_pending(root: Path) -> None:
    save_pending(
        root,
        {
            "requires_gate_ledger": False,
            "reasons": [],
            "changed_paths": [],
            "gate_ledger_notice_emitted": False,
        },
    )


def read_tracking_candidates(
    root: Path, contract: dict[str, Any] | None = None
) -> list[str]:
    candidates: list[str] = list(COMMIT_GUIDANCE_FILES)
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


def is_git_commit_command(command: str) -> bool:
    try:
        tokens = _strip_env_assignments(shlex.split(command))
    except ValueError:
        return False
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token in SHELL_CONTROL_TOKENS:
            index += 1
            continue
        if Path(token).name != "git":
            index += 1
            continue
        cursor = index + 1
        while cursor < len(tokens):
            value = tokens[cursor]
            if value in SHELL_CONTROL_TOKENS:
                break
            if value == "commit":
                return True
            if value in {"-c", "-C", "--git-dir", "--work-tree"}:
                cursor += 2
                continue
            if value.startswith("-"):
                cursor += 1
                continue
            break
        index = max(cursor + 1, index + 1)
    return False


def missing_commit_guidance_reads(root: Path, event: dict[str, Any]) -> list[str]:
    ledger = load_read_ledger_for_event(root, event)
    read_paths = set(ledger.get("reads", {}).keys())
    return [
        path
        for path in COMMIT_GUIDANCE_FILES
        if (root / path).is_file() and path not in read_paths
    ]


def record_read(
    root: Path, path: str, event: dict[str, Any], source: str = "tool"
) -> bool:
    full = root / path
    if not full.exists() or not full.is_file():
        return False
    ledger = load_read_ledger_for_event(root, event)
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
    save_read_ledger_for_event(root, event, ledger)
    return is_new_read


def _strip_env_assignments(tokens: list[str]) -> list[str]:
    while tokens and "=" in tokens[0] and not tokens[0].startswith("-"):
        tokens.pop(0)
    return tokens


def _normalize_operand(token: str, root: Path) -> str:
    normalized = rel_path(token, root)
    if normalized.startswith("./"):
        return normalized[2:]
    return normalized


def _content_read_operands(root: Path, command: str) -> set[str]:
    if SHELL_CONTROL_RE.search(command):
        return set()
    try:
        tokens = _strip_env_assignments(shlex.split(command))
    except ValueError:
        return set()
    if not tokens:
        return set()

    executable = Path(tokens[0]).name
    args = tokens[1:]
    operands: list[str] = []
    if executable in {"cat", "nl", "head", "tail", "less", "more"}:
        operands = [token for token in args if not token.startswith("-")]
    elif executable == "sed":
        skip_next = False
        for token in args:
            if skip_next:
                skip_next = False
                continue
            if token in {"-e", "-f"}:
                skip_next = True
                continue
            if token.startswith("-"):
                continue
            candidate = root / _normalize_operand(token, root)
            if candidate.is_file():
                operands.append(token)
    elif executable in {"grep", "rg"}:
        pattern_seen = False
        skip_next = False
        for token in args:
            if skip_next:
                skip_next = False
                continue
            if token in {"-e", "--regexp", "-f", "--file"}:
                skip_next = True
                pattern_seen = True
                continue
            if token.startswith("-"):
                continue
            if not pattern_seen:
                pattern_seen = True
                continue
            operands.append(token)
    elif executable == "git" and args and args[0] in {"diff", "show"}:
        for token in args[1:]:
            if token == "--":
                continue
            if token.startswith("-"):
                continue
            if ":" in token and not (root / token).exists():
                continue
            operands.append(token)

    return {_normalize_operand(token, root) for token in operands}


def record_command_reads(root: Path, command: str, event: dict[str, Any]) -> list[str]:
    if not READ_COMMAND_RE.search(command):
        return []
    session = load_session_for_event(root, event)
    skill = session.get("active_skill")
    contract = None
    if skill:
        contract = contract_by_skill(root, skill)
    operands = _content_read_operands(root, command)
    recorded: list[str] = []
    for path in sorted(read_tracking_candidates(root, contract), key=len, reverse=True):
        if path in operands:
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
    allowed = set(read_tracking_candidates(root, active_contract(root, event)))
    recorded: list[str] = []
    for candidate in candidates:
        rel = rel_path(candidate, root)
        if rel in allowed:
            if record_read(root, rel, event, source=name):
                recorded.append(rel)
    return recorded


def missing_reads(
    root: Path,
    contract: dict[str, Any],
    event: dict[str, Any] | None = None,
) -> list[str]:
    ledger = load_read_ledger_for_event(root, event or {})
    read_paths = set(ledger.get("reads", {}).keys())
    return [
        path
        for path in required_existing_files(root, contract)
        if path not in read_paths
    ]


def active_contract(
    root: Path,
    event: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    session = load_session_for_event(root, event or {})
    skill = session.get("active_skill")
    if not skill:
        return None
    return contract_by_skill(root, skill)


def looks_mutating_bash(command: str) -> bool:
    return bool(MUTATING_COMMAND_RE.search(command)) or has_shell_redirection(command)


def has_shell_redirection(command: str) -> bool:
    quote: str | None = None
    escaped = False
    for index, char in enumerate(command):
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if quote:
            if char == quote:
                quote = None
            continue
        if char in {"'", '"'}:
            quote = char
            continue
        if char == ">":
            previous_char = command[index - 1] if index else ""
            next_char = command[index + 1] if index + 1 < len(command) else ""
            if previous_char == "=" or next_char == "=":
                continue
            return True
    return False


def is_tool_owned_write_tool_command(command: str, root: Path | None = None) -> bool:
    if SHELL_CONTROL_RE.search(command):
        return False
    try:
        tokens = _strip_env_assignments(shlex.split(command))
    except ValueError:
        return False
    if not tokens:
        return False

    executable = Path(tokens[0]).name
    script_index = 1 if _is_python_executable(executable) else 0
    if len(tokens) <= script_index:
        return False
    script = rel_path(tokens[script_index], root or repo_root()).lstrip("./")
    return script.startswith(TOOL_OWNED_WRITE_TOOL_PREFIXES)


def is_untrusted_tool_owned_path_command(
    command: str,
    root: Path | None = None,
) -> bool:
    if is_tool_owned_write_tool_command(command, root):
        return False
    if looks_mutating_bash(command):
        return True
    if SHELL_CONTROL_RE.search(command):
        return False
    try:
        tokens = _strip_env_assignments(shlex.split(command))
    except ValueError:
        return False
    if not tokens:
        return False
    executable = Path(tokens[0]).name
    if _is_python_executable(executable):
        return len(tokens) > 1
    if executable in SCRIPTING_EXECUTABLES:
        return any(token in INLINE_INTERPRETER_FLAGS for token in tokens[1:])
    return False


def is_review_trace_bash_write(root: Path, command: str) -> bool:
    if SHELL_CONTROL_RE.search(command):
        return False
    try:
        tokens = _strip_env_assignments(shlex.split(command))
    except ValueError:
        return False
    if not tokens or Path(tokens[0]).name != "mkdir":
        return False

    targets: list[str] = []
    for token in tokens[1:]:
        if token == "--":
            continue
        if token.startswith("-"):
            continue
        targets.append(rel_path(token, root))
    return bool(targets) and all(
        path_matches_any(target, REVIEW_WRITE_ALLOWED_PATHS)
        for target in targets
    )


def _is_python_executable(executable: str) -> bool:
    return bool(re.fullmatch(r"python(?:\d+(?:\.\d+)*)?|py", executable))


def python_script_from_command(root: Path, command: str) -> str | None:
    if SHELL_CONTROL_RE.search(command):
        return None
    try:
        tokens = _strip_env_assignments(shlex.split(command))
    except ValueError:
        return None
    if len(tokens) < 2:
        return None
    executable = Path(tokens[0]).name
    if not _is_python_executable(executable):
        return None
    return rel_path(tokens[1], root).lstrip("./")


def is_direct_external_review_command(root: Path, command: str) -> bool:
    return python_script_from_command(root, command) in EXTERNAL_MODEL_REVIEW_SCRIPTS


def is_external_review_wrapper_command(root: Path, command: str) -> bool:
    return python_script_from_command(root, command) == EXTERNAL_MODEL_REVIEW_WRAPPER


def external_review_output_paths(root: Path, command: str) -> list[str]:
    if not is_external_review_wrapper_command(root, command):
        return []
    try:
        tokens = shlex.split(command)
    except ValueError:
        return ["<invalid external review command>"]

    paths: list[str] = []
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token in EXTERNAL_MODEL_REVIEW_OUTPUT_FLAGS:
            if index + 1 < len(tokens):
                paths.append(rel_path(tokens[index + 1], root))
            else:
                paths.append(f"<missing value for {token}>")
            index += 2
            continue
        for flag in EXTERNAL_MODEL_REVIEW_OUTPUT_FLAGS:
            if token.startswith(f"{flag}="):
                paths.append(rel_path(token.split("=", 1)[1], root))
                break
        index += 1
    return paths


def external_review_session_allowed(
    root: Path,
    event: dict[str, Any] | None = None,
) -> bool:
    session = load_session_for_event(root, event or {})
    return (
        session.get("active_skill") == "code-review"
        and session.get("intent_class") == "code_review_heavy"
    )


def is_mutating_tool_event(event: dict[str, Any], root: Path | None = None) -> bool:
    name = normalize_tool_name(tool_name(event))
    command = tool_text(event)
    workspace = root or repo_root()
    return name in {"apply_patch", "Edit", "Write"} or (
        name == "Bash"
        and (
            looks_mutating_bash(command)
            or bool(external_review_output_paths(workspace, command))
            or bool(tool_owned_output_paths(workspace, command))
        )
    )


def tool_owned_output_paths(root: Path, command: str) -> list[str]:
    script = python_script_from_command(root, command)
    if not script:
        return []
    return list(TOOL_OWNED_OUTPUT_PATHS_BY_SCRIPT.get(script, []))


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
    elif name == "Bash":
        wrapper_outputs = external_review_output_paths(root, command)
        tool_outputs = tool_owned_output_paths(root, command)
        if wrapper_outputs:
            paths.extend(wrapper_outputs)
            if looks_mutating_bash(command):
                paths.append("<bash mutation>")
        elif tool_outputs:
            paths.extend(tool_outputs)
            if looks_mutating_bash(command):
                paths.append("<bash mutation>")
        elif looks_mutating_bash(command):
            if is_review_trace_bash_write(root, command):
                paths.extend(REVIEW_WRITE_ALLOWED_PATHS)
            else:
                paths.append("<bash mutation>")
    return paths


def mark_tool_activity(root: Path, event: dict[str, Any]) -> dict[str, Any]:
    session = load_session_for_event(root, event)
    if not is_harness_workspace(root):
        return session
    if is_mutating_tool_event(event, root):
        session["mutating_tool_seen"] = True
        session["last_mutating_tool"] = normalize_tool_name(tool_name(event))
        session["last_mutating_turn_id"] = event.get("turn_id")
        save_session(root, session)
    return session


def changed_paths(root: Path) -> list[str]:
    paths: list[str] = []
    commands = [
        ["git", "diff", "--name-only"],
        ["git", "diff", "--cached", "--name-only"],
        ["git", "ls-files", "--others", "--exclude-standard"],
    ]
    for command in commands:
        paths.extend(_git_changed_paths(root, command))
    return sorted(dict.fromkeys(paths))


def _git_changed_paths(root: Path, command: list[str]) -> list[str]:
    try:
        result = subprocess.run(
            command,
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


def path_pattern_covered_by(pattern: str, allowed_paths: list[str]) -> bool:
    if path_matches_any(pattern.rstrip("/"), allowed_paths):
        return True
    if not pattern.endswith("/"):
        return False
    for allowed in allowed_paths:
        if allowed.endswith("/") and pattern.startswith(allowed):
            return True
        if allowed == pattern.rstrip("/"):
            return True
    return False


def is_synthetic_mutation_path(path: str) -> bool:
    return path.startswith("<") and path.endswith(">")


def contract_write_scope_paths(contract: dict[str, Any]) -> list[str]:
    scope = contract.get("write_scope")
    if isinstance(scope, dict):
        paths = scope.get("allowed_paths")
        if isinstance(paths, list):
            return [str(path) for path in paths]
    return []


def guardrail_owner_skills_for_paths(root: Path, paths: list[str]) -> set[str]:
    owners: set[str] = set()
    for skill, patterns in GUARDRAIL_PATH_OWNERS.items():
        for path in paths:
            if not is_synthetic_mutation_path(path) and path_matches_any(
                path,
                patterns,
            ):
                owners.add(skill)
    return owners


def command_mentions_guardrail_path(command: str) -> set[str]:
    owners: set[str] = set()
    for skill, patterns in GUARDRAIL_PATH_OWNERS.items():
        for pattern in patterns:
            token = pattern.rstrip("/")
            if token and token in command:
                owners.add(skill)
    return owners


def workflow_owner_skills_for_paths(root: Path, paths: list[str]) -> set[str]:
    owners: set[str] = set()
    for contract in load_contracts(root):
        skill = str(contract.get("skill", ""))
        allowed_paths = contract_write_scope_paths(contract)
        for path in paths:
            if not is_synthetic_mutation_path(path) and path_matches_any(
                path,
                allowed_paths,
            ):
                owners.add(skill)
    return owners


def no_contract_write_block_reason(
    root: Path,
    event: dict[str, Any],
    paths: list[str],
) -> str | None:
    command = tool_text(event)
    guardrail_owners = guardrail_owner_skills_for_paths(root, paths)
    if normalize_tool_name(tool_name(event)) == "Bash":
        guardrail_owners.update(command_mentions_guardrail_path(command))
    if guardrail_owners:
        owners = ", ".join(f"`{owner}`" for owner in sorted(guardrail_owners))
        shown = "\n".join(f"- {p}" for p in paths[:12]) or "- <bash mutation>"
        return (
            "Blocked by Harness policy: this write targets guardrail-sensitive "
            "paths and requires an explicit hard Skill Contract before retrying. "
            f"Activate {owners}, complete its Read Contract, then retry.\n"
            f"Attempted paths:\n{shown}"
        )

    workflow_owners = workflow_owner_skills_for_paths(root, paths)
    if workflow_owners:
        owners = ", ".join(f"`{owner}`" for owner in sorted(workflow_owners)[:8])
        shown = "\n".join(f"- {p}" for p in paths[:12])
        return (
            "Blocked by Harness policy: this path is owned by a workflow "
            "Skill Contract, but no hard active skill is selected. Activate the "
            "correct Skill/Stage and complete required reads before writing.\n"
            f"Possible owners: {owners}\nAttempted paths:\n{shown}"
        )
    return None


def write_scope_violations(
    contract: dict[str, Any], paths: list[str]
) -> list[str]:
    allowed_paths = contract_write_scope_paths(contract)
    if not allowed_paths:
        return [path for path in paths if not is_synthetic_mutation_path(path)]
    return [
        path
        for path in paths
        if not is_synthetic_mutation_path(path)
        and not path_matches_any(path, allowed_paths)
    ]


def is_local_code_review_trace_path(path: str) -> bool:
    return path_matches_any(path, REVIEW_WRITE_ALLOWED_PATHS)


def is_code_review_audit_write_event(
    root: Path,
    event: dict[str, Any],
    contract: dict[str, Any] | None,
) -> bool:
    if not contract or contract.get("skill") != "code-review":
        return False
    if not is_mutating_tool_event(event, root):
        return False
    paths = mutating_event_paths(root, event)
    return bool(paths) and all(is_local_code_review_trace_path(path) for path in paths)


def mark_pending_for_changes(root: Path, event: dict[str, Any]) -> dict[str, Any]:
    pending = load_pending(root)
    if not is_harness_workspace(root):
        return pending

    contract = active_contract(root, event)
    if is_code_review_audit_write_event(root, event, contract):
        save_pending(root, pending)
        return pending

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
    touched = [
        p
        for p in paths
        if path_matches_any(p, sensitive) and not is_local_code_review_trace_path(p)
    ]
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


def has_gate_ledger(message: str) -> bool:
    if not re.search(r"\bgate ledger\b", message, flags=re.IGNORECASE):
        return False
    lowered = message.lower()
    required = ("command", "result", "reason", "artifact")
    return all(re.search(rf"\b{field}s?\b", lowered) for field in required)


def block_pre_tool(root: Path, event: dict[str, Any]) -> str | None:
    if not is_harness_workspace(root):
        return None

    name = normalize_tool_name(tool_name(event))
    command = tool_text(event)

    if name == "Bash":
        if is_git_commit_command(command):
            missing_commit_reads = missing_commit_guidance_reads(root, event)
            if missing_commit_reads:
                shown = "\n".join(f"- {p}" for p in missing_commit_reads[:12])
                return (
                    "Blocked by Harness policy: read sliced commit guidance "
                    "before `git commit`, then identify independent Commit "
                    "Slices and commit one completed slice at a time.\n"
                    f"{shown}"
                )
        if is_direct_external_review_command(root, command):
            return (
                "Blocked by Harness policy: external model review must run "
                "through `tooling/model_api/harness_external_review.py` so "
                "network approval is scoped to `$code-review heavy`."
            )
        if is_external_review_wrapper_command(
            root, command
        ) and not external_review_session_allowed(root, event):
            return (
                "Blocked by Harness policy: the external review wrapper is "
                "allowed only during an active `$code-review heavy` session."
            )
        for pattern in IGNORE_GIT_ADD_PATTERNS:
            if re.search(r"\bgit\s+add\b", command) and pattern in command:
                return (
                    "Blocked by Harness policy: do not add local/reference "
                    f"artifact `{pattern}` to git."
                )
        if any(path in command for path in DIRECT_TOOL_OWNED_PATHS):
            if is_untrusted_tool_owned_path_command(command, root):
                return (
                    "Blocked by Harness policy: .evidence/**, "
                    ".auto_iterate/**, docs/_views/**, and docs/_site/** "
                    "are tool/controller-owned paths."
                )

    if name == "apply_patch":
        patch_text = command
        if any(
            f"*** Update File: {p}" in patch_text
            or f"*** Add File: {p}" in patch_text
            or f"*** Delete File: {p}" in patch_text
            for p in DIRECT_TOOL_OWNED_PATHS
        ):
            return (
                "Blocked by Harness policy: do not manually patch "
                ".evidence/**, .auto_iterate/**, docs/_views/**, or "
                "docs/_site/**."
            )

    if name in {"Edit", "Write"}:
        tool_owned_paths = [
            path
            for path in mutating_event_paths(root, event)
            if path_matches_any(path, DIRECT_TOOL_OWNED_PATHS)
        ]
        if tool_owned_paths:
            shown = "\n".join(f"- {p}" for p in tool_owned_paths[:12])
            return (
                "Blocked by Harness policy: do not manually edit or write "
                ".evidence/**, .auto_iterate/**, docs/_views/**, or "
                "docs/_site/**.\n"
                f"{shown}"
            )

    contract = active_contract(root, event)
    is_mutating_tool = is_mutating_tool_event(event, root)
    if contract and is_mutating_tool:
        session = load_session_for_event(root, event)
        mode = session.get("enforcement_mode") or ENFORCEMENT_ACTIVE_WRITE
        paths = mutating_event_paths(root, event)
        if mode == ENFORCEMENT_ACTIVE_READ:
            if contract.get("skill") == "code-review" and paths and all(
                path_matches_any(path, REVIEW_WRITE_ALLOWED_PATHS) for path in paths
            ):
                missing = missing_reads(root, contract, event)
                if missing:
                    shown = "\n".join(f"- {p}" for p in missing[:12])
                    return (
                        "Required read set is incomplete before read-mode "
                        f"artifact writes for `{contract['skill']}`:\n{shown}"
                    )
            else:
                shown = "\n".join(f"- {p}" for p in paths[:12]) or "- <write>"
                return (
                    "Blocked by Harness policy: the active "
                    f"`{contract['skill']}` contract is in active_read mode. "
                    "Read-only/status sessions may only write declared "
                    "read-mode artifacts.\n"
                    f"Attempted paths:\n{shown}"
                )
        else:
            missing = missing_reads(root, contract, event)
            if missing:
                shown = "\n".join(f"- {p}" for p in missing[:12])
                return (
                    "Required read set is incomplete before write actions for "
                    f"`{contract['skill']}`:\n{shown}"
                )
        if contract.get("skill") == "code-review":
            disallowed = [
                p for p in paths if not path_matches_any(p, REVIEW_WRITE_ALLOWED_PATHS)
            ]
            if disallowed:
                shown = "\n".join(f"- {p}" for p in disallowed[:12])
                return (
                    "Blocked by Harness policy: `code-review` is review-only. "
                    "Write review artifacts only under "
                    "`.agents/state/review_traces/code-review/` and route fixes "
                    f"through `$code-debug` or `$harness-maintenance`.\n{shown}"
                )
        violations = write_scope_violations(contract, mutating_event_paths(root, event))
        if violations:
            shown = "\n".join(f"- {p}" for p in violations[:12])
            allowed = "\n".join(
                f"- {p}" for p in contract_write_scope_paths(contract)[:12]
            )
            return (
                "Blocked by Harness policy: write is outside the active "
                f"`{contract['skill']}` stage write scope.\n"
                f"Attempted paths:\n{shown}\nAllowed paths:\n{allowed}"
            )
    elif is_mutating_tool:
        if name == "Bash" and is_tool_owned_write_tool_command(command, root):
            paths = mutating_event_paths(root, event)
            if any(
                path_matches_any(path, ["docs/_views/", "docs/_site/"])
                for path in paths
            ):
                shown = "\n".join(f"- {p}" for p in paths[:12])
                return (
                    "Blocked by Harness policy: docs-site renderer output "
                    "requires an active `$docs-site` or owning stage Skill "
                    "Contract with completed required reads.\n"
                    f"Attempted paths:\n{shown}"
                )
            return None
        paths = mutating_event_paths(root, event)
        reason = no_contract_write_block_reason(root, event, paths)
        if reason:
            return reason
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

    session = load_session_for_event(root, event)
    pending = load_pending(root)
    contract = active_contract(root, event)
    enforce_read_set = bool(
        contract
        and (
            session.get("read_contract_stop_required")
            or session.get("mutating_tool_seen")
            or pending.get("requires_gate_ledger")
        )
    )
    if contract and enforce_read_set:
        missing = missing_reads(root, contract, event)
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
        if not has_gate_ledger(message):
            changed = "\n".join(f"- {p}" for p in pending.get("changed_paths", [])[:12])
            return {
                "decision": "block",
                "reason": (
                    "Sensitive workflow files changed. Add a Gate ledger with "
                    "command, result, reason, and artifacts before finalizing.\n"
                    + changed
                ),
            }
        clear_pending(root)
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
        + "Enforcement mode: "
        + f"{match.get('enforcement_mode') if match else 'unknown'}.\n"
        + "Required read set before write actions:\n"
        + "\n".join(f"- {p}" for p in required)
        + "\nRequired actions:\n"
        + "\n".join(f"- {a}" for a in actions)
        + "\nForbidden actions:\n"
        + "\n".join(f"- {a}" for a in forbidden)
        + "\nReport a Gate ledger when contract conditions require one."
    )


def additional_context_for_candidate(
    contract: dict[str, Any],
    match: dict[str, Any] | None = None,
) -> str:
    reason = ""
    if match and match.get("candidate_reason"):
        reason = f"Reason: {match.get('candidate_reason')}.\n"
    trigger = ""
    if match:
        trigger_type = match.get("candidate_trigger_type") or match.get(
            "trigger_type"
        )
        trigger_value = match.get("candidate_trigger") or match.get("trigger")
        trigger = (
            f"Detection: advisory {trigger_type} "
            f"trigger `{trigger_value}`; "
            f"intent={match.get('intent_class')}.\n"
        )
    return (
        f"Harness advisory skill context: {contract['skill']}\n"
        + trigger
        + reason
        + "This is context only. It does not grant Write Scope. "
        "Use an explicit hard Skill Contract before writing guardrail or "
        "workflow paths."
    )


def read_hook_event() -> dict[str, Any]:
    try:
        raw = sys.stdin.read()
        return json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        return {}


def emit(data: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(data, ensure_ascii=False))
