from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "tooling/evidence/build_experiment_evidence_index.py"
LIGHT_SCRIPT = REPO_ROOT / "tooling/evidence/build_light_evidence_index.py"
MIGRATE_SCRIPT = REPO_ROOT / "tooling/evidence/migrate_iteration_log_v2.py"


def _iteration(exp_dir: str = "experiments/iter1") -> dict:
    return {
        "id": "iter1",
        "status": "completed",
        "git_commit": "abc123",
        "hypothesis": "Test whether the new method improves the recorded split.",
        "metrics": {"accuracy": 0.91},
        "lessons": ["The method improved accuracy on the recorded split."],
        "lesson_candidates": [
            {
                "claim": "The method improved accuracy on the recorded split.",
                "level": "project",
                "confidence": "medium",
                "evidence": ["experiments/iter1/epochs/1/eval.jsonl"],
                "promotion_status": "candidate",
                "boundary": "Only claim this for the recorded split.",
                "future_action": "Run a seed sweep.",
            }
        ],
        "run_manifest": {
            "artifact_contract_version": "1",
            "run_type": "full",
            "command": "python train.py",
            "exp_dir": exp_dir,
            "resolved_config_path": f"{exp_dir}/run_param.yaml",
            "stdout_log_path": f"{exp_dir}/stdout+stderr.log",
            "git_snapshot_path": f"{exp_dir}/git_status/commit.txt",
            "git_commit": "abc123",
            "pre_train_commit": "abc123",
            "pre_eval_commit_NOT_CHANGED": True,
            "eval_artifact_paths": [f"{exp_dir}/epochs/1/eval.jsonl"],
        },
    }


def _write_bundle(root: Path, iteration: dict) -> None:
    manifest = iteration["run_manifest"]
    exp_dir = root / manifest["exp_dir"]
    (exp_dir / "git_status").mkdir(parents=True, exist_ok=True)
    (exp_dir / "epochs" / "1").mkdir(parents=True, exist_ok=True)
    (exp_dir / "run_param.yaml").write_text(
        "seed: 1\nobjective: recorded split comparison\n",
        encoding="utf-8",
    )
    (exp_dir / "stdout+stderr.log").write_text("done\n", encoding="utf-8")
    (exp_dir / "git_status" / "commit.txt").write_text("abc123\n", encoding="utf-8")
    (exp_dir / "epochs" / "1" / "eval.jsonl").write_text(
        '{"metric": "accuracy", "accuracy": 0.91, "result": "improved"}\n',
        encoding="utf-8",
    )


