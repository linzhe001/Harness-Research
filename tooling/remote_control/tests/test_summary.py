from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from remote_control.config import RemoteControlConfig
from remote_control.summary import build_summary


class SummaryTest(unittest.TestCase):
    def test_build_summary_inactive_loop(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            cfg = RemoteControlConfig(
                workspace_root=workspace,
                default_goal_path=None,
                default_controller_config=None,
                default_accounts_config=None,
                default_tail_lines=20,
                default_log_lines=40,
            )

            with patch(
                "remote_control.summary.get_status",
                return_value=type("R", (), {"data": {"error": "No active loop"}})(),
            ), patch(
                "remote_control.summary.tail_events",
                return_value=type("R", (), {"ok": True, "data": {"events": []}})(),
            ):
                summary = build_summary(workspace, cfg)

        self.assertEqual(summary["workspace"]["name"], workspace.name)
        self.assertEqual(summary["auto_iterate"]["status"], "inactive")
        self.assertFalse(summary["staged_goal_present"])
        self.assertTrue(summary["recommended_actions"])


if __name__ == "__main__":
    unittest.main()
