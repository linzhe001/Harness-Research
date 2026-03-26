from __future__ import annotations

import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from remote_control.logs import read_latest_log


class LogsTest(unittest.TestCase):
    def test_read_latest_stdout_log(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            runtime = workspace / ".auto_iterate" / "runtime"
            runtime.mkdir(parents=True, exist_ok=True)

            older = runtime / "round1_plan.stdout.log"
            newer = runtime / "round2_run_full.stdout.log"
            older.write_text("old", encoding="utf-8")
            time.sleep(0.01)
            newer.write_text("new\nline2", encoding="utf-8")

            info = read_latest_log(workspace, stream="stdout", lines=2)
            self.assertEqual(info["path"], str(newer))
            self.assertIn("line2", info["content"])


if __name__ == "__main__":
    unittest.main()
