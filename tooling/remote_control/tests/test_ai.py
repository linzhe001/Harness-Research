from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from remote_control.ai import get_status, pause_loop, tail_events


class AITest(unittest.TestCase):
    def test_get_status_success(self) -> None:
        stdout = """{
  "status": "running",
  "current_round_index": 2,
  "current_phase_key": "run_full",
  "accounts": {"selected_account_id": "acc1"},
  "objective": {"primary_metric": {"name": "score"}},
  "best": {"primary_metric": {"value": 0.88}},
  "budget": {"max_rounds": 10}
}"""
        proc = subprocess.CompletedProcess(args=[], returncode=0, stdout=stdout, stderr="")

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            script = workspace / "tooling" / "auto_iterate" / "scripts"
            script.mkdir(parents=True, exist_ok=True)
            (script / "auto_iterate_ctl.sh").write_text("#!/usr/bin/env bash\n", encoding="utf-8")
            with patch("remote_control.ai.subprocess.run", return_value=proc):
                result = get_status(workspace)

        self.assertTrue(result.ok)
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(result.data["status"], "running")

    def test_tail_events_success(self) -> None:
        stdout = "\n".join(
            [
                '{"ts":"2026-03-26T00:00:00Z","round_index":1,"event":"ROUND_STARTED","phase_key":"plan"}',
                '{"ts":"2026-03-26T00:01:00Z","round_index":1,"event":"ROUND_COMPLETED","phase_key":"run_full"}',
            ]
        )
        proc = subprocess.CompletedProcess(args=[], returncode=0, stdout=stdout, stderr="")

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            script = workspace / "tooling" / "auto_iterate" / "scripts"
            script.mkdir(parents=True, exist_ok=True)
            (script / "auto_iterate_ctl.sh").write_text("#!/usr/bin/env bash\n", encoding="utf-8")
            with patch("remote_control.ai.subprocess.run", return_value=proc):
                result = tail_events(workspace, lines=2)

        self.assertTrue(result.ok)
        self.assertEqual(len(result.data["events"]), 2)

    def test_pause_loop_failure_maps_exit_code(self) -> None:
        proc = subprocess.CompletedProcess(args=[], returncode=102, stdout="", stderr="lock conflict")

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            script = workspace / "tooling" / "auto_iterate" / "scripts"
            script.mkdir(parents=True, exist_ok=True)
            (script / "auto_iterate_ctl.sh").write_text("#!/usr/bin/env bash\n", encoding="utf-8")
            with patch("remote_control.ai.subprocess.run", return_value=proc):
                result = pause_loop(workspace)

        self.assertFalse(result.ok)
        self.assertEqual(result.category, "lock_conflict")
        self.assertEqual(result.exit_code, 102)


if __name__ == "__main__":
    unittest.main()
