# PatchPulse

**Python 3.10+ · Offline patch-regression comparisons · Validated, reproducible CSV-to-JSON analysis**

PatchPulse compares **synthetic or user-authorized** before/after game-session telemetry. It groups samples by region and highlights changes in average FPS, p95 frame time, p95 ping, and crashes per session.

The tool demonstrates how an engineer can build **explainable investigation signals** while keeping results distinct from causal claims. No Riot Games integrations, game clients, accounts, or production telemetry are involved.

**Start here:** [Engineering case study](docs/case-study.md) · [Six synthetic sample rows](examples/before.csv) · [Golden JSON report](evidence/sample-report.json) · [Test validation](evidence/validation.md)

## What the synthetic sample demonstrates

The fixture has **three before samples** from build `1.0` and **three after samples** from build `1.1`, all in region `NA`. It is an illustrative comparison, not an estimate of how any real software patch performed.

| Metric | Before mean | After mean | Interpretation |
| --- | ---: | ---: | --- |
| Average FPS | 120.00 | 92.67 | −22.78% — lower is unfavorable |
| p95 frame time | 10.33 ms | 15.00 ms | +45.16% — higher is unfavorable |
| p95 ping | 31.00 ms | 36.00 ms | +16.13% — higher is unfavorable |
| Crashes per session | 0.00 | 0.33 | Percent change undefined; zero-baseline increase flagged |

With the default **10% threshold** and at least **three samples in both cohorts**, all four metrics emit investigation flags. This includes the special zero-baseline crash rule (see below). A flag is **not proof that a software patch caused the change**.

[Inspect the exact JSON](evidence/sample-report.json) · [Before CSV](examples/before.csv) · [After CSV](examples/after.csv)

## Quick start

Requires Python 3.10+ and the Python standard library at runtime.

```bash
python -m pip install -e .
python -m patchpulse --before examples/before.csv --after examples/after.csv --output report.json
python -m unittest discover -s tests -v
```

`report.json` is a local generated file and is ignored by Git. A complete JSON payload is staged to a temporary file in the destination directory before replacing an existing report. The CLI refuses to write into either input CSV, including hard-linked aliases. This does not guarantee durability under sudden power loss or simultaneous writers.

## Input and algorithm

**Required CSV header, in exact order:**

```csv
match_id,region,build,avg_fps,p95_frame_ms,p95_ping_ms,crashes
```

Each match/session ID must be unique within its input file. ID, region and build labels cannot be blank. Metrics must be finite and nonnegative; crash counts must be exactly representable whole numbers. Unexpected/missing columns and malformed values are rejected with source-line errors. Region and build labels are input context; output is region-aggregated and does not expose individual match IDs.

For each region, PatchPulse computes an arithmetic mean of each metric independently for before and after. A **higher** FPS is generally favorable; **higher** frame time, ping and crash rate are unfavorable. The percentage change is `(after_mean - before_mean) / before_mean * 100` when the before mean is positive.

**Zero baseline:** a percentage cannot be computed from zero. The report uses JSON `null` for `change_pct`. If an unfavorable metric (frame time, ping or crashes) rises from zero to a positive value, PatchPulse flags it for investigation **only when both cohorts meet the minimum sample count**. An unchanged metric is not flagged even with threshold `0`.

**Sample sufficiency:** at least three rows in both cohorts are needed for a default flag. Regions that appear only on one side remain visible but cannot be flagged. All reported changes are descriptive observations, not statistical significance tests.

## Validation and limitations

The tests cover strict CSV parsing; non-finite and overflow inputs; cohort separation; threshold boundaries; the zero-baseline crash rule; missing samples; input/output collisions; CLI exit status; and **equality with the committed golden JSON**. GitHub Actions tests Python **3.10, 3.11, 3.12** on **Windows and Ubuntu**.

See [the verification record](evidence/validation.md) for exact hosted runs and supported evidence. This synthetic six-row fixture is too small to infer a real population effect. Region-level grouping alone does not control for hardware, game settings, skill, time of day, selection bias, network routes, or measurement quality. PatchPulse does not establish causality and should only process data the user owns or is authorized to analyze.

MIT licensed. Independent educational project; not affiliated with or endorsed by Riot Games.
