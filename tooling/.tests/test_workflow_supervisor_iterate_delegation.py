from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "tooling" / "workflow_supervisor" / "scripts"))

import workflow_ctl  # noqa: E402


def make_workspace(tmp_path: Path) -> Path:
    root = tmp_path / "workspace"
    root.mkdir()
    shutil.copytree(REPO_ROOT / "schemas", root / "schemas")
    (root / "docs").mkdir()
    (root / "docs" / "auto_iterate_goal.md").write_text(
        """# Auto-Iterate Goal

## Objective

### Primary Metric
- **name**: validation_score
- **direction**: maximize
- **target**: 1.0

### Constraints
- Keep changes scoped.

## Contract Readiness
- **evaluation_contract**: legacy_protocol
- **source**: fixture

## Patience
- **max_no_improve_rounds**: 1
- **min_primary_delta**: 0.1

## Budget
- **max_rounds**: 1
- **max_gpu_hours**: 1.0

## Screening Policy
- **enabled**: false
- **threshold_pct**: 90
- **default_steps**: 10

## Initial Hypotheses
1. Test hypothesis.

## Forbidden Directions
- Do not use external data.
""",
        encoding="utf-8",
    )
    return root


def test_iterate_start_delegates_to_auto_iterate_dry_run(
    tmp_path: Path,
    capsys,
) -> None:
    root = make_workspace(tmp_path)

    code = workflow_ctl.main(
        [
            "--workspace-root",
            str(root),
            "start",
            "--segment",
            "iterate",
            "--goal",
            "delegate WF10",
            "--auto-dry-run",
            "--max-rounds",
            "0",
            "--skip-dynamic-preflight",
            "--skip-dynamic-preflight-reason",
            "fixture dry run",
            "--json",
        ]
    )

    assert code == workflow_ctl.EXIT_OK
    payload = json.loads(capsys.readouterr().out)
    state = payload["state"]
    run_id = state["active_run_id"]
    assert state["status"] == "completed"
    assert state["segment"] == "iterate"
    assert state["segment_status"] == "iterate_delegated_max_rounds_reached"
    assert (root / ".auto_iterate" / "state.json").exists()
    record = json.loads(
        (
            root
            / ".workflow_supervisor"
            / "runs"
            / run_id
            / "node_runs"
            / "iterate_delegate_auto_iterate.json"
        ).read_text(encoding="utf-8")
    )
    assert record["gate_ledger"][0]["result"] == "PASS"
    assert not any(
        path.startswith(".auto_iterate/") for path in record["observed_writes"]
    )


def test_monitor_iterate_maps_manual_action_to_pending_request(
    tmp_path: Path,
    capsys,
) -> None:
    root = make_workspace(tmp_path)
    run_id = "sup_20260605_000000"
    (root / ".auto_iterate").mkdir()
    workflow_ctl.atomic_write_json(
        root / ".auto_iterate" / "state.json",
        {
            "schema_version": 1,
            "loop_id": "auto_20260605_000000",
            "status": "paused",
            "halt_reason": "manual_action_required",
            "current_round_index": 1,
            "current_phase_key": "eval",
            "current_iteration_id": "iter_001",
            "accounts": {"selected_account_id": "external_current"},
            "objective": {"primary_metric": {"name": "validation_score"}},
            "best": {"primary_metric": None},
            "budget": {"completed_rounds": 1, "max_rounds": 2},
            "llm_budget": {"used_calls": 5, "max_calls": 20},
            "last_decision": None,
            "last_failure": {"phase": "eval"},
        },
    )
    workflow_ctl.supervisor_root(root).mkdir()
    state = workflow_ctl.base_state(run_id, "iterate")
    state["status"] = "completed"
    state["segment_status"] = "iterate_delegated_running"
    state["current_node_id"] = None
    workflow_ctl.save_state(root, state)

    code = workflow_ctl.main(
        [
            "--workspace-root",
            str(root),
            "monitor-iterate",
            "--json",
        ]
    )

    assert code == workflow_ctl.EXIT_MANUAL_ACTION
    payload = json.loads(capsys.readouterr().out)
    assert payload["supervisor_updated"] is True
    supervisor = payload["supervisor"]["state"]
    assert supervisor["status"] == "paused"
    assert supervisor["segment_status"] == "auto_iterate_manual_action_required"
    pending = json.loads(
        (root / ".workflow_supervisor" / "pending_request.json").read_text(
            encoding="utf-8"
        )
    )
    assert pending["type"] == "STEER"
    assert pending["reason"] == "auto_iterate_manual_action_required"
    assert ".auto_iterate/state.json" in pending["gate_status_refs"]
    assert pending["request_snapshot_hash"] == workflow_ctl.request_snapshot_hash(
        pending
    )
