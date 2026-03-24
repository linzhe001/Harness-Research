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

VALID_PHASE_KEYS = {"plan", "code", "run_screening", "run_full", "eval"}
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
}

_GPU_VISIBLE_PHASES = {"run_screening", "run_full"}
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
    if pk in ("plan", "code", "eval") and rt is not None:
        raise BriefValidationError(
            f"phase_key={pk} should have run_type=null, got {rt!r}"
        )

    rm = brief.get("recovery_mode")
    if rm not in VALID_RECOVERY_MODES:
        raise BriefValidationError(f"Invalid recovery_mode: {rm!r}")


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
        "IMPORTANT:\n"
        "- auto_mode=true: do NOT ask for user confirmation.\n"
        "- Write exactly 1 new iteration entry with status=planned.\n"
        "- Include screening.recommended field.\n"
        "- iteration_log.json is the source of truth.\n"
    ),
    "code": (
        "You are in auto_mode. Execute `$iterate code` for iteration {iteration_id}.\n"
        "\n"
        "Phase: code. Implement the planned changes.\n"
        "\n"
        "IMPORTANT:\n"
        "- auto_mode=true: do NOT ask for user confirmation.\n"
        "- You MUST create a semantic git commit.\n"
        "- Update iteration status to training with git_commit and git_message.\n"
        "- Use $code-debug for actual code modifications.\n"
    ),
    "run_screening": (
        "You are in auto_mode. Execute `$iterate run` "
        "(screening mode) for iteration {iteration_id}.\n"
        "\n"
        "Phase: run_screening. Run a short proxy training ({screening_steps} steps).\n"
        "\n"
        "IMPORTANT:\n"
        "- auto_mode=true: do NOT ask for user confirmation.\n"
        "- Update screening.status to passed|failed|skipped.\n"
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
        "- Update full_run.status to completed|recoverable_failed|failed.\n"
        "- Record metrics in full_run.metrics.\n"
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
        "- Decision must be exactly ONE of: NEXT_ROUND, DEBUG, CONTINUE, "
        "PIVOT, ABORT.\n"
        "  - NEXT_ROUND: ordinary improvement, continue loop.\n"
        "  - DEBUG: bug/stability issue, continue with debug focus.\n"
        "  - CONTINUE: target met or ready for WF9 handoff.\n"
        "  - PIVOT: fundamental approach change needed.\n"
        "  - ABORT: terminate this research direction.\n"
        "- Record at least 1 lesson.\n"
        "- Set iteration status to completed.\n"
    ),
}


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
        screening_steps=sp.get("default_steps", 5000),
        threshold_pct=sp.get("threshold_pct", 90),
    )


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
) -> dict[str, Any]:
    """Build a runtime result dict per 01§7."""
    return {
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


def build_codex_command(workspace_root: str | Path, phase_key: str) -> list[str]:
    """Build the codex CLI command for a given phase.

    Run phases need direct host access so training can see the local GPU.
    Other phases stay on the safer workspace-write sandbox.
    """
    cmd = ["codex"]
    if phase_key in _GPU_VISIBLE_PHASES:
        cmd.append("--dangerously-bypass-approvals-and-sandbox")
    else:
        cmd.append("--full-auto")
    cmd.extend([
        "exec",
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

        # Write brief for the adapter / diagnostics.
        atomic_write_json(brief_path, brief)

        started_at = iso_now()

        if dry_run:
            return self._dry_run_result(brief, account_id, started_at,
                                        stdout_path, stderr_path)

        prompt = render_prompt(brief, iteration_id=iteration_id)

        exit_code, timed_out, duration = self._invoke_codex(
            phase_key=pk,
            prompt=prompt,
            codex_home=codex_home,
            timeout_sec=timeout_sec,
            terminate_grace_sec=terminate_grace_sec,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
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
        )
        atomic_write_json(result_path, result)
        return result

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
    ) -> tuple[int, bool, float]:
        """Spawn ``codex exec`` and return ``(exit_code, timed_out, duration_sec)``."""
        env = os.environ.copy()
        env["CODEX_HOME"] = codex_home

        cmd = build_codex_command(self.workspace_root, phase_key)

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