def test_build_experiment_evidence_index_writes_paper_facing_outputs(
    tmp_path: Path,
) -> None:
    iteration = _iteration()
    _write_bundle(tmp_path, iteration)
    watchdog_status = (
        tmp_path
        / ".auto_iterate"
        / "run_health"
        / "status"
        / "auto_round1_run_full.json"
    )
    watchdog_status.parent.mkdir(parents=True)
    watchdog_status.write_text(
        json.dumps(
            {
                "status": "COMPLETED",
                "task": "auto_round1_run_full",
                "type": "training",
                "phase_key": "run_full",
                "iteration_id": "iter1",
                "ts": "2026-04-30T00:00:00Z",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (tmp_path / "docs" / "40_iterations").mkdir(parents=True)
    (tmp_path / "docs" / "40_iterations" / "iter1.md").write_text(
        "\n".join(
            [
                "# Iteration iter1",
                "",
                "Purpose: test whether the new method improves the recorded split.",
                "Result: accuracy reached 0.91 on the recorded split.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (tmp_path / "iteration_log.json").write_text(
        json.dumps({"iterations": [iteration]}) + "\n",
        encoding="utf-8",
    )
    discovery = tmp_path / "docs" / "45_discoveries" / "Discovery_Ledger.md"
    discovery.parent.mkdir(parents=True)
    discovery.write_text(
        "\n".join(
            [
                "# Discovery Ledger",
                "",
                "| ID | Date | Level | Status | Summary | Evidence Refs | "
                "Next Experiment Hint |",
                "| --- | --- | --- | --- | --- | --- | --- |",
                "| d1 | 2026-06-17 | phenomenon | open | accuracy jump after "
                "config change | iteration_log.json | ablate config |",
                "",
            ]
        ),
        encoding="utf-8",
    )
    queue = tmp_path / "docs" / "40_iterations" / "Experiment_Queue.md"
    queue.parent.mkdir(parents=True, exist_ok=True)
    queue.write_text(
        "\n".join(
            [
                "# Experiment Queue",
                "",
                "| ID | Priority | Status | Assurance Axis | Question | "
                "Falsifier | Evidence Needed |",
                "| --- | --- | --- | --- | --- | --- | --- |",
                "| q1 | high | open | ablation | test whether the gain is "
                "component-specific | no change after ablation | "
                "ablation metrics |",
                "",
            ]
        ),
        encoding="utf-8",
    )
    wiki = tmp_path / "docs" / "45_discoveries" / "Research_Wiki.md"
    wiki.write_text(
        "\n".join(
            [
                "# Research Wiki",
                "",
                "| ID | Type | Status | Summary | Evidence Refs |",
                "| --- | --- | --- | --- | --- |",
                "| w1 | finding | active | component appears responsible for "
                "accuracy gain | iteration_log.json |",
                "",
            ]
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--workspace-root", str(tmp_path)],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    output_json = tmp_path / "docs/30_evidence/Experiment_Evidence_Index.json"
    output_md = tmp_path / "docs/30_evidence/Experiment_Evidence_Index.md"
    assert output_json.exists()
    assert output_md.exists()
    data = json.loads(output_json.read_text(encoding="utf-8"))
    assert data["schema_version"] == "0.1"
    assert data["light_evidence_index"]["record_count"] >= 1
    entry = data["entries"][0]
    assert entry["valid_for_claim"] is True
    assert entry["analysis_report_path"] == "docs/40_iterations/iter1.md"
    assert "new method improves" in entry["purpose_summary"]
    assert "accuracy" in entry["result_summary"]
    assert entry["trust_assessment"]["level"] == "cross_checked"
    assert entry["trust_assessment"]["purpose_cross_checked"] is True
    assert entry["trust_assessment"]["result_cross_checked"] is True
    read_paths = {item["path"] for item in entry["evidence_read_set"]}
    assert "iteration_log.json" in read_paths
    assert "docs/40_iterations/iter1.md" in read_paths
    assert "experiments/iter1/epochs/1/eval.jsonl" in read_paths
    output_text = output_md.read_text(encoding="utf-8")
    assert "Light Evidence source" in output_text
    assert "Only rows with `valid_for_claim=true`" in output_text
    assert "`iteration_log.json` is a weak signal" in output_text


def test_build_light_evidence_index_writes_compact_records(tmp_path: Path) -> None:
    iteration = _iteration()
    iteration["schema_version"] = "2"
    iteration["action_state"] = {
        "next_action": "stop",
        "last_action": "eval",
        "reason": "test fixture",
        "blocked_by": [],
    }
    iteration["implementation"] = {
        "scope": "config_only",
        "code_manifest_path": None,
        "touched_paths": [],
        "stable_api_changed": False,
        "delegated_build_run_id": None,
        "promotion": {"status": "not_applicable", "plan_path": None},
    }
    _write_bundle(tmp_path, iteration)
    watchdog_status = (
        tmp_path
        / ".auto_iterate"
        / "run_health"
        / "status"
        / "auto_round1_run_full.json"
    )
    watchdog_status.parent.mkdir(parents=True)
    watchdog_status.write_text(
        json.dumps(
            {
                "status": "COMPLETED",
                "task": "auto_round1_run_full",
                "type": "training",
                "phase_key": "run_full",
                "iteration_id": "iter1",
                "ts": "2026-04-30T00:00:00Z",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (tmp_path / "iteration_log.json").write_text(
        json.dumps(
            {
                "schema_version": "2",
                "project": "test",
                "baseline_metrics": {},
                "best_iteration": "iter1",
                "iterations": [iteration],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    discovery = tmp_path / "docs" / "45_discoveries" / "Discovery_Ledger.md"
    discovery.parent.mkdir(parents=True)
    discovery.write_text(
        "\n".join(
            [
                "# Discovery Ledger",
                "",
                "| ID | Date | Level | Status | Summary | Evidence Refs | "
                "Next Experiment Hint |",
                "| --- | --- | --- | --- | --- | --- | --- |",
                "| d1 | 2026-06-17 | phenomenon | open | accuracy jump after "
                "config change | iteration_log.json | ablate config |",
                "",
            ]
        ),
        encoding="utf-8",
    )
    queue = tmp_path / "docs" / "40_iterations" / "Experiment_Queue.md"
    queue.parent.mkdir(parents=True, exist_ok=True)
    queue.write_text(
        "\n".join(
            [
                "# Experiment Queue",
                "",
                "| ID | Priority | Status | Assurance Axis | Question | "
                "Falsifier | Evidence Needed |",
                "| --- | --- | --- | --- | --- | --- | --- |",
                "| q1 | high | open | ablation | test whether the gain is "
                "component-specific | no change after ablation | "
                "ablation metrics |",
                "",
            ]
        ),
        encoding="utf-8",
    )
    wiki = tmp_path / "docs" / "45_discoveries" / "Research_Wiki.md"
    wiki.write_text(
        "\n".join(
            [
                "# Research Wiki",
                "",
                "| ID | Type | Status | Summary | Evidence Refs |",
                "| --- | --- | --- | --- | --- |",
                "| w1 | finding | active | component appears responsible for "
                "accuracy gain | iteration_log.json |",
                "",
            ]
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [sys.executable, str(LIGHT_SCRIPT), "--workspace-root", str(tmp_path)],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    data = json.loads(
        (tmp_path / ".evidence/light/index.json").read_text(encoding="utf-8")
    )
    assert data["schema_version"] == "light-v1"
    run_records = [item for item in data["records"] if item["id"] == "run:iter1"]
    assert run_records
    assert run_records[0]["summary"]
    assert run_records[0]["source_refs"]
    assert run_records[0]["pre_train_commit"] == "abc123"
    assert run_records[0]["pre_eval_commit_NOT_CHANGED"] is True
    assert run_records[0]["watchdog_status_path"].endswith(
        "auto_round1_run_full.json"
    )
    discoveries = [
        item for item in data["records"] if item["id"] == "discovery:d1"
    ]
    assert discoveries
    assert discoveries[0]["kind"] == "discovery"
    assert discoveries[0]["level"] == "phenomenon"
    queue_records = [
        item for item in data["records"] if item["id"] == "experiment_queue:q1"
    ]
    assert queue_records
    assert queue_records[0]["kind"] == "experiment_queue"
    assert queue_records[0]["assurance_axis"] == "ablation"
    wiki_records = [
        item for item in data["records"] if item["id"] == "research_wiki:w1"
    ]
    assert wiki_records
    assert wiki_records[0]["kind"] == "research_wiki"
    assert wiki_records[0]["topic_type"] == "finding"


def test_migrate_iteration_log_v2_writes_strict_fields_and_manifest(
    tmp_path: Path,
) -> None:
    legacy = {
        "iterations": [
            {
                "id": "iter1",
                "status": "training",
                "config_diff": {"run_local_config": "runs/iter1/config.yaml"},
            }
        ]
    }
    (tmp_path / "iteration_log.json").write_text(
        json.dumps(legacy) + "\n",
        encoding="utf-8",
    )

    result = subprocess.run(
        [sys.executable, str(MIGRATE_SCRIPT), "--workspace-root", str(tmp_path)],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    migrated = json.loads((tmp_path / "iteration_log.json").read_text())
    assert migrated["schema_version"] == "2"
    iteration = migrated["iterations"][0]
    assert iteration["status"] == "ready_to_run"
    assert iteration["action_state"]["next_action"] == "run_screening"
    assert iteration["implementation"]["scope"] == "config_only"
    manifest_path = tmp_path / iteration["implementation"]["code_manifest_path"]
    assert manifest_path.exists()
