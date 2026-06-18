"""Runtime adapter: brief building, prompt rendering, Codex invocation,
timeout supervision, and heartbeat worker.

The runtime adapter is responsible for:
1. Building a round brief JSON from controller state.
2. Rendering a phase-specific prompt for Codex stdin.
3. Launching ``codex exec`` as a subprocess with timeout.
4. Collecting stdout/stderr/exit-code into a result JSON.

The adapter does NOT:
- Write ``.auto_iterate/state.json`` or ``iteration_log.json``.
- Judge repository postconditions.

See ``02_controller_runtime_plan.md`` §2.5 for the frozen invocation
contract and ``01_contract_freeze.md`` §6–7 for brief/result schemas.
"""

from __future__ import annotations

import importlib.util
import json
import os
import re
import subprocess
import threading
import time
from pathlib import Path
from typing import Any

import tomllib

from .events import iso_now
from .state import atomic_write_json, validate_schema_version

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VALID_PHASE_KEYS = {
    "plan",
    "code",
    "run_screening",
    "run_full",
    "eval",
    "debug",
    "compare",
    "ablate",
    "register",
    "promote",
    "discard",
    "stop",
}
VALID_RUN_TYPES = {"screening", "full", None}
VALID_RECOVERY_MODES = {"normal", "retry", "resume"}

RUNTIME_EXIT_CLASSES = {
    "success",
    "quota_or_rate_limit",
    "auth_failure",
    "interactive_block",
    "timeout",
    "interrupted",
    "internal_error",
}

# Phase-key to phase-family mapping.
PHASE_FAMILY = {
    "plan": "plan",
    "code": "code",
    "run_screening": "run",
    "run_full": "run",
    "eval": "eval",
    "debug": "debug",
    "compare": "analyze",
    "ablate": "run",
    "register": "run",
    "promote": "code",
    "discard": "control",
    "stop": "control",
}

_GPU_VISIBLE_PHASES = {"run_screening", "run_full"}
_HOST_ACCESS_PHASES = {"code", "promote"}
_WATCHDOG_PHASES = {"run_screening", "run_full", "eval"}
_WATCHDOG_POLICY_ENABLED = "status_json_only"
_TOOLING_DIR = Path(__file__).resolve().parents[3]
_WATCHDOG_PATH = _TOOLING_DIR / "run_health" / "watchdog.py"
_QUOTA_OR_RATE_LIMIT_PATTERNS = (
    re.compile(r"you(?:'ve| have) hit your usage limit", re.IGNORECASE),
    re.compile(r"hit your usage limit", re.IGNORECASE),
    re.compile(r"usage limit exceeded", re.IGNORECASE),
    re.compile(r"rate limit exceeded", re.IGNORECASE),
    re.compile(r"quota exceeded", re.IGNORECASE),
    re.compile(r"too many requests", re.IGNORECASE),
    re.compile(r"\b429\b.*(?:too many requests|rate limit|quota)", re.IGNORECASE),
)
_AUTH_FAILURE_PATTERNS = (
    re.compile(r"auth(?:entication)? failure", re.IGNORECASE),
    re.compile(r"unauthorized", re.IGNORECASE),
    re.compile(r"invalid api key", re.IGNORECASE),
    re.compile(r"please run codex login", re.IGNORECASE),
    re.compile(r"\b401\b"),
)

_WATCHDOG_MODULE: Any | None = None


# ---------------------------------------------------------------------------
# Brief validation
# ---------------------------------------------------------------------------

class BriefValidationError(Exception):
    """The round brief is malformed or inconsistent."""


def validate_brief(brief: dict[str, Any]) -> None:
    """Raise ``BriefValidationError`` if the brief is invalid."""
    validate_schema_version(brief, label="brief")

    pk = brief.get("phase_key")
    if pk not in VALID_PHASE_KEYS:
        raise BriefValidationError(f"Invalid phase_key: {pk!r}")

    rt = brief.get("run_type")
    if rt not in VALID_RUN_TYPES:
        raise BriefValidationError(f"Invalid run_type: {rt!r}")

    # Consistency: phase_key vs run_type.
    if pk == "run_screening" and rt != "screening":
        raise BriefValidationError(
            f"phase_key=run_screening requires run_type=screening, got {rt!r}"
        )
    if pk == "run_full" and rt != "full":
        raise BriefValidationError(
            f"phase_key=run_full requires run_type=full, got {rt!r}"
        )
    if pk not in ("run_screening", "run_full") and rt is not None:
        raise BriefValidationError(
            f"phase_key={pk} should have run_type=null, got {rt!r}"
        )

    rm = brief.get("recovery_mode")
    if rm not in VALID_RECOVERY_MODES:
        raise BriefValidationError(f"Invalid recovery_mode: {rm!r}")


