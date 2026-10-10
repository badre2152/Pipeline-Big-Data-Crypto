"""Enforce source formatting without affecting pipeline behavior."""

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1] / "src"
BANNER = re.compile(r"^\s*#\s*[─═-]{5,}|^\s*#\s*─+.*─+")
EMOJI = re.compile(r"[✅🚀📊⚠🎯💡\uFE0F]")


class SourceStyleTests(unittest.TestCase):
    def test_source_has_no_decorative_banners_or_emojis(self):
        for path in ROOT.rglob("*.py"):
            with self.subTest(path=str(path)):
                source = path.read_text(encoding="utf-8")
                self.assertFalse(EMOJI.search(source), str(path))
                self.assertFalse(any(BANNER.match(x) for x in source.splitlines()), str(path))


if __name__ == "__main__":
    unittest.main()
