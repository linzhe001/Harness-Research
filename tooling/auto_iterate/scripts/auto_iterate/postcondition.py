"""Repository postcondition validator.

Phase success is determined *only* by inspecting the repository state
(``iteration_log.json``, ``PROJECT_STATE.json``), never from runtime
stdout, chat prose, or runtime metadata.

See ``01_contract_freeze.md`` §4.4 for the frozen postcondition table
and §4.5 for the ``current_iteration_id`` binding algorithm.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from .state import StateLoadError, load_json

TOOLING_DIR = Path(__file__).resolve().parents[3]
if str(TOOLING_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLING_DIR))

from run_artifacts import run_artifact_errors  # noqa: E402

_DEFAULT_MANIFEST = object()

# ---------------------------------------------------------------------------
# Result dataclass (plain dict for simplicity)
# ---------------------------------------------------------------------------

def _ok(phase_key: str, classification: str, iteration_id: str | None,
        payload: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "ok": True,
        "phase_key": phase_key,
        "classification": classification,
        "iteration_id": iteration_id,
        "payload": payload or {},
    }


def _fail(phase_key: str, classification: str, iteration_id: str | None,
          payload: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "ok": False,
        "phase_key": phase_key,
        "classification": classification,
        "iteration_id": iteration_id,
        "payload": payload or {},
    }


# ---------------------------------------------------------------------------
# current_iteration_id binding (01§4.5)
# ---------------------------------------------------------------------------

def bind_iteration_id(
    pre_ids: set[str],
    post_ids: set[str],
) -> tuple[str | None, str | None]:
    """Return ``(iteration_id, error_message)``.

    Exactly one new ID must appear; otherwise return an error.
    """
    new_ids = post_ids - pre_ids
    if len(new_ids) == 0:
        return None, "plan did not create a new iteration entry"
    if len(new_ids) > 1:
        return (
            None,
            f"plan created {len(new_ids)} entries (ambiguous): {sorted(new_ids)}",
        )
    return new_ids.pop(), None


# ---------------------------------------------------------------------------
# Per-phase validators
# ---------------------------------------------------------------------------

def _get_iteration(iterations: list[dict], iteration_id: str) -> dict | None:
    for it in iterations:
        if it.get("id") == iteration_id:
            return it
    return None


def _get_ids(iterations: list[dict]) -> set[str]:
    return {it["id"] for it in iterations if "id" in it}


def _existing_planned_iteration_id(
    iterations: list[dict],
) -> tuple[str | None, str | None]:
    blocking_statuses = {"coding", "training", "running"}
    blocking = sorted(
        it["id"]
        for it in iterations
        if isinstance(it.get("id"), str) and it.get("status") in blocking_statuses
    )
    if blocking:
        return (
            None,
            "cannot adopt an existing planned iteration while blocking "
            f"unfinished iterations exist: {blocking}",
        )

    planned = sorted(
        it["id"]
        for it in iterations
        if isinstance(it.get("id"), str) and it.get("status") == "planned"
    )
    if len(planned) == 0:
        return None, "plan did not create a new iteration entry"
    if len(planned) > 1:
        return (
            None,
            "plan did not create a new iteration entry and found multiple "
            f"existing planned iterations (ambiguous): {planned}",
        )
    return planned[0], None


def _run_manifest_error(
    iteration: dict,
    *,
    run_manifest: dict[str, Any] | object = _DEFAULT_MANIFEST,
    manifest_name: str = "run_manifest",
) -> str | None:
    if run_manifest is _DEFAULT_MANIFEST:
        run_manifest = iteration.get("run_manifest")
    if not isinstance(run_manifest, dict) or not run_manifest:
        return f"{manifest_name} is required"
    if (
        not isinstance(run_manifest.get("command"), str)
        or not run_manifest.get("command", "").strip()
    ):
        return f"{manifest_name}.command is required"
    if (
        not isinstance(run_manifest.get("exp_dir"), str)
        or not run_manifest.get("exp_dir", "").strip()
    ):
        return f"{manifest_name}.exp_dir is required"
    return None


def _run_artifact_error(
    root: Path,
    iteration: dict,
    *,
    run_manifest: dict[str, Any] | object = _DEFAULT_MANIFEST,
    manifest_name: str = "run_manifest",
) -> str | None:
    kwargs: dict[str, Any] = {"manifest_name": manifest_name}
    if run_manifest is not _DEFAULT_MANIFEST:
        kwargs["run_manifest"] = run_manifest
    errors = run_artifact_errors(root, iteration, **kwargs)
    if not errors:
        return None
    return "; ".join(errors)


def _screening_run_manifest(iteration: dict) -> dict[str, Any] | None:
    screening = iteration.get("screening")
    if not isinstance(screening, dict):
        return None
    manifest = screening.get("run_manifest")
    return manifest if isinstance(manifest, dict) else None


def _manifest_exp_dir(manifest: Any) -> str | None:
    if not isinstance(manifest, dict):
        return None
    exp_dir = manifest.get("exp_dir")
    if not isinstance(exp_dir, str) or not exp_dir.strip():
        return None
    return exp_dir.strip()


def _screening_run_artifact_error(root: Path, iteration: dict) -> str | None:
    screening = iteration.get("screening")
    if not (
        isinstance(screening, dict)
        and screening.get("status") in ("passed", "failed")
        and isinstance(screening.get("metrics"), dict)
        and screening.get("metrics")
    ):
        return None

    screening_manifest = _screening_run_manifest(iteration)
    manifest_error = _run_manifest_error(
        iteration,
        run_manifest=screening_manifest,
        manifest_name="screening.run_manifest",
    )
    if manifest_error:
        return manifest_error

    artifact_error = _run_artifact_error(
        root,
        iteration,
        run_manifest=screening_manifest,
        manifest_name="screening.run_manifest",
    )
    if artifact_error:
        return artifact_error

    full_run = iteration.get("full_run")
    if isinstance(full_run, dict) and full_run.get("status") == "completed":
        full_exp_dir = _manifest_exp_dir(iteration.get("run_manifest"))
        screening_exp_dir = _manifest_exp_dir(screening_manifest)
        if full_exp_dir and screening_exp_dir and full_exp_dir == screening_exp_dir:
            return (
                "screening.run_manifest.exp_dir must differ from "
                "run_manifest.exp_dir when full_run.status=completed"
            )
    return None


def _tracked_metric_names(protocol: Any) -> set[str]:
    if not isinstance(protocol, dict):
        return set()
    metrics = protocol.get("tracked_metrics")
    if not isinstance(metrics, list):
        return set()
    names: set[str] = set()
    for item in metrics:
        if isinstance(item, dict) and isinstance(item.get("name"), str):
            names.add(item["name"])
        elif isinstance(item, str):
            names.add(item)
    return names


def _primary_metric_name(protocol: Any) -> str | None:
    if not isinstance(protocol, dict):
        return None
    metric = protocol.get("primary_metric")
    if isinstance(metric, str) and metric.strip():
        return metric.strip()
    if isinstance(metric, dict):
        name = metric.get("name")
        if isinstance(name, str) and name.strip():
            return name.strip()
    return None


def _metrics_protocol_error(
    metrics: dict[str, Any],
    *,
    tracked: set[str],
    primary_metric: str | None,
) -> str | None:
    if tracked:
        unknown = sorted(set(metrics) - tracked)
        if unknown:
            return (
                "metrics contain keys outside the tracked metric protocol: "
                f"{', '.join(unknown)}"
            )
    if primary_metric and primary_metric not in metrics:
        return f"metrics must include primary metric {primary_metric!r}"
    if primary_metric:
        value = metrics[primary_metric]
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return f"primary metric {primary_metric!r} must be numeric"
    return None


def _screening_metrics_error(iteration: dict, tracked: set[str]) -> str | None:
    screening = iteration.get("screening")
    if not isinstance(screening, dict):
        return "screening is required"
    status = screening.get("status")
    if status not in ("passed", "failed"):
        return None
    metrics = screening.get("metrics")
    if not isinstance(metrics, dict) or not metrics:
        return "screening.metrics are required when screening.status is passed|failed"
    if tracked:
        unknown = sorted(set(metrics) - tracked)
        if unknown:
            return (
                "screening.metrics contain keys outside the tracked metric "
                f"protocol: {', '.join(unknown)}"
            )
    return None


def _valid_codex_review(value: Any) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, dict):
        status = value.get("status")
        if isinstance(status, str) and status.strip():
            return True
        approved = value.get("approved")
        rounds = value.get("rounds")
        feedback = value.get("feedback")
        return (
            isinstance(approved, bool)
            or isinstance(rounds, int)
            or (isinstance(feedback, str) and bool(feedback.strip()))
        )
    return False


def iteration_metrics(iteration: dict[str, Any]) -> dict[str, Any]:
    top_level = iteration.get("metrics")
    if isinstance(top_level, dict) and top_level:
        return top_level
    full_run = iteration.get("full_run")
    if isinstance(full_run, dict):
        nested = full_run.get("metrics")
        if isinstance(nested, dict):
            return nested
    return {}


def iteration_metrics_conflict(iteration: dict[str, Any]) -> bool:
    top_level = iteration.get("metrics")
    full_run = iteration.get("full_run")
    if not isinstance(top_level, dict) or not top_level:
        return False
    if not isinstance(full_run, dict):
        return False
    nested = full_run.get("metrics")
    return isinstance(nested, dict) and bool(nested) and top_level != nested


def iteration_report_paths(root: Path, iteration_id: str) -> list[Path]:
    """Return supported per-iteration report locations."""
    return [
        root / "docs" / "iterations" / f"{iteration_id}.md",
        root / "docs" / "40_iterations" / f"{iteration_id}.md",
    ]


def existing_iteration_report_path(root: Path, iteration_id: str) -> Path | None:
    for path in iteration_report_paths(root, iteration_id):
        if path.exists():
            return path
    return None


def iteration_report_error(root: Path, iteration_id: str) -> str:
    candidates = ", ".join(
        path.relative_to(root).as_posix()
        for path in iteration_report_paths(root, iteration_id)
    )
    return f"Per-iteration report is required at one of: {candidates}"


class PostconditionValidator:
    """Validates repository postconditions after each phase."""

    def __init__(self, workspace_root: str | Path) -> None:
        self.root = Path(workspace_root)
        self.iter_log_path = self.root / "iteration_log.json"

    def load_iteration_log(self) -> dict[str, Any]:
        try:
            return load_json(self.iter_log_path)
        except StateLoadError:
            return {"iterations": []}

    def get_iteration_ids(self) -> set[str]:
        log = self.load_iteration_log()
        return _get_ids(log.get("iterations", []))

    def validate(
        self,
        phase_key: str,
        current_iteration_id: str | None,
        *,
        pre_ids: set[str] | None = None,
        primary_metric_name: str | None = None,
    ) -> dict[str, Any]:
        """Run the postcondition check for *phase_key*.

        For ``plan``, *pre_ids* must be the set of iteration IDs before
        the phase ran; the validator computes new IDs and binds
        ``current_iteration_id``.

        For all other phases, *current_iteration_id* must already be
        bound (set during the ``plan`` phase).
        """
        log = self.load_iteration_log()
        iterations = log.get("iterations", [])
        tracked = _tracked_metric_names(log.get("evaluation_protocol"))
        primary_metric = (
            primary_metric_name
            or _primary_metric_name(log.get("evaluation_protocol"))
        )

        if phase_key == "plan":
            return self._validate_plan(iterations, pre_ids or set())
        elif phase_key == "code":
            return self._validate_code(iterations, current_iteration_id)
        elif phase_key == "run_screening":
            return self._validate_run_screening(
                iterations,
                current_iteration_id,
                tracked,
            )
        elif phase_key == "run_full":
            return self._validate_run_full(
                iterations,
                current_iteration_id,
                tracked,
                primary_metric,
            )
        elif phase_key == "eval":
            return self._validate_eval(
                iterations,
                current_iteration_id,
                tracked,
                primary_metric,
            )
        else:
            return _fail(phase_key, "unknown_phase", current_iteration_id,
                         {"error": f"Unknown phase_key: {phase_key}"})

    # -- plan ---------------------------------------------------------------

    def _validate_plan(
        self, iterations: list[dict], pre_ids: set[str],
    ) -> dict[str, Any]:
        post_ids = _get_ids(iterations)
        iter_id, err = bind_iteration_id(pre_ids, post_ids)
        if err:
            if post_ids - pre_ids:
                return _fail("plan", "postcondition_failed", None,
                             {"error": err})
            iter_id, err = _existing_planned_iteration_id(iterations)
            if err:
                return _fail("plan", "postcondition_failed", None,
                             {"error": err})

        it = _get_iteration(iterations, iter_id)  # type: ignore[arg-type]
        if it is None:
            return _fail("plan", "postcondition_failed", iter_id,
                         {"error": "New iteration not found after binding"})

        if it.get("status") != "planned":
            return _fail(
                "plan",
                "postcondition_failed",
                iter_id,
                {"error": f"Expected status=planned, got {it.get('status')!r}"},
            )

        # Check required plan fields
        missing = []
        if not it.get("hypothesis"):
            missing.append("hypothesis")
        if not it.get("date"):
            missing.append("date")
        if not it.get("changes_summary"):
            missing.append("changes_summary")
        if "config_diff" not in it or not isinstance(it.get("config_diff"), dict):
            missing.append("config_diff")
        screening = it.get("screening")
        if not isinstance(screening, dict) or not isinstance(
            screening.get("recommended"),
            bool,
        ):
            missing.append("screening.recommended")
        if not _valid_codex_review(it.get("codex_review")):
            missing.append("codex_review")
        if missing:
            return _fail("plan", "postcondition_failed", iter_id,
                         {"missing_fields": missing})

        payload = {"adopted_existing": iter_id in pre_ids}
        return _ok("plan", "planned", iter_id, payload)

    # -- code ---------------------------------------------------------------

    def _validate_code(
        self, iterations: list[dict], iteration_id: str | None,
    ) -> dict[str, Any]:
        if iteration_id is None:
            return _fail("code", "postcondition_failed", None,
                         {"error": "current_iteration_id not bound"})

        it = _get_iteration(iterations, iteration_id)
        if it is None:
            return _fail("code", "postcondition_failed", iteration_id,
                         {"error": f"Iteration {iteration_id} not found"})

        if it.get("status") != "training":
            return _fail(
                "code",
                "postcondition_failed",
                iteration_id,
                {"error": f"Expected status=training, got {it.get('status')!r}"},
            )

        if not it.get("git_commit"):
            return _fail("code", "postcondition_failed", iteration_id,
                         {"missing_fields": ["git_commit"]})
        if not it.get("git_message"):
            return _fail("code", "postcondition_failed", iteration_id,
                         {"missing_fields": ["git_message"]})

        return _ok("code", "training", iteration_id)

    # -- run_screening ------------------------------------------------------

    def _validate_run_screening(
        self,
        iterations: list[dict],
        iteration_id: str | None,
        tracked_metrics: set[str],
    ) -> dict[str, Any]:
        if iteration_id is None:
            return _fail("run_screening", "postcondition_failed", None,
                         {"error": "current_iteration_id not bound"})

        it = _get_iteration(iterations, iteration_id)
        if it is None:
            return _fail("run_screening", "postcondition_failed", iteration_id,
                         {"error": f"Iteration {iteration_id} not found"})

        screening = it.get("screening", {})
        status = screening.get("status")
        if status not in ("passed", "failed", "skipped"):
            return _fail(
                "run_screening",
                "postcondition_failed",
                iteration_id,
                {
                    "error": (
                        f"screening.status={status!r}, "
                        "expected passed|failed|skipped"
                    )
                },
            )
        screening_manifest = _screening_run_manifest(it)
        manifest_error = (
            None
            if status == "skipped"
            else _run_manifest_error(
                it,
                run_manifest=screening_manifest,
                manifest_name="screening.run_manifest",
            )
        )
        if manifest_error:
            return _fail("run_screening", "postcondition_failed", iteration_id,
                         {"error": manifest_error})
        if status in ("passed", "failed"):
            artifact_error = _run_artifact_error(
                self.root,
                it,
                run_manifest=screening_manifest,
                manifest_name="screening.run_manifest",
            )
            if artifact_error:
                return _fail("run_screening", "postcondition_failed",
                             iteration_id, {"error": artifact_error})
        metrics_error = _screening_metrics_error(it, tracked_metrics)
        if metrics_error:
            return _fail("run_screening", "postcondition_failed", iteration_id,
                         {"error": metrics_error})

        return _ok("run_screening", status, iteration_id,
                    {"screening_status": status})

    # -- run_full -----------------------------------------------------------

    def _validate_run_full(
        self,
        iterations: list[dict],
        iteration_id: str | None,
        tracked_metrics: set[str],
        primary_metric: str | None,
    ) -> dict[str, Any]:
        if iteration_id is None:
            return _fail("run_full", "postcondition_failed", None,
                         {"error": "current_iteration_id not bound"})

        it = _get_iteration(iterations, iteration_id)
        if it is None:
            return _fail("run_full", "postcondition_failed", iteration_id,
                         {"error": f"Iteration {iteration_id} not found"})

        full_run = it.get("full_run", {})
        status = full_run.get("status")
        if status not in ("completed", "recoverable_failed", "failed"):
            return _fail(
                "run_full",
                "postcondition_failed",
                iteration_id,
                {
                    "error": (
                        f"full_run.status={status!r}, "
                        "expected completed|recoverable_failed|failed"
                    )
                },
            )
        if status == "completed":
            metrics = full_run.get("metrics", {})
            if not isinstance(metrics, dict) or not metrics:
                return _fail(
                    "run_full",
                    "postcondition_failed",
                    iteration_id,
                    {
                        "error": (
                            "full_run.metrics are required when "
                            "full_run.status=completed"
                        )
                    },
                )
            metrics_error = _metrics_protocol_error(
                metrics,
                tracked=tracked_metrics,
                primary_metric=primary_metric,
            )
            if metrics_error:
                return _fail("run_full", "postcondition_failed", iteration_id,
                             {"error": metrics_error})
            manifest_error = _run_manifest_error(it)
            if manifest_error:
                return _fail("run_full", "postcondition_failed", iteration_id,
                             {"error": manifest_error})
            artifact_error = _run_artifact_error(self.root, it)
            if artifact_error:
                return _fail("run_full", "postcondition_failed", iteration_id,
                             {"error": artifact_error})
            screening_artifact_error = _screening_run_artifact_error(
                self.root,
                it,
            )
            if screening_artifact_error:
                return _fail(
                    "run_full",
                    "postcondition_failed",
                    iteration_id,
                    {"error": screening_artifact_error},
                )
        if status in ("recoverable_failed", "failed"):
            run_manifest = it.get("run_manifest", {}) or {}
            if not full_run.get("error") and not run_manifest.get("error"):
                return _fail("run_full", "postcondition_failed", iteration_id,
                             {"error": "error is required for failed full_run status"})

        return _ok("run_full", status, iteration_id,
                    {"full_run_status": status})

    # -- eval ---------------------------------------------------------------

    def _validate_eval(
        self,
        iterations: list[dict],
        iteration_id: str | None,
        tracked_metrics: set[str],
        primary_metric: str | None,
    ) -> dict[str, Any]:
        if iteration_id is None:
            return _fail("eval", "postcondition_failed", None,
                         {"error": "current_iteration_id not bound"})

        it = _get_iteration(iterations, iteration_id)
        if it is None:
            return _fail("eval", "postcondition_failed", iteration_id,
                         {"error": f"Iteration {iteration_id} not found"})

        if it.get("status") != "completed":
            return _fail(
                "eval",
                "postcondition_failed",
                iteration_id,
                {"error": f"Expected status=completed, got {it.get('status')!r}"},
            )

        decision = it.get("decision")
        valid_decisions = {"NEXT_ROUND", "DEBUG", "CONTINUE", "PIVOT", "ABORT"}
        if decision not in valid_decisions:
            return _fail(
                "eval",
                "postcondition_failed",
                iteration_id,
                {"error": f"decision={decision!r}, expected one of {valid_decisions}"},
            )

        lessons = it.get("lessons", [])
        if not lessons:
            return _fail("eval", "postcondition_failed", iteration_id,
                         {"error": "At least 1 lesson is required"})

        if iteration_metrics_conflict(it):
            return _fail(
                "eval",
                "postcondition_failed",
                iteration_id,
                {
                    "error": (
                        "iteration.metrics and full_run.metrics both exist "
                        "with different values"
                    )
                },
            )

        metrics = iteration_metrics(it)
        if not isinstance(metrics, dict) or not metrics:
            return _fail("eval", "postcondition_failed", iteration_id,
                         {"error": "Finalized metrics are required"})
        metrics_error = _metrics_protocol_error(
            metrics,
            tracked=tracked_metrics,
            primary_metric=primary_metric,
        )
        if metrics_error:
            return _fail("eval", "postcondition_failed", iteration_id,
                         {"error": metrics_error})
        git_commit = it.get("git_commit")
        if not isinstance(git_commit, str) or not git_commit.strip():
            return _fail("eval", "postcondition_failed", iteration_id,
                         {"error": "git_commit is required"})
        manifest_error = _run_manifest_error(it)
        if manifest_error:
            return _fail("eval", "postcondition_failed", iteration_id,
                         {"error": manifest_error})
        artifact_error = _run_artifact_error(self.root, it)
        if artifact_error:
            return _fail("eval", "postcondition_failed", iteration_id,
                         {"error": artifact_error})
        screening_artifact_error = _screening_run_artifact_error(self.root, it)
        if screening_artifact_error:
            return _fail("eval", "postcondition_failed", iteration_id,
                         {"error": screening_artifact_error})
        if existing_iteration_report_path(self.root, iteration_id) is None:
            return _fail(
                "eval",
                "postcondition_failed",
                iteration_id,
                {"error": iteration_report_error(self.root, iteration_id)},
            )

        return _ok("eval", "completed", iteration_id,
                    {"decision": decision})
