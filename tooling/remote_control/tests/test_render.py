from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from remote_control.render import render_hint_text, render_logs_text, render_status_text, render_tail_text


class RenderTest(unittest.TestCase):
    def test_render_status_text(self) -> None:
        text = render_status_text(
            {
                "status": "paused",
                "current_round_index": 3,
                "current_phase_key": "plan",
                "accounts": {"selected_account_id": "acc2"},
                "objective": {"primary_metric": {"name": "score"}},
                "best": {"primary_metric": {"value": 0.91}},
                "halt_reason": "operator_pause",
            }
        )
        self.assertIn("paused", text)
        self.assertIn("acc2", text)
        self.assertIn("score", text)

    def test_render_tail_text(self) -> None:
        text = render_tail_text(
            [
                {
                    "ts": "2026-03-26T00:00:00Z",
                    "round_index": 4,
                    "event": "ROUND_COMPLETED",
                    "phase_key": "run_full",
                }
            ]
        )
        self.assertIn("ROUND_COMPLETED", text)

    def test_render_logs_text(self) -> None:
        text = render_logs_text({"path": "/tmp/test.log", "stream": "stdout", "content": "line1\nline2"})
        self.assertIn("/tmp/test.log", text)
        self.assertIn("line2", text)

    def test_render_hint_text(self) -> None:
        text = render_hint_text(
            {
                "title": "Auto-iterate 已暂停",
                "recommended_actions": [
                    {"label": "继续", "value": "/ai resume"},
                    {"label": "停止", "value": "/ai stop"},
                ],
            }
        )
        self.assertIn("/ai resume", text)
        self.assertIn("Auto-iterate", text)


if __name__ == "__main__":
    unittest.main()
