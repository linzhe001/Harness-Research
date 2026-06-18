from __future__ import annotations

import importlib.util
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
WATCHDOG_PATH = REPO_ROOT / "tooling" / "run_health" / "watchdog.py"

spec = importlib.util.spec_from_file_location("run_health_watchdog", WATCHDOG_PATH)
assert spec is not None
watchdog = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(watchdog)


def test_register_and_unregister_task(tmp_path: Path) -> None:
    task = {
        "name": "iter1",
        "type": "training",
        "session": "iter1",
        "session_type": "none",
    }

    registered = watchdog.register_task(tmp_path, json.dumps(task))

    assert registered["name"] == "iter1"
    tasks = json.loads((tmp_path / "tasks.json").read_text(encoding="utf-8"))
    assert tasks[0]["session_type"] == "none"
    assert watchdog.unregister_task(tmp_path, "iter1") is True
    assert json.loads((tmp_path / "tasks.json").read_text(encoding="utf-8")) == []


def test_output_check_marks_completed(tmp_path: Path) -> None:
    marker = tmp_path / "done.txt"
    marker.write_text("done\n", encoding="utf-8")
    task = {
        "name": "download",
        "type": "download",
        "session": "none",
        "session_type": "none",
        "output_check": str(marker),
    }
    watchdog.register_task(tmp_path, json.dumps(task))

    statuses = watchdog.check_all(tmp_path)

    assert statuses[0]["status"] == "COMPLETED"
    status_file = tmp_path / "status" / "download.json"
    assert json.loads(status_file.read_text(encoding="utf-8"))["status"] == "COMPLETED"


def test_missing_session_marks_dead(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(watchdog, "session_alive", lambda _session, _type: False)
    task = {
        "name": "iter2",
        "type": "training",
        "session": "missing",
        "session_type": "tmux",
    }
    watchdog.register_task(tmp_path, json.dumps(task))

    statuses = watchdog.check_all(tmp_path)

    assert statuses[0]["status"] == "DEAD"
    assert "session is not alive" in statuses[0]["msg"]
    assert (tmp_path / "alerts.log").exists()


def test_oom_log_marks_oom(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(watchdog, "session_alive", lambda _session, _type: True)
    log = tmp_path / "train.log"
    log.write_text("RuntimeError: CUDA out of memory\n", encoding="utf-8")
    task = {
        "name": "iter3",
        "type": "training",
        "session": "iter3",
        "session_type": "none",
        "log_path": str(log),
    }
    watchdog.register_task(tmp_path, json.dumps(task))

    statuses = watchdog.check_all(tmp_path)

    assert statuses[0]["status"] == "OOM"
    assert statuses[0]["suggested_action"] == "reduce_batch_or_restart_from_checkpoint"


def test_summary_json_and_txt_are_written(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(watchdog, "session_alive", lambda _session, _type: True)
    monkeypatch.setattr(watchdog, "gpu_snapshot", lambda: [])
    task = {
        "name": "cmd1",
        "type": "command",
        "session": "cmd1",
        "session_type": "none",
    }
    watchdog.register_task(tmp_path, json.dumps(task))

    watchdog.check_all(tmp_path)

    summary = json.loads(
        (tmp_path / "status" / "summary.json").read_text(encoding="utf-8")
    )
    assert summary["task_count"] == 1
    assert summary["statuses"][0]["task"] == "cmd1"
    assert "cmd1(command): OK" in (
        tmp_path / "status" / "summary.txt"
    ).read_text(encoding="utf-8")