def _load_watchdog_module() -> Any:
    """Load the notification-free run health watchdog implementation."""
    global _WATCHDOG_MODULE
    if _WATCHDOG_MODULE is not None:
        return _WATCHDOG_MODULE
    spec = importlib.util.spec_from_file_location(
        "harness_run_health_watchdog",
        _WATCHDOG_PATH,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load watchdog module from {_WATCHDOG_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    _WATCHDOG_MODULE = module
    return module


def _watchdog_enabled(brief: dict[str, Any]) -> bool:
    if brief.get("phase_key") not in _WATCHDOG_PHASES:
        return False
    policy = brief.get("automation_policy")
    if not isinstance(policy, dict):
        return False
    return policy.get("watchdog_policy") == _WATCHDOG_POLICY_ENABLED


def _safe_watchdog_name(value: str) -> str:
    name = re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("._-")
    return name or "auto_iterate_phase"


# ---------------------------------------------------------------------------
# Brief builder
# ---------------------------------------------------------------------------

def build_brief(
    state: dict[str, Any],
    phase_key: str,
    *,
    recovery_mode: str = "normal",
    round_type: str = "ordinary",
    recent_lessons: list[str] | None = None,
    failed_hypotheses: list[str] | None = None,
) -> dict[str, Any]:
    """Construct a round brief JSON from the controller state."""
    run_type: str | None = None
    if phase_key == "run_screening":
        run_type = "screening"
    elif phase_key == "run_full":
        run_type = "full"

    budget = state.get("budget", {})
    llm = state.get("llm_budget", {})
    obj = state.get("objective", {})
    best = state.get("best", {})
    sp = state.get(
        "screening_policy",
        state.get("_policy", {}).get("screening_policy", {}),
    )
    timeouts = state.get(
        "timeouts",
        state.get(
            "_policy",
            {},
        ).get(
            "timeouts",
            {
                "plan": 1800,
                "code": 3600,
                "run_screening": 14400,
                "run_full": 28800,
                "eval": 1800,
                "debug": 3600,
                "compare": 1800,
                "ablate": 3600,
                "register": 1200,
                "promote": 3600,
                "discard": 900,
                "stop": 300,
            },
        ),
    )

    brief: dict[str, Any] = {
        "schema_version": 1,
        "loop_id": state.get("loop_id", ""),
        "round_index": state.get("current_round_index", 0),
        "phase_family": PHASE_FAMILY.get(phase_key, phase_key),
        "phase_key": phase_key,
        "run_type": run_type,
        "tool": state.get("tool", "codex"),
        "auto_mode": True,
        "recovery_mode": recovery_mode,
        "round_type": round_type,
        "objective": obj,
        "current_best": {
            "iteration_id": best.get("iteration_id"),
            "primary_metric": best.get("primary_metric"),
        },
        "initial_hypotheses": state.get("initial_hypotheses", []),
        "forbidden_directions": state.get("forbidden_directions", []),
        "automation_policy": state.get("automation_policy", {}),
        "assurance_axes": state.get("assurance_axes", []),
        "recent_lessons": recent_lessons or [],
        "failed_hypotheses": failed_hypotheses or [],
        "budget_status": {
            "completed_rounds": budget.get("completed_rounds", 0),
            "max_rounds": budget.get("max_rounds", 0),
            "used_gpu_hours": budget.get("used_gpu_hours", 0),
            "max_gpu_hours": budget.get("max_gpu_hours", 0),
            "used_llm_calls": llm.get("used_calls", 0),
            "max_llm_calls": llm.get("max_calls", 0),
        },
        "screening_policy": sp if isinstance(sp, dict) else {},
        "timeouts": timeouts if isinstance(timeouts, dict) else {},
    }
    return brief


# ---------------------------------------------------------------------------
# Prompt renderer
# ---------------------------------------------------------------------------

_PROMPT_TEMPLATES: dict[str, str] = {
    "plan": (
        "You are in auto_mode. Execute `$iterate plan` for the current research loop.\n"
        "\n"
        "Round {round_index} of {max_rounds}. Phase: plan.\n"
        "Objective: {metric_name} {direction} (target: {target}).\n"
        "Current best: {best_metric} (iteration {best_iter}).\n"
        "\n"
        "Recent lessons:\n{lessons}\n"
        "\n"
        "Failed hypotheses:\n{failed}\n"
        "\n"
        "Seed hypotheses from the active goal:\n{initial_hypotheses}\n"
        "\n"
        "Forbidden directions:\n{forbidden_directions}\n"
        "\n"
        "Assurance axes:\n{assurance_axes}\n"
        "\n"
        "Automation policy:\n{automation_policy}\n"
        "\n"
        "IMPORTANT:\n"
        "- auto_mode=true: do NOT ask for user confirmation.\n"
        "- Prefer seed hypotheses when they are still viable.\n"
        "- Do not propose any plan that violates a forbidden direction.\n"
        "- Select and record one assurance_axis for the iteration.\n"
        "- Check docs/40_iterations/Experiment_Queue.md when present and "
        "consume one queued item or explain why another hypothesis is higher "
        "priority.\n"
        "- Write exactly 1 new iteration entry with status=planned.\n"
        "- Include id, date, hypothesis, changes_summary, status=planned, "
        "config_diff object, screening.recommended boolean, and codex_review.\n"
        "- iteration_log.json is the source of truth.\n"
    ),
    "code": (
        "You are in auto_mode. Execute `$iterate code` for iteration {iteration_id}.\n"
        "\n"
        "Phase: code. Implement the planned changes.\n"
        "\n"
        "IMPORTANT:\n"
        "- auto_mode=true: do NOT ask for user confirmation.\n"
        "- Create an automatic commit checkpoint with the slice or experiment "
        "validation profile.\n"
        "- Update iteration status to ready_to_run with git_commit and git_message.\n"
        "- Update action_state.last_action=code and action_state.next_action "
        "to the next concrete action.\n"
        "- Keep implementation.scope, implementation.touched_paths, and the "
        "run code manifest current.\n"
        "- Use $code-debug for actual code modifications.\n"
    ),
    "run_screening": (
        "You are in auto_mode. Execute `$iterate run` "
        "(screening mode) for iteration {iteration_id}.\n"
        "\n"
        "Phase: run_screening. Run the planned screening command for the "
        "active iteration.\n"
        "\n"
        "IMPORTANT:\n"
        "- auto_mode=true: do NOT ask for user confirmation.\n"
        "- Read iteration_log.json for iteration {iteration_id} before choosing "
        "a command.\n"
        "- If config_diff.planned_command exists, run that exact command; do "
        "not substitute a generic training dry-run or training smoke command.\n"
        "- Before launching the planned command, create or verify a Semantic "
        "Execution Commit covering stable code, eval logic used by the "
        "command, durable configs, and run-local code/configs under "
        "runs/wf10/{iteration_id}/. Record the hash as pre_train_commit.\n"
        "- Before running config_diff.planned_command, check any "
        "config_diff.run_local_config path and any --config path in the "
        "planned command. If the path is missing and config_diff contains "
        "base_config plus overrides, materialize the run-local config first; "
        "otherwise record a planned_command_not_runnable failure without "
        "launching an unrelated command.\n"
        "- If the planned command is not runnable, set screening.status=failed "
        "and record the failed planned command in screening.run_manifest.\n"
        "- Update screening.status to passed|failed|skipped.\n"
        "- Set iteration status to ready_to_eval when screening should be "
        "evaluated next, or keep ready_to_run/running only if a full run is "
        "the next action.\n"
        "- Update action_state.last_action=run_screening and "
        "action_state.next_action to run_full, eval, debug, compare, or stop.\n"
        "- When screening.status is passed or failed, record screening.metrics.\n"
        "- When screening.status is passed or failed, record "
        "screening.run_manifest with artifact_contract_version, "
        "run_type=screening, command, exp_dir, git_commit, "
        "pre_train_commit, resolved_config_path, stdout_log_path, "
        "git_snapshot_path, run_local_code_manifest_path when present, and "
        "eval_artifact_paths for the screening run.\n"
        "- Mirror the same screening bundle in top-level run_manifest until "
        "a full run replaces it.\n"
        "- Screening threshold: {threshold_pct}% of baseline.\n"
    ),
    "run_full": (
        "You are in auto_mode. Execute `$iterate run` "
        "(full training) for iteration {iteration_id}.\n"
        "\n"
        "Phase: run_full. Run the complete training.\n"
        "\n"
        "IMPORTANT:\n"
        "- auto_mode=true: do NOT ask for user confirmation.\n"
        "- Before launching the full command, create or verify a Semantic "
        "Execution Commit covering stable code, eval logic used by the "
        "command, durable configs, and run-local code/configs under "
        "runs/wf10/{iteration_id}/. Record the hash as pre_train_commit.\n"
        "- Update full_run.status to completed|recoverable_failed|failed.\n"
        "- Set iteration status to ready_to_eval for completed or terminal "
        "failed full runs; use needs_debug for recoverable implementation or "
        "runtime failures.\n"
        "- Update action_state.last_action=run_full and action_state.next_action "
        "to eval, debug, compare, promote, discard, or stop.\n"
        "- Record metrics in full_run.metrics.\n"
        "- Preserve any screening bundle in screening.run_manifest before "
        "overwriting top-level run_manifest.\n"
        "- Record top-level run_manifest with artifact_contract_version, "
        "run_type=full, command, exp_dir, git_commit, pre_train_commit, "
        "resolved_config_path, stdout_log_path, git_snapshot_path, "
        "run_local_code_manifest_path when present, and eval_artifact_paths "
        "for the full run.\n"
    ),
    "eval": (
        "You are in auto_mode. Execute `$iterate eval` for iteration {iteration_id}.\n"
        "\n"
        "Phase: eval. Analyze results and make a decision.\n"
        "Objective: {metric_name} {direction} (target: {target}).\n"
        "Current best: {best_metric} (iteration {best_iter}).\n"
        "\n"
        "IMPORTANT:\n"
        "- auto_mode=true: do NOT ask for user confirmation.\n"
        "- Before using metric output as Conclusion Evidence, create or verify "
        "pre_eval_commit. If eval logic, eval configs, run-local eval helpers, "
        "claim-support docs, and release-validation code are unchanged since "
        "pre_train_commit, record pre_eval_commit_NOT_CHANGED.\n"
        "- Decision must be exactly ONE of: NEXT_ROUND, DEBUG, CONTINUE, "
        "PIVOT, ABORT.\n"
        "  - NEXT_ROUND: ordinary improvement, continue loop.\n"
        "  - DEBUG: bug/stability issue, continue with debug focus.\n"
        "  - CONTINUE: target met or ready for WF11 handoff.\n"
        "  - PIVOT: fundamental approach change needed.\n"
        "  - ABORT: terminate this research direction.\n"
        "- Record at least 1 lesson.\n"
        "- Preserve git_commit, the final top-level run_manifest artifact "
        "bundle, pre_train_commit, pre_eval_commit or "
        "pre_eval_commit_NOT_CHANGED, and screening.run_manifest when "
        "screening metrics exist before completion.\n"
        "- Record assurance_axis and claim_delta_evidence or "
        "claim_delta_evidence_NOT_CHANGED.\n"
        "- Update docs/40_iterations/Experiment_Queue.md and "
        "docs/45_discoveries/Research_Wiki.md when eval creates follow-up "
        "experiments or stable searchable findings; otherwise report NOT_RUN.\n"
        "- Update action_state.last_action=eval and action_state.next_action "
        "to plan, debug, promote, discard, or stop.\n"
        "- If screening.status=passed and no full_run exists because the "
        "screening primary metric already met the target, finalize metrics "
        "from screening.metrics and explain the screening-target decision.\n"
        "- If screening.status=failed and no full_run exists, finalize metrics "
        "from screening.metrics and explain the failed-screen decision.\n"
        "- Set iteration status to completed.\n"
    ),
    "debug": (
        "You are in auto_mode. Execute `$iterate debug` for iteration {iteration_id}.\n"
        "\n"
        "Phase: debug. Diagnose and repair the current WF10 blocker without "
        "starting an unrelated iteration.\n"
        "\n"
        "IMPORTANT:\n"
        "- auto_mode=true: do NOT ask for user confirmation.\n"
        "- Read iteration_log.json and the run/code manifests for this iteration.\n"
        "- Record the blocker, touched paths, validation commands, and outcome.\n"
        "- Update action_state.last_action=debug and action_state.next_action "
        "to code, run_screening, run_full, eval, compare, discard, or stop.\n"
    ),
    "compare": (
        "You are in auto_mode. Execute `$iterate compare` for iteration "
        "{iteration_id}.\n"
        "\n"
        "Phase: compare. Compare the active result against baseline, previous "
        "best, and relevant recent runs.\n"
        "\n"
        "IMPORTANT:\n"
        "- auto_mode=true: do NOT ask for user confirmation.\n"
        "- Do not invent metrics; use only recorded run artifacts and "
        "iteration_log.json.\n"
        "- Update action_state.last_action=compare and action_state.next_action "
        "to eval, ablate, promote, discard, plan, or stop.\n"
    ),
    "ablate": (
        "You are in auto_mode. Execute `$iterate ablate` for iteration "
        "{iteration_id}.\n"
        "\n"
        "Phase: ablate. Create or continue bounded ablation sub-iterations.\n"
        "\n"
        "IMPORTANT:\n"
        "- auto_mode=true: do NOT ask for user confirmation.\n"
        "- Keep ablation work tied to the parent iteration and record "
        "ablation_summary when available.\n"
        "- Update action_state.last_action=ablate and action_state.next_action "
        "to code, run_screening, run_full, eval, compare, or stop.\n"
    ),
    "register": (
        "You are in auto_mode. Execute `$iterate register` for iteration "
        "{iteration_id}.\n"
        "\n"
        "Phase: register. Register an externally executed or manual run without "
        "inventing missing metrics.\n"
        "\n"
        "IMPORTANT:\n"
        "- auto_mode=true: do NOT ask for user confirmation.\n"
        "- Record command, expected outputs, observed artifact paths, and any "
        "missing evidence explicitly.\n"
        "- Set status to ready_to_eval only when the registered run has a "
        "valid run_manifest bundle; otherwise set needs_more_evidence.\n"
        "- Update action_state.last_action=register and action_state.next_action "
        "to eval, compare, debug, discard, or stop.\n"
    ),
    "promote": (
        "You are in auto_mode. Execute `$iterate promote` for iteration "
        "{iteration_id}.\n"
        "\n"
        "Phase: promote. Promote run-local or candidate WF10 code into stable "
        "implementation surfaces only when the promotion plan and gates support it.\n"
        "\n"
        "IMPORTANT:\n"
        "- auto_mode=true: do NOT ask for user confirmation.\n"
        "- Read implementation.promotion.plan_path and the run code manifest.\n"
        "- Update stable code, tests, project_map.json, and Codebase_Map.md "
        "when stable interfaces or responsibilities change.\n"
        "- Record promotion.status and promoted_commit or rejection reason.\n"
        "- Update action_state.last_action=promote and action_state.next_action "
        "to eval, plan, discard, or stop.\n"
    ),
    "discard": (
        "You are in auto_mode. Execute `$iterate discard` for iteration "
        "{iteration_id}.\n"
        "\n"
        "Phase: discard. Close an iteration or branch that should not continue.\n"
        "\n"
        "IMPORTANT:\n"
        "- auto_mode=true: do NOT ask for user confirmation.\n"
        "- Preserve the reason and any negative result evidence.\n"
        "- Set status to abandoned when the iteration is closed.\n"
        "- Update action_state.last_action=discard and action_state.next_action "
        "to plan or stop.\n"
    ),
    "stop": (
        "You are in auto_mode. Execute `$iterate status` and stop the loop.\n"
        "\n"
        "Phase: stop. Summarize why the run loop should stop and leave "
        "iteration_log.json unchanged unless a missing stop reason must be recorded.\n"
    ),
}

_COMPLETION_INSTRUCTIONS = (
    "\n\n"
    "COMPLETION CONTRACT:\n"
    "- When the required phase state change is complete, write a concise final "
    "summary and exit immediately.\n"
    "- Do not keep inspecting unrelated files after the postcondition can pass.\n"
    "- Do not render docs-site or generated views during auto-iterate phases; "
    "report a docs_site_boundary_report when relevant.\n"
)


def render_prompt(brief: dict[str, Any], iteration_id: str | None = None) -> str:
    """Render a phase-specific prompt string for Codex stdin."""
    pk = brief["phase_key"]
    template = _PROMPT_TEMPLATES.get(pk, _PROMPT_TEMPLATES["plan"])

    obj = brief.get("objective", {})
    pm = obj.get("primary_metric", {})
    best = brief.get("current_best", {})
    bs = brief.get("budget_status", {})
    sp = brief.get("screening_policy", {})

    lessons = brief.get("recent_lessons", [])
    lessons_str = (
        "\n".join(f"  - {lesson}" for lesson in lessons)
        if lessons
        else "  (none)"
    )
    failed = brief.get("failed_hypotheses", [])
    failed_str = (
        "\n".join(f"  - {hypothesis}" for hypothesis in failed)
        if failed
        else "  (none)"
    )
    initial_hypotheses = brief.get("initial_hypotheses", [])
    initial_hypotheses_str = (
        "\n".join(f"  - {hypothesis}" for hypothesis in initial_hypotheses)
        if initial_hypotheses
        else "  (none)"
    )
    forbidden_directions = brief.get("forbidden_directions", [])
    forbidden_directions_str = (
        "\n".join(f"  - {direction}" for direction in forbidden_directions)
        if forbidden_directions
        else "  (none)"
    )
    assurance_axes = brief.get("assurance_axes", [])
    assurance_axes_str = (
        "\n".join(f"  - {axis}" for axis in assurance_axes)
        if assurance_axes
        else "  (none)"
    )
    automation_policy = brief.get("automation_policy", {})
    automation_policy_str = (
        "\n".join(
            f"  - {key}: {value}" for key, value in sorted(automation_policy.items())
        )
        if isinstance(automation_policy, dict) and automation_policy
        else "  (none)"
    )

    return template.format(
        round_index=brief.get("round_index", "?"),
        max_rounds=bs.get("max_rounds", "?"),
        metric_name=pm.get("name", "?"),
        direction=pm.get("direction", "?"),
        target=pm.get("target", "?"),
        best_metric=best.get("primary_metric", "N/A"),
        best_iter=best.get("iteration_id", "N/A"),
        iteration_id=iteration_id or "?",
        lessons=lessons_str,
        failed=failed_str,
        initial_hypotheses=initial_hypotheses_str,
        forbidden_directions=forbidden_directions_str,
        assurance_axes=assurance_axes_str,
        automation_policy=automation_policy_str,
        screening_steps=sp.get("default_steps", 5000),
        threshold_pct=sp.get("threshold_pct", 90),
    ) + _COMPLETION_INSTRUCTIONS


# ---------------------------------------------------------------------------
# Result builder
# ---------------------------------------------------------------------------

def build_result(
    brief: dict[str, Any],
    account_id: str,
    started_at: str,
    finished_at: str,
    duration_sec: float,
    exit_code: int,
    runtime_exit_class: str,
    failure_reason: str | None,
    timed_out: bool,
    stdout_path: str,
    stderr_path: str,
    watchdog: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a runtime result dict per 01§7."""
    result: dict[str, Any] = {
        "schema_version": 1,
        "phase_family": brief.get("phase_family", ""),
        "phase_key": brief.get("phase_key", ""),
        "run_type": brief.get("run_type"),
        "account_id": account_id,
        "started_at": started_at,
        "finished_at": finished_at,
        "duration_sec": round(duration_sec, 1),
        "exit_code": exit_code,
        "runtime_exit_class": runtime_exit_class,
        "failure_reason": failure_reason,
        "timed_out": timed_out,
        "stdout_path": stdout_path,
        "stderr_path": stderr_path,
    }
    if watchdog is not None:
        result["watchdog"] = watchdog
        status_path = watchdog.get("status_path")
        if isinstance(status_path, str) and status_path:
            result["watchdog_status_path"] = status_path
    return result


def _stderr_matches(
    stderr_path: str | None,
    patterns: tuple[re.Pattern[str], ...],
) -> bool:
    if not stderr_path:
        return False
    path = Path(stderr_path)
    if not path.exists():
        return False
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return False
    return any(pattern.search(text) for pattern in patterns)


def classify_exit(
    exit_code: int,
    timed_out: bool,
    stderr_path: str | None = None,
) -> str:
    """Map a process exit code to a ``runtime_exit_class``."""
    if timed_out:
        return "timeout"
    if _stderr_matches(stderr_path, _QUOTA_OR_RATE_LIMIT_PATTERNS):
        return "quota_or_rate_limit"
    if _stderr_matches(stderr_path, _AUTH_FAILURE_PATTERNS):
        return "auth_failure"
    if exit_code == 0:
        return "success"
    # Codex-specific heuristics (can be extended).
    if exit_code in (75, 69):  # EX_TEMPFAIL, EX_UNAVAILABLE
        return "quota_or_rate_limit"
    if exit_code == 77:  # EX_NOPERM
        return "auth_failure"
    return "internal_error"


_MODEL_LINE_RE = re.compile(r"^model:\s*(.+?)\s*$")


def _expected_model(codex_home: str) -> str | None:
    config_path = Path(codex_home) / "config.toml"
    if not config_path.exists():
        return None
    try:
        with config_path.open("rb") as f:
            raw = tomllib.load(f)
    except Exception:
        return None
    model = raw.get("model")
    return model if isinstance(model, str) and model else None


def _actual_model(stderr_path: str) -> str | None:
    path = Path(stderr_path)
    if not path.exists():
        return None
    try:
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            match = _MODEL_LINE_RE.match(line.strip())
            if match:
                model = match.group(1).strip()
                if model:
                    return model
    except Exception:
        return None
    return None


def build_codex_command(
    workspace_root: str | Path,
    phase_key: str,
    *,
    run_phase_full_access: bool = True,
) -> list[str]:
    """Build the codex CLI command for a given phase.

    The code phase needs direct host access because WF10 code postconditions
    require a semantic git commit, which writes ``.git``. Run phases default to
    direct host access so training can see the local GPU.
    Set ``run_phase_full_access=False`` to keep them in ``--full-auto`` when a
    project uses CPU-only or separately managed execution.
    Other phases stay on the safer workspace-write sandbox.
    """
    cmd = ["codex", "exec"]
    if phase_key in _HOST_ACCESS_PHASES or (
        phase_key in _GPU_VISIBLE_PHASES and run_phase_full_access
    ):
        cmd.append("--dangerously-bypass-approvals-and-sandbox")
    else:
        cmd.append("--full-auto")
    cmd.extend([
        "--cd", str(workspace_root),
        "-",  # read prompt from stdin
    ])
    return cmd


# ---------------------------------------------------------------------------
# PhaseSupervisor — launches and monitors runtime
# ---------------------------------------------------------------------------

class PhaseSupervisor:
    """Launch a Codex runtime process for one phase and collect results."""

    def __init__(
        self,
        workspace_root: str | Path,
        runtime_dir: str | Path,
    ) -> None:
        self.workspace_root = Path(workspace_root)
        self.runtime_dir = Path(runtime_dir)
        self.runtime_dir.mkdir(parents=True, exist_ok=True)

    def run_phase(
        self,
        brief: dict[str, Any],
        account_id: str,
        codex_home: str,
        timeout_sec: int,
        terminate_grace_sec: int = 30,
        *,
        iteration_id: str | None = None,
        dry_run: bool = False,
        run_phase_full_access: bool = True,
    ) -> dict[str, Any]:
        """Launch the runtime, wait with timeout, and return result dict.

        If *dry_run* is True, skip actual Codex invocation and return a
        synthetic success result.
        """
        validate_brief(brief)

        pk = brief["phase_key"]
        ri = brief.get("round_index", 0)
        stdout_path = str(self.runtime_dir / f"round{ri}_{pk}.stdout.log")
        stderr_path = str(self.runtime_dir / f"round{ri}_{pk}.stderr.log")
        brief_path = str(self.runtime_dir / f"round{ri}_{pk}_brief.json")
        result_path = str(self.runtime_dir / f"round{ri}_{pk}_result.json")
        result_file = Path(result_path)

        # Write brief for the adapter / diagnostics.
        result_file.unlink(missing_ok=True)
        atomic_write_json(brief_path, brief)

        started_at = iso_now()

        if dry_run:
            return self._dry_run_result(brief, account_id, started_at,
                                        stdout_path, stderr_path)

        prompt = render_prompt(brief, iteration_id=iteration_id)
        watchdog_registration = self._watchdog_registration(
            brief,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            result_path=result_path,
            iteration_id=iteration_id,
        )

        exit_code, timed_out, duration = self._invoke_codex(
            phase_key=pk,
            prompt=prompt,
            codex_home=codex_home,
            timeout_sec=timeout_sec,
            terminate_grace_sec=terminate_grace_sec,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            run_phase_full_access=run_phase_full_access,
            watchdog_registration=watchdog_registration,
        )

        exit_class = classify_exit(exit_code, timed_out, stderr_path=stderr_path)
        failure_reason = None if exit_class == "success" else exit_class

        if exit_class == "success":
            expected_model = _expected_model(codex_home)
            actual_model = _actual_model(stderr_path)
            if expected_model and actual_model and expected_model != actual_model:
                exit_class = "quota_or_rate_limit"
                failure_reason = (
                    f"model_downgrade: expected {expected_model}, got {actual_model}"
                )

        finished_at = iso_now()

        result = build_result(
            brief=brief,
            account_id=account_id,
            started_at=started_at,
            finished_at=finished_at,
            duration_sec=duration,
            exit_code=exit_code,
            runtime_exit_class=exit_class,
            failure_reason=failure_reason,
            timed_out=timed_out,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            watchdog=self._watchdog_payload(watchdog_registration),
        )
        atomic_write_json(result_path, result)
        final_watchdog_status = self._refresh_watchdog(watchdog_registration)
        if final_watchdog_status is not None:
            result.setdefault("watchdog", {})["last_status"] = final_watchdog_status
            atomic_write_json(result_path, result)
        return result

    # ------------------------------------------------------------------
    # Watchdog registration
    # ------------------------------------------------------------------

    def _watchdog_registration(
        self,
        brief: dict[str, Any],
        *,
        stdout_path: str,
        stderr_path: str,
        result_path: str,
        iteration_id: str | None,
    ) -> dict[str, Any] | None:
        if not _watchdog_enabled(brief):
            return None

        phase_key = str(brief.get("phase_key", "phase"))
        round_index = str(brief.get("round_index", 0))
        loop_id = str(brief.get("loop_id") or "loop")
        name = _safe_watchdog_name(
            f"{loop_id}_round{round_index}_{phase_key}"
        )
        base_dir = self.runtime_dir.parent / "run_health"
        status_path = base_dir / "status" / f"{name}.json"
        summary_path = base_dir / "status" / "summary.json"
        task_type = "training" if phase_key in {"run_screening", "run_full"} else "command"
        task: dict[str, Any] = {
            "name": name,
            "type": task_type,
            "session_type": "pid",
            "session": "pending",
            "log_path": stdout_path,
            "stderr_path": stderr_path,
            "output_check": result_path,
            "registered_by": "auto_iterate",
            "workspace_root": str(self.workspace_root),
            "phase_key": phase_key,
            "loop_id": loop_id,
            "round_index": brief.get("round_index", 0),
            "iteration_id": iteration_id,
            "result_path": result_path,
        }
        return {
            "base_dir": str(base_dir),
            "task": task,
            "task_name": name,
            "status_path": str(status_path),
            "summary_path": str(summary_path),
            "registered": False,
        }

    def _watchdog_payload(
        self,
        registration: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        if registration is None:
            return None
        task = registration.get("task")
        phase_key = task.get("phase_key") if isinstance(task, dict) else None
        iteration_id = task.get("iteration_id") if isinstance(task, dict) else None
        payload = {
            "policy": _WATCHDOG_POLICY_ENABLED,
            "base_dir": registration.get("base_dir"),
            "task_name": registration.get("task_name"),
            "status_path": registration.get("status_path"),
            "summary_path": registration.get("summary_path"),
            "registered": bool(registration.get("registered")),
            "phase_key": phase_key,
            "iteration_id": iteration_id,
        }
        if registration.get("error"):
            payload["error"] = registration["error"]
        return payload

    def _register_watchdog(
        self,
        registration: dict[str, Any] | None,
        pid: int,
    ) -> None:
        if registration is None:
            return
        try:
            module = _load_watchdog_module()
            task = dict(registration["task"])
            task["session"] = str(pid)
            registration["task"] = task
            module.register_task(registration["base_dir"], json.dumps(task))
            module.check_all(registration["base_dir"])
            registration["registered"] = True
        except Exception as exc:  # noqa: BLE001 - watchdog must not fail runtime
            registration["error"] = str(exc)

    def _refresh_watchdog(
        self,
        registration: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        if registration is None or not registration.get("registered"):
            return None
        try:
            module = _load_watchdog_module()
            statuses = module.check_all(registration["base_dir"])
        except Exception as exc:  # noqa: BLE001 - watchdog must not fail runtime
            registration["error"] = str(exc)
            return None
        task_name = registration.get("task_name")
        for status in statuses:
            if isinstance(status, dict) and status.get("task") == task_name:
                return status
        return None

    # ------------------------------------------------------------------
    # Codex invocation
    # ------------------------------------------------------------------

    def _invoke_codex(
        self,
        phase_key: str,
        prompt: str,
        codex_home: str,
        timeout_sec: int,
        terminate_grace_sec: int,
        stdout_path: str,
        stderr_path: str,
        run_phase_full_access: bool = True,
        watchdog_registration: dict[str, Any] | None = None,
    ) -> tuple[int, bool, float]:
        """Spawn ``codex exec`` and return ``(exit_code, timed_out, duration_sec)``."""
        env = os.environ.copy()
        env["CODEX_HOME"] = codex_home

        cmd = build_codex_command(
            self.workspace_root,
            phase_key,
            run_phase_full_access=run_phase_full_access,
        )

        start = time.monotonic()
        timed_out = False

        with open(stdout_path, "w") as fout, open(stderr_path, "w") as ferr:
            try:
                proc = subprocess.Popen(
                    cmd,
                    stdin=subprocess.PIPE,
                    stdout=fout,
                    stderr=ferr,
                    env=env,
                    cwd=str(self.workspace_root),
                )
                self._register_watchdog(watchdog_registration, proc.pid)
                proc.stdin.write(prompt.encode("utf-8"))  # type: ignore[union-attr]
                proc.stdin.close()  # type: ignore[union-attr]

                try:
                    proc.wait(timeout=timeout_sec)
                except subprocess.TimeoutExpired:
                    timed_out = True
                    self._terminate(proc, terminate_grace_sec)

            except FileNotFoundError:
                # codex binary not found
                duration = time.monotonic() - start
                return 127, False, duration
            except Exception:
                duration = time.monotonic() - start
                return 1, False, duration

        duration = time.monotonic() - start
        return proc.returncode or 0, timed_out, duration

    def _terminate(self, proc: subprocess.Popen, grace_sec: int) -> None:
        """Graceful SIGTERM → wait → SIGKILL."""
        try:
            proc.terminate()
            proc.wait(timeout=grace_sec)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()

    # ------------------------------------------------------------------
    # Dry run
    # ------------------------------------------------------------------

    def _dry_run_result(
        self,
        brief: dict[str, Any],
        account_id: str,
        started_at: str,
        stdout_path: str,
        stderr_path: str,
    ) -> dict[str, Any]:
        # Create empty log files.
        Path(stdout_path).write_text("[dry_run] No real invocation.\n")
        Path(stderr_path).write_text("")
        return build_result(
            brief=brief,
            account_id=account_id,
            started_at=started_at,
            finished_at=iso_now(),
            duration_sec=0.0,
            exit_code=0,
            runtime_exit_class="success",
            failure_reason=None,
            timed_out=False,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
        )


# ---------------------------------------------------------------------------
# HeartbeatWorker
# ---------------------------------------------------------------------------

class HeartbeatWorker:
    """Background thread that refreshes the lock heartbeat periodically."""

    def __init__(self, lock_manager: Any, interval_sec: int = 30) -> None:
        self._lock_manager = lock_manager
        self._interval = interval_sec
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._alive = False

    def start(self) -> None:
        self._stop_event.clear()
        self._alive = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=self._interval + 5)
        self._alive = False

    def is_alive(self) -> bool:
        if self._thread is None:
            return False
        return self._thread.is_alive() and self._alive

    def _run(self) -> None:
        while not self._stop_event.is_set():
            try:
                self._lock_manager.update_heartbeat()
            except Exception:
                self._alive = False
                return
            self._stop_event.wait(timeout=self._interval)
