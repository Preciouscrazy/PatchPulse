# PatchPulse

A local, offline patch-regression analysis toolkit for game telemetry.

PatchPulse compares aggregate performance metrics before and after a game update using CSV exports. It reports relative changes and flags potential regressions; it does not connect to Riot services, scrape clients, or claim causal attribution.

## Quick start

Requires Python 3.10+ (standard library only).

```bash
python -m patchpulse --before examples/before.csv --after examples/after.csv --output report.json
python -m unittest discover -s tests -v
```

Input columns: `match_id,region,build,avg_fps,p95_frame_ms,p95_ping_ms,crashes`. Each row represents a match or session. Build and region are labels; comparisons are stratified by region, and match IDs are not included in reports.

## Interpretation

A positive change in p95 frame time, p95 ping, or crashes per session can indicate regression; a negative change in average FPS can indicate regression. Default thresholds are configurable. Minimum 3 observations per region in each cohort are required for a flag. Outputs are observational, not statistically causal. Use larger samples and controlled comparisons before making decisions.

## Responsible use

Use only telemetry you own or are authorized to analyze. This is an independent educational project, not affiliated with or endorsed by Riot Games.

## Development

Run `python -m unittest discover -s tests -v`. CI runs tests on Python 3.10–3.12. License: MIT.
