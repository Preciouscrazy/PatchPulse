# PatchPulse — Validation record

**Upgrade branch:** `improve/patchpulse-reliability-ci-case-study`  
**Source base:** [Original main](https://github.com/Preciouscrazy/PatchPulse/commit/068f9d983b9b292771315056f18cc9e40f4abbc1) · [Earlier evidence PR #2](https://github.com/Preciouscrazy/PatchPulse/pull/2)

## Initial baseline

The original implementation had **three unit tests**. Its [baseline Ubuntu run #43105208862](https://github.com/Preciouscrazy/PatchPulse/actions/runs/43105208862) passed on Python 3.10, 3.11 and 3.12. The earlier open evidence PR added a six-row illustrative report that this upgrade incorporates and updates for the zero-baseline crash rule.

## Expanded test coverage

The upgrade defines **32 unit test methods** and **12 CLI subprocess test methods** (44 total). Tests check:

- Exact CSV header and row width; duplicates; blank IDs; invalid numbers and quoted values
- `NaN`, infinity, overflow, incorrect crash counts, threshold and sample-count limits
- Region isolation, insufficient cohorts, missing regions and improvement/worsening directions
- A zero-baseline crash increase, meaningful zero threshold behavior, and a golden JSON reference
- CLI success/error codes, both input/output alias directions, hard-link aliases, default output, and preserving existing reports on failures

The workflow installs PatchPulse and runs the entire suite on **Ubuntu 24.04 and Windows latest**, each with **Python 3.10, 3.11 and 3.12**. A hard-link test may be skipped if the environment does not support hard links; the remaining suite still runs.

| Runner | Python 3.10 | Python 3.11 | Python 3.12 |
| --- | --- | --- | --- |
| Ubuntu 24.04 | Pending | Pending | Pending |
| Windows latest | Pending | Pending | Pending |

**The CI matrix remains pending until a successful GitHub-hosted run of the upgraded source is confirmed.** This file will be updated with checked run links and results.

## Reproduce

```bash
python -m pip install -e .
python -m unittest discover -s tests -v
python -m patchpulse --before examples/before.csv --after examples/after.csv --output report.json
```

The canonical checked-in output is [`evidence/sample-report.json`](sample-report.json), which is a synthetic example, not game performance data. CI tests confirm stated program behavior, not causal attribution or performance of a live game.
