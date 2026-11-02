import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from patchpulse.core import analyze, load_rows

class PatchPulseTests(unittest.TestCase):
    def test_regression(self):
        before = [{"region": "NA", "avg_fps": 120, "p95_frame_ms": 10, "p95_ping_ms": 30, "crashes": 0}] * 3
        after = [{"region": "NA", "avg_fps": 90, "p95_frame_ms": 14, "p95_ping_ms": 30, "crashes": 0}] * 3
        report = analyze(before, after)
        self.assertTrue(report["regions"][0]["metrics"]["avg_fps"]["regression"])
        self.assertTrue(report["regions"][0]["metrics"]["p95_frame_ms"]["regression"])

    def test_insufficient_sample(self):
        row = {"region": "EU", "avg_fps": 100, "p95_frame_ms": 10, "p95_ping_ms": 30, "crashes": 0}
        self.assertFalse(analyze([row], [dict(row, avg_fps=10)])["regions"][0]["metrics"]["avg_fps"]["regression"])

    def test_invalid_input(self):
        with self.assertRaises(ValueError):
            analyze([], [], threshold=-1)

if __name__ == "__main__":
    unittest.main()
