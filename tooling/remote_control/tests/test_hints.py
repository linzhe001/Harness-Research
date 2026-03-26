from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from remote_control.hints import build_hint, recommended_actions


class HintsTest(unittest.TestCase):
    def test_recommended_actions_for_paused_loop(self) -> None:
        actions = recommended_actions({"auto_iterate": {"status": "paused"}})
        values = [action["value"] for action in actions]
        self.assertIn("/ai resume", values)
        self.assertIn("/ai stop", values)

    def test_build_hint_for_workspace_switch(self) -> None:
        hint = build_hint("workspace-switched", {"auto_iterate": {"status": "inactive"}})
        self.assertEqual(hint["context"], "workspace-switched")
        values = [action["value"] for action in hint["recommended_actions"]]
        self.assertIn("/new", values)
        self.assertIn("/ai status", values)


if __name__ == "__main__":
    unittest.main()
