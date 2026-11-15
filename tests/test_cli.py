"""Real-process and file-safety tests for the PatchPulse command line."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class PatchPulseCliTests(unittest.TestCase):
    def run_cli(self, *arguments, cwd=None):
        env = os.environ.copy()
        env["PYTHONPATH"] = str(ROOT / "src") + os.pathsep + env.get("PYTHONPATH", "")
        return subprocess.run(
            [sys.executable, "-m", "patchpulse", *(str(x) for x in arguments)],
            cwd=cwd or ROOT, env=env,
            capture_output=True, text=True, check=False, timeout=20,
        )

    def sample_args(self):
        return ("--before", ROOT / "examples" / "before.csv",
                "--after", ROOT / "examples" / "after.csv")

    def test_golden_report_matches_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "report.json"
            result = self.run_cli(*self.sample_args(), "--output", dest)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(dest.read_text(encoding="utf-8")),
                             json.loads((ROOT / "evidence" / "sample-report.json").read_text(encoding="utf-8")))

    def test_default_output_in_working_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = self.run_cli(*self.sample_args(), cwd=tmp)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads((Path(tmp) / "report.json").read_text())["regions"][0]["region"], "NA")

    def test_output_alias_to_before_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "before.csv"
            source.write_bytes((ROOT / "examples" / "before.csv").read_bytes())
            original = source.read_bytes()
            r = self.run_cli("--before", source, "--after", ROOT / "examples" / "after.csv", "--output", source)
            self.assertEqual(r.returncode, 2)
            self.assertIn("overwrite", r.stderr)
            self.assertEqual(source.read_bytes(), original)

    def test_output_alias_to_after_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "after.csv"
            source.write_bytes((ROOT / "examples" / "after.csv").read_bytes())
            original = source.read_bytes()
            r = self.run_cli("--before", ROOT / "examples" / "before.csv", "--after", source, "--output", source)
            self.assertEqual(r.returncode, 2)
            self.assertEqual(source.read_bytes(), original)

    def test_existing_hard_link_alias_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "before.csv"
            dest = Path(tmp) / "output.csv"
            source.write_bytes((ROOT / "examples" / "before.csv").read_bytes())
            try:
                os.link(source, dest)
            except OSError as exc:
                self.skipTest(f"Hard links unsupported: {exc}")
            original = source.read_bytes()
            r = self.run_cli("--before", source, "--after", ROOT / "examples" / "after.csv", "--output", dest)
            self.assertEqual(r.returncode, 2)
            self.assertEqual(source.read_bytes(), original)

    def test_bad_csv_preserves_existing_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            invalid = Path(tmp) / "before.csv"
            output = Path(tmp) / "report.json"
            invalid.write_text("wrong,header\n", encoding="utf-8")
            output.write_text("old content", encoding="utf-8")
            r = self.run_cli("--before", invalid, "--after", ROOT / "examples" / "after.csv", "--output", output)
            self.assertEqual(r.returncode, 2)
            self.assertEqual(output.read_text(encoding="utf-8"), "old content")

    def test_nan_threshold_exit_two_preserves_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "report.json"
            output.write_text("original", encoding="utf-8")
            r = self.run_cli(*self.sample_args(), "--threshold", "nan", "--output", output)
            self.assertEqual(r.returncode, 2)
            self.assertEqual(output.read_text(encoding="utf-8"), "original")

    def test_infinite_threshold_exit_two(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "report.json"
            r = self.run_cli(*self.sample_args(), "--threshold", "inf", "--output", output)
            self.assertEqual(r.returncode, 2)
            self.assertFalse(output.exists())

    def test_existing_output_replaced_without_tmp_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "report.json"
            dest.write_text("old report", encoding="utf-8")
            r = self.run_cli(*self.sample_args(), "--output", dest)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(json.loads(dest.read_text())["regions"][0]["metrics"]["crashes"]["regression"], True)
            self.assertFalse(list(Path(tmp).glob("*.tmp")))

    def test_missing_input_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = self.run_cli("--before", Path(tmp) / "missing.csv", "--after", ROOT / "examples" / "after.csv",
                             "--output", Path(tmp) / "report.json")
            self.assertEqual(r.returncode, 2)
            self.assertIn("Error:", r.stderr)

    def test_help_exits_zero(self):
        r = self.run_cli("--help")
        self.assertEqual(r.returncode, 0)
        self.assertIn("--threshold", r.stdout)

    def test_missing_arguments_exit_two(self):
        r = self.run_cli("--threshold", "10")
        self.assertEqual(r.returncode, 2)
        self.assertIn("required", r.stderr)


if __name__ == "__main__":
    unittest.main()
