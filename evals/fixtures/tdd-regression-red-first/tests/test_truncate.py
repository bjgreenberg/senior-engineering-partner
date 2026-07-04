"""Tests for billing.truncate. Run from the repo root: python3 -m unittest"""

import unittest

from billing.truncate import safe_truncate


class TestSafeTruncate(unittest.TestCase):
    def test_returns_short_text_unchanged(self) -> None:
        self.assertEqual(safe_truncate("Total due: $12.00", 80), "Total due: $12.00")

    def test_result_never_exceeds_limit(self) -> None:
        self.assertLessEqual(len(safe_truncate("a" * 500, 100)), 100)


if __name__ == "__main__":
    unittest.main()
