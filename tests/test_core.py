"""Unit, edge-case, cohort and golden-report tests for PatchPulse."""

import json
import math
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from patchpulse.core import analyze, load_rows


def row(region="NA", fps=120, frame=10, ping=30, crashes=0):
    return {"region": region, "avg_fps": fps, "p95_frame_ms": frame,
            "p95_ping_ms": ping, "crashes": crashes}


class PatchPulseTests(unittest.TestCase):
    def setUp(self):
        self.before = [row(), row(fps=118, frame=11, ping=32),
                       row(fps=122, frame=10, ping=31)]
        self.after = [row(fps=92, frame=15, ping=35),
                      row(fps=95, frame=14, ping=37),
                      row(fps=91, frame=16, ping=36, crashes=1)]

    def csv(self, content):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "samples.csv"
            p.write_text(content, encoding="utf-8")
            return load_rows(p)

    def test_regression(self):
        report = analyze(self.before, self.after)
        metrics = report["regions"][0]["metrics"]
        for metric in ("avg_fps", "p95_frame_ms", "p95_ping_ms", "crashes"):
            self.assertTrue(metrics[metric]["regression"], metric)

    def test_zero_baseline_crashes_report_undefined_pct(self):
        crashes = analyze(self.before, self.after)["regions"][0]["metrics"]["crashes"]
        self.assertIsNone(crashes["change_pct"])
        self.assertAlmostEqual(crashes["after"], 1 / 3)
        self.assertTrue(crashes["regression"])

    def test_zero_baseline_no_new_crashes_not_flagged(self):
        result = analyze([row()] * 3, [row()] * 3)
        self.assertFalse(result["regions"][0]["metrics"]["crashes"]["regression"])

    def test_zero_baseline_zero_fps_to_positive_is_not_regression(self):
        result = analyze([row(fps=0)] * 3, [row(fps=40)] * 3)
        fps = result["regions"][0]["metrics"]["avg_fps"]
        self.assertIsNone(fps["change_pct"])
        self.assertFalse(fps["regression"])

    def test_improvement_directions(self):
        result = analyze([row(fps=80, frame=30, ping=40, crashes=2)] * 3,
                         [row(fps=120, frame=10, ping=20, crashes=0)] * 3)
        self.assertTrue(all(not m["regression"] for m in result["regions"][0]["metrics"].values()))

    def test_insufficient_sample(self):
        result = analyze([row()], [row(fps=10)])
        self.assertFalse(result["regions"][0]["sufficient_samples"])
        self.assertFalse(result["regions"][0]["metrics"]["avg_fps"]["regression"])

    def test_threshold_inclusive(self):
        before, after = [row(fps=100)] * 3, [row(fps=90)] * 3
        self.assertTrue(analyze(before, after, threshold=10)["regions"][0]["metrics"]["avg_fps"]["regression"])

    def test_threshold_over_change_not_flagged(self):
        result = analyze([row(fps=100)] * 3, [row(fps=90)] * 3, threshold=11)
        self.assertFalse(result["regions"][0]["metrics"]["avg_fps"]["regression"])

    def test_threshold_zero_does_not_flag_unchanged_metrics(self):
        result = analyze([row()] * 3, [row()] * 3, threshold=0)
        self.assertTrue(result["regions"][0]["metrics"]["avg_fps"]["regression"])

    def test_reject_invalid_threshold(self):
        for value in (-1, math.nan, math.inf, -math.inf, True, "10", None):
            with self.subTest(value=value), self.assertRaises(ValueError):
                analyze(self.before, self.after, threshold=value)

    def test_reject_invalid_min_samples(self):
        for value in (0, -1, 1.5, True, "3", None):
            with self.subTest(value=value), self.assertRaises(ValueError):
                analyze(self.before, self.after, min_samples=value)

    def test_min_samples_one_allows_single_record(self):
        result = analyze([row()], [row(fps=60)], min_samples=1)
        self.assertTrue(result["regions"][0]["metrics"]["avg_fps"]["regression"])

    def test_reject_empty_cohorts(self):
        for a, b in (([], [row()]), ([row()], []), ([], [])):
            with self.subTest(a=a, b=b), self.assertRaises(ValueError):
                analyze(a, b)

    def test_reject_missing_region(self):
        for value in ("", "   ", None, 123):
            with self.subTest(value=value), self.assertRaises(ValueError):
                analyze([dict(row(), region=value)], [row()])

    def test_reject_nonfinite_or_negative_direct_metrics(self):
        for metric in ("avg_fps", "p95_frame_ms", "p95_ping_ms", "crashes"):
            for value in (-1, math.inf, math.nan, -math.inf, True, "10"):
                with self.subTest(metric=metric, value=value), self.assertRaises(ValueError):
                    analyze([dict(row(), **{metric:value})], [row()])

    def test_reject_noninteger_crashes(self):
        with self.assertRaisesRegex(ValueError, "integer"):
            analyze([row(crashes=0.5)], [row()])

    def test_reject_huge_crash_count(self):
        with self.assertRaisesRegex(ValueError, "integer"):
            analyze([row(crashes=2**54)], [row()])

    def test_reject_malformed_direct_row(self):
        for sample in (None, {}, {"region": "NA"}, "oops"):
            with self.subTest(sample=sample), self.assertRaises(ValueError):
                analyze([sample], [row()])

    def test_reject_nonfinite_cohort_sum(self):
        with self.assertRaisesRegex(ValueError, "numeric range"):
            analyze([row(fps=1e308)] * 3, [row()] * 3)

    def test_reject_nonfinite_relative_change(self):
        with self.assertRaisesRegex(ValueError, "numeric range"):
            analyze([row(fps=1e-300)] * 3, [row(fps=1e308)] * 3)

    def test_regions_sorted_and_not_mixed(self):
        before = [row("NA")] * 3 + [row("EU", fps=60)] * 3
        after = [row("NA", fps=90)] * 3 + [row("EU", fps=30)] * 3
        result = analyze(before, after)
        self.assertEqual([c["region"] for c in result["regions"]], ["EU", "NA"])

    def test_missing_one_side_region_is_not_flagged(self):
        result = analyze([row("EU")], [row("NA")], min_samples=1)
        for region in result["regions"]:
            self.assertFalse(region["sufficient_samples"])
            self.assertTrue(all(not m["regression"] for m in region["metrics"].values()))

    def test_output_does_not_include_match_ids(self):
        result = analyze(load_rows(ROOT / "examples" / "before.csv"),
                         load_rows(ROOT / "examples" / "after.csv"))
        self.assertNotIn("a1", json.dumps(result))
        self.assertNotIn("b1", json.dumps(result))

    def test_golden_sample_evidence_matches(self):
        result = analyze(load_rows(ROOT / "examples" / "before.csv"),
                         load_rows(ROOT / "examples" / "after.csv"))
        expected = json.loads((ROOT / "evidence" / "sample-report.json").read_text(encoding="utf-8"))
        self.assertEqual(result, expected)

    def test_sample_rows_have_expected_count(self):
        self.assertEqual(len(load_rows(ROOT / "examples" / "before.csv")), 3)
        self.assertEqual(len(load_rows(ROOT / "examples" / "after.csv")), 3)

    def test_csv_accepts_bom_and_quoted_region(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "rows.csv"
            p.write_text('match_id,region,build,avg_fps,p95_frame_ms,p95_ping_ms,crashes\n"a,1","N,A",1,100,10,20,0\n',encoding="utf-8-sig")
            self.assertEqual(load_rows(p)[0]["region"], "N,A")

    def test_csv_rejects_incorrect_headers(self):
        for header in ("match_id,region,build,avg_fps", "region,match_id,build,avg_fps,p95_frame_ms,p95_ping_ms,crashes",
                       "match_id,region,build,avg_fps,p95_frame_ms,p95_ping_ms,crashes,crashes"):
            with self.subTest(header=header), self.assertRaisesRegex(ValueError, "header"):
                self.csv(header + "\na1,NA,1,120,10,30,0\n")

    def test_csv_rejects_extra_and_missing_cells(self):
        for sample in ("a1,NA,1,120,10,30,0,extra", "a1,NA,1,120,10,30"):
            with self.subTest(sample=sample), self.assertRaisesRegex(ValueError, "seven columns"):
                self.csv("match_id,region,build,avg_fps,p95_frame_ms,p95_ping_ms,crashes\n"+sample+"\n")

    def test_csv_rejects_duplicate_ids(self):
        with self.assertRaisesRegex(ValueError, "duplicate match ID"):
            self.csv("match_id,region,build,avg_fps,p95_frame_ms,p95_ping_ms,crashes\na1,NA,1,100,10,20,0\na1,EU,1,100,10,20,0\n")

    def test_csv_rejects_bad_rows_with_line_numbers(self):
        for sample in ("a1,NA,1,nan,10,20,0", "a1,NA,1,100,-1,20,0", "a1,NA,1,100,10,20,0.5",
                       "a1,NA,1,100,10,20,inf", "a1,,1,100,10,20,0"):
            with self.subTest(sample=sample), self.assertRaisesRegex(ValueError, r"samples.csv:2:"):
                self.csv("match_id,region,build,avg_fps,p95_frame_ms,p95_ping_ms,crashes\n"+sample+"\n")

    def test_csv_rejects_unterminated_quote(self):
        with self.assertRaises(ValueError):
            self.csv('match_id,region,build,avg_fps,p95_frame_ms,p95_ping_ms,crashes\n"a1,NA,1,100,10,20,0\n')

    def test_csv_rejects_no_data_rows(self):
        with self.assertRaisesRegex(ValueError, "no data rows"):
            self.csv("match_id,region,build,avg_fps,p95_frame_ms,p95_ping_ms,crashes\n")


if __name__ == "__main__":
    unittest.main()
