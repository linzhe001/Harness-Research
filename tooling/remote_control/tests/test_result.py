from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from remote_control.result import category_for_exit_code, make_result


class ResultTest(unittest.TestCase):
    def test_category_mapping(self) -> None:
        self.assertEqual(category_for_exit_code(0), "ok")
        self.assertEqual(category_for_exit_code(105), "manual_action_required")
        self.assertEqual(category_for_exit_code(999), "fatal")

    def test_make_result_defaults(self) -> None:
        result = make_result(ok=False, exit_code=102)
        self.assertFalse(result.ok)
        self.assertEqual(result.category, "lock_conflict")
        self.assertEqual(result.exit_code, 102)
        self.assertIn("lock", result.message.lower())


if __name__ == "__main__":
    unittest.main()
